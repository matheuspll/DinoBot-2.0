# Em server/modules/load_vectorstore.py

import os
from typing import List
from langchain_core.documents import Document
#from langchain_community.vectorstores import Chroma
from langchain_chroma import Chroma
#from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from logger import setup_logger

log = setup_logger()

PERSIST_DIR = "./chroma_store"

def add_documents_to_vectorstore(documents: List[Document]) -> Chroma | None:
    """
    Recebe uma lista de Documentos LangChain, os processa e os adiciona ao ChromaDB.

    Args:
        documents: Uma lista de objetos Document do LangChain.

    Returns:
        O objeto vectorstore do Chroma atualizado.
    """
    if not documents:
        log.warning("Nenhuma lista de documentos foi fornecida para adicionar ao vectorstore.")
        return None

    # 1. Divide os Documentos recebidos em chunks
    # Como já recebemos Documentos, usamos split_documents diretamente.
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = splitter.split_documents(documents)
    log.info(f"{len(documents)} página(s) dividida(s) em {len(chunks)} chunks.")

    # 2. Configura o modelo de embedding
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L12-v2",
        model_kwargs={'device': 'cpu'} # Especifique CPU para consistência
    )

    # 3. Cria ou atualiza o banco de dados vetorial
    if os.path.exists(PERSIST_DIR) and os.listdir(PERSIST_DIR):
        log.info(f"Carregando ChromaDB existente de '{PERSIST_DIR}' e adicionando novos chunks.")
        vectorstore = Chroma(
            persist_directory=PERSIST_DIR,
            embedding_function=embeddings
        )
        vectorstore.add_documents(chunks)
    else:
        log.info(f"Criando um novo ChromaDB em '{PERSIST_DIR}'.")
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=PERSIST_DIR
        )
    
    # 4. Salva as alterações no disco
    log.info("Banco de dados ChromaDB atualizado e salvo no disco.")

    return vectorstore