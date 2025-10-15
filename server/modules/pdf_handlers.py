# Em server/modules/pdf_handler.py

from pathlib import Path
from typing import List
from fastapi import UploadFile
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from logger import setup_logger

log = setup_logger()
UPLOAD_DIR = Path("./uploaded_pdfs")

def process_uploaded_pdf(file: UploadFile) -> List[Document] | None:
    """
    Salva um arquivo PDF enviado, extrai o conteúdo de TODAS as páginas
    e retorna uma lista de Documentos LangChain.

    Args:
        file: O objeto UploadFile vindo diretamente do FastAPI.

    Returns:
        Uma lista de objetos Document, onde cada um representa uma página do PDF,
        ou None se ocorrer um erro.
    """
    try:
        # Garante que o diretório de destino exista
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # Define o caminho completo para salvar o arquivo
        file_path = UPLOAD_DIR / file.filename

        # Salva o conteúdo do arquivo no disco
        with open(file_path, "wb") as f:
            f.write(file.file.read())
        log.info(f"Arquivo '{file.filename}' salvo com sucesso em '{file_path}'.")

        # Carrega o PDF salvo para extrair o texto
        loader = PyPDFLoader(str(file_path))
        
        # .load() extrai TODAS as páginas do PDF e retorna uma lista de Documentos.
        documents = loader.load()
        log.info(f"{len(documents)} páginas extraídas do arquivo '{file.filename}'.")
        
        return documents

    except Exception as e:
        log.error(f"Falha ao processar o arquivo '{file.filename}': {e}")
        return None