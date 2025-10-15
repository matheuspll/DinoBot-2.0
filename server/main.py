# Em server/main.py

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from contextlib import asynccontextmanager
import os

# Importa as funções refatoradas dos nossos módulos
from modules.pdf_handlers import process_uploaded_pdf
from modules.load_vectorstore import add_documents_to_vectorstore, PERSIST_DIR
from modules.llm import get_llm_chain
from modules.query_handlers import query_chain
from logger import setup_logger

# Nossas variáveis globais para manter o estado da aplicação
# Elas serão inicializadas durante o evento de "lifespan"
chain = None
log = setup_logger()

# O "lifespan manager" é a forma moderna de executar código na inicialização e no desligamento
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Código a ser executado ANTES de a aplicação começar a receber requisições
    log.info("Iniciando a aplicação...")
    global chain
    if os.path.exists(PERSIST_DIR):
        log.info("Carregando vectorstore existente e montando a cadeia RAG...")
        # Se o banco de dados já existe, carrega-o e monta a cadeia principal
        #from langchain_community.vectorstores import Chroma
        from langchain_chroma import Chroma
        #from langchain_community.embeddings import HuggingFaceEmbeddings
        from langchain_huggingface import HuggingFaceEmbeddings

        vectorstore = Chroma(
            persist_directory=PERSIST_DIR,
            embedding_function=HuggingFaceEmbeddings(
                model_name="all-MiniLM-L12-v2",
                model_kwargs={'device': 'cpu'}
            )
        )
        chain = get_llm_chain(vectorstore)
        log.info("Cadeia RAG pronta.")
    else:
        log.warning("Nenhum vectorstore encontrado. A cadeia não foi montada. Faça o upload de PDFs para começar.")
    
    yield # A aplicação fica rodando aqui
    
    # Código a ser executado APÓS a aplicação ser desligada (opcional)
    log.info("Aplicação encerrada.")

app = FastAPI(title="RagBot2.0", lifespan=lifespan)

# Permite que o frontend (que roda em outra porta/domínio) acesse esta API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/upload_pdfs/")
async def upload_pdfs(files: List[UploadFile] = File(...)):
    """
    Recebe uma lista de PDFs, os processa e atualiza o vectorstore e a cadeia RAG.
    """
    global chain
    log.info(f"Recebidos {len(files)} arquivos para processamento.")
    
    all_docs = []
    for file in files:
        # 1. Processa cada PDF para extrair seus documentos (páginas)
        docs = process_uploaded_pdf(file)
        if docs:
            all_docs.extend(docs)
    
    if not all_docs:
        raise HTTPException(status_code=400, detail="Nenhum documento válido pôde ser processado.")

    # 2. Adiciona os documentos extraídos ao banco de dados vetorial
    vectorstore = add_documents_to_vectorstore(all_docs)
    
    # 3. CRUCIAL: Recria a cadeia RAG com o banco de dados atualizado
    chain = get_llm_chain(vectorstore)
    
    log.info("Documentos adicionados e cadeia RAG atualizada com sucesso.")
    return {"message": "Arquivos processados e vectorstore atualizado com sucesso."}


@app.post("/ask/")
async def ask_question(question: str = Form(...)):
    """
    Recebe uma pergunta e a responde usando a cadeia RAG pré-carregada.
    """
    global chain
    if chain is None:
        log.error("Tentativa de fazer uma pergunta sem a cadeia RAG estar pronta.")
        raise HTTPException(status_code=400, detail="O sistema não está pronto. Por favor, envie os documentos PDF primeiro.")
    
    try:
        log.info(f"Recebida a pergunta do usuário: '{question}'")
        # 4. Executa a cadeia de forma rápida e eficiente
        result = query_chain(chain, question)
        log.info("Pergunta respondida com sucesso.")
        return result
    except Exception as e:
        log.exception("Erro ao processar a pergunta.")
        raise HTTPException(status_code=500, detail=f"Erro interno ao processar a pergunta: {e}")

@app.get("/test")
async def test():
    return {"message": "Servidor RagBot2.0 está no ar!"}