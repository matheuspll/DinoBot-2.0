import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.chains import RetrievalQA

# Carrega as variáveis do arquivo .env para o ambiente do sistema
load_dotenv()

def get_llm_chain(vectorstore):
    """
    Cria e configura a cadeia de Pergunta e Resposta com Recuperação (RAG).
    """
    # 1. Inicializa o LLM (cérebro)
    # Pega a chave da API do ambiente e configura o modelo LLaMA3 via Groq.
    llm = ChatGroq(
        groq_api_key=os.getenv('GROQ_API_KEY'),
        model_name='llama3-70b-8192',
        temperature=0.2 # Adicionado para respostas mais focadas
    )

    # 2. Cria o Recuperador (bibliotecário)
    # Transforma seu banco de dados vetorial em um buscador que encontrará
    # os 3 trechos (k=3) mais relevantes para a pergunta do usuário.
    retriever = vectorstore.as_retriever(search_kwargs={'k': 3})

    # 3. Monta a Cadeia Final
    # Une o cérebro (llm) e o bibliotecário (retriever) em uma única cadeia.
    # 'chain_type="stuff"' significa que ele vai "enfiar" os trechos encontrados
    # diretamente no prompt do LLM.
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type='stuff',
        retriever=retriever,
        return_source_documents=True # Importante: retorna os trechos usados como fonte
    )
    
    return qa_chain