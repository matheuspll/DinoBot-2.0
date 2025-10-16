# Em server/modules/load_vectorstore.py

import os
import re
from typing import List, Dict, Optional
from pathlib import Path
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from logger import setup_logger

log = setup_logger()

PERSIST_DIR = "./chroma_store"
EXTRACTED_JSON_DIR = "./extracted_json"


def detect_section_from_content(content: str) -> str:
    """
    Detecta a seção do documento baseado no conteúdo.

    Args:
        content: Texto do chunk

    Returns:
        Nome da seção: 'ementa', 'acordao', 'voto', 'relatorio', 'outros'
    """
    content_upper = content.upper()

    # Detectar EMENTA (geralmente tem palavras-chave em caps)
    if re.search(r'E\s*M\s*E\s*N\s*T\s*A', content_upper):
        return 'ementa'

    # Detectar ACÓRDÃO
    if re.search(r'A\s*C\s*[ÓO]\s*R\s*D\s*[ÃA]\s*O', content_upper):
        return 'acordao'

    # Detectar VOTO
    if 'VOTO' in content_upper or 'FUNDAMENTAÇÃO' in content_upper:
        return 'voto'

    # Detectar RELATÓRIO
    if 'RELATÓRIO' in content_upper or 'RELATOR' in content_upper:
        return 'relatorio'

    return 'outros'


def create_structural_chunks_from_json(json_data: Dict, source_file: str) -> List[Document]:
    """
    Cria chunks estruturados baseado no JSON extraído.
    Cada seção lógica (ementa, acordão) vira um chunk.

    Args:
        json_data: Dicionário com dados extraídos do PDF
        source_file: Nome do arquivo PDF original

    Returns:
        Lista de Documents com metadados enriquecidos
    """
    chunks = []

    # Extrair metadados comuns
    acordao_numero = json_data.get('acordao_numero', 'Desconhecido')
    processo = json_data.get('processo', 'Desconhecido')
    decisao = json_data.get('acordao', {}).get('decisao', None)

    # Extrair ano da data_sessao ou acordao_numero
    ano = None
    if json_data.get('data_sessao'):
        ano = str(json_data['data_sessao'])[:4]
    elif '/' in acordao_numero:
        ano = acordao_numero.split('/')[-1]

    # CHUNK 1: EMENTA (prioridade máxima)
    if json_data.get('ementa'):
        ementa = json_data['ementa']

        # Preparar metadados filtrando None
        metadata_ementa = {
            'source': source_file,
            'acordao_numero': acordao_numero,
            'processo': processo,
            'secao': 'ementa',
            'relevancia_juridica': 1.5,  # EMENTA tem peso maior
            'page': 1  # Ementa geralmente está na página 1
        }

        # Adicionar campos opcionais apenas se não forem None
        if ementa.get('tipo_tributo'):
            metadata_ementa['tipo_tributo'] = ementa.get('tipo_tributo')
        if ementa.get('palavras_chave'):
            metadata_ementa['palavras_chave'] = ','.join(ementa.get('palavras_chave', []))
        if decisao:
            metadata_ementa['decisao'] = decisao
        if ano:
            metadata_ementa['ano'] = ano

        chunks.append(Document(
            page_content=ementa.get('texto_completo', ''),
            metadata=metadata_ementa
        ))
        log.debug(f"Chunk EMENTA criado para {source_file}")

    # CHUNK 2: ACÓRDÃO (decisão + fundamentação)
    if json_data.get('acordao'):
        acordao = json_data['acordao']
        texto_acordao = acordao.get('texto_completo', '')

        # Se texto do acórdão for muito longo (>3000 chars), dividir preservando parágrafos
        if len(texto_acordao) > 3000:
            paragrafos = texto_acordao.split('\n\n')
            sub_chunks = []
            current = ""

            for paragrafo in paragrafos:
                if len(current) + len(paragrafo) < 2000:
                    current += paragrafo + "\n\n"
                else:
                    if current:
                        sub_chunks.append(current.strip())
                    current = paragrafo + "\n\n"

            if current:
                sub_chunks.append(current.strip())

            # Criar documento para cada sub-chunk
            for i, sub_chunk in enumerate(sub_chunks):
                metadata_acordao = {
                    'source': source_file,
                    'acordao_numero': acordao_numero,
                    'processo': processo,
                    'secao': f'acordao_parte_{i+1}',
                    'relevancia_juridica': 1.2,  # ACÓRDÃO tem peso médio-alto
                    'page': i + 2  # Estimativa de página
                }

                # Adicionar campos opcionais apenas se não forem None
                if acordao.get('decisao'):
                    metadata_acordao['decisao'] = acordao.get('decisao')
                if acordao.get('votacao'):
                    metadata_acordao['votacao'] = acordao.get('votacao')
                if ano:
                    metadata_acordao['ano'] = ano

                chunks.append(Document(
                    page_content=sub_chunk,
                    metadata=metadata_acordao
                ))
            log.debug(f"Acórdão longo dividido em {len(sub_chunks)} sub-chunks para {source_file}")
        else:
            # Acórdão cabe em um único chunk
            metadata_acordao_unico = {
                'source': source_file,
                'acordao_numero': acordao_numero,
                'processo': processo,
                'secao': 'acordao',
                'relevancia_juridica': 1.2,
                'page': 2
            }

            # Adicionar campos opcionais apenas se não forem None
            if acordao.get('decisao'):
                metadata_acordao_unico['decisao'] = acordao.get('decisao')
            if acordao.get('votacao'):
                metadata_acordao_unico['votacao'] = acordao.get('votacao')
            if ano:
                metadata_acordao_unico['ano'] = ano

            chunks.append(Document(
                page_content=texto_acordao,
                metadata=metadata_acordao_unico
            ))
            log.debug(f"Chunk ACÓRDÃO criado para {source_file}")

    log.info(f"Criados {len(chunks)} chunks estruturais para {source_file}")
    return chunks


def add_documents_to_vectorstore(documents: List[Document]) -> Chroma | None:
    """
    MODO LEGADO: Recebe documentos (páginas de PDF) e adiciona ao vectorstore
    com chunking tradicional por tamanho.

    NOTA: Esta função é mantida para compatibilidade, mas o ideal é usar
    add_documents_with_structured_chunking() com JSONs extraídos.

    Args:
        documents: Uma lista de objetos Document do LangChain.

    Returns:
        O objeto vectorstore do Chroma atualizado.
    """
    if not documents:
        log.warning("Nenhuma lista de documentos foi fornecida para adicionar ao vectorstore.")
        return None

    # 1. Divide os Documentos recebidos em chunks (modo tradicional)
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = splitter.split_documents(documents)

    # 2. Enriquecer metadados básicos detectando seção
    for chunk in chunks:
        if 'secao' not in chunk.metadata:
            chunk.metadata['secao'] = detect_section_from_content(chunk.page_content)
        if 'relevancia_juridica' not in chunk.metadata:
            # Dar peso baseado na seção detectada
            secao = chunk.metadata.get('secao', 'outros')
            weights = {
                'ementa': 1.5,
                'acordao': 1.2,
                'voto': 1.0,
                'relatorio': 0.9,
                'outros': 0.8
            }
            chunk.metadata['relevancia_juridica'] = weights.get(secao, 1.0)

    log.info(f"{len(documents)} página(s) dividida(s) em {len(chunks)} chunks.")

    # 3. Configura o modelo de embedding
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L12-v2",
        model_kwargs={'device': 'cpu'}
    )

    # 4. Cria ou atualiza o banco de dados vetorial
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

    log.info("Banco de dados ChromaDB atualizado e salvo no disco.")
    return vectorstore


def add_documents_with_structured_chunking(
    pdf_path: Path,
    json_data: Optional[Dict] = None
) -> Chroma | None:
    """
    MODO RECOMENDADO: Cria chunks estruturados a partir do JSON extraído.

    Args:
        pdf_path: Caminho do PDF original
        json_data: Dicionário com dados extraídos (se None, usa chunking legado)

    Returns:
        Vectorstore atualizado
    """
    if json_data:
        # Usar chunking estrutural baseado no JSON
        log.info(f"Usando chunking estrutural para {pdf_path.name}")
        chunks = create_structural_chunks_from_json(json_data, pdf_path.name)
    else:
        # Fallback para chunking tradicional
        log.warning(f"JSON não disponível para {pdf_path.name}, usando chunking tradicional")
        from modules.pdf_handlers import process_uploaded_pdf

        # Processar PDF para obter documentos
        class MockUploadFile:
            def __init__(self, path):
                self.filename = path.name
                with open(path, 'rb') as f:
                    self.file = f
                    self.content = f.read()

        mock_file = MockUploadFile(pdf_path)
        documents = process_uploaded_pdf(mock_file)

        if not documents:
            log.error(f"Falha ao processar {pdf_path.name}")
            return None

        # Usar função legado
        return add_documents_to_vectorstore(documents)

    # Configurar embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L12-v2",
        model_kwargs={'device': 'cpu'}
    )

    # Adicionar ao vectorstore
    if os.path.exists(PERSIST_DIR) and os.listdir(PERSIST_DIR):
        log.info(f"Atualizando ChromaDB existente com chunks estruturados")
        vectorstore = Chroma(
            persist_directory=PERSIST_DIR,
            embedding_function=embeddings
        )
        vectorstore.add_documents(chunks)
    else:
        log.info(f"Criando novo ChromaDB com chunks estruturados")
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=PERSIST_DIR
        )

    log.info(f"Vectorstore atualizado com {len(chunks)} chunks estruturados")
    return vectorstore