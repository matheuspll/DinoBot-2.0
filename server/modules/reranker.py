"""
Módulo de reranking para melhorar a relevância dos chunks recuperados.

Aplica pesos baseados em:
1. Relevância jurídica da seção (ementa > acordão > outros)
2. Match de palavras-chave da query
3. Match de metadados estruturados
"""

from typing import List
from langchain_core.documents import Document
from logger import setup_logger

log = setup_logger()


def rerank_by_relevance(chunks: List[Document], query: str, top_k: int = 5) -> List[Document]:
    """
    Reranqueia chunks baseado em múltiplos fatores de relevância.

    Args:
        chunks: Lista de documentos recuperados do vectorstore
        query: Query original do usuário
        top_k: Número de chunks a retornar após reranking

    Returns:
        Lista de chunks reranqueados (top_k mais relevantes)
    """
    if not chunks:
        return []

    log.debug(f"Reranqueando {len(chunks)} chunks para query: '{query[:50]}...'")

    query_lower = query.lower()
    query_tokens = set(query_lower.split())

    scored_chunks = []

    for chunk in chunks:
        score = 1.0  # Score base

        # FATOR 1: Peso da seção (relevância jurídica)
        relevancia = chunk.metadata.get('relevancia_juridica', 1.0)
        score *= relevancia
        log.debug(f"  Chunk {chunk.metadata.get('source', 'unknown')[:30]} - Relevância base: {relevancia:.2f}")

        # FATOR 2: Match de palavras-chave da query no conteúdo
        chunk_lower = chunk.page_content.lower()
        matching_tokens = sum(1 for token in query_tokens if len(token) > 3 and token in chunk_lower)

        if matching_tokens > 0:
            keyword_boost = 1 + (0.1 * matching_tokens)
            score *= keyword_boost
            log.debug(f"    + Keyword boost: {keyword_boost:.2f} ({matching_tokens} matches)")

        # FATOR 3: Boost por palavras-chave estruturadas (metadata)
        if 'palavras_chave' in chunk.metadata and chunk.metadata['palavras_chave']:
            palavras_meta = chunk.metadata['palavras_chave'].lower()
            for token in query_tokens:
                if len(token) > 3 and token in palavras_meta:
                    score *= 1.3
                    log.debug(f"    + Metadata keyword boost: 1.3 ('{token}')")
                    break  # Aplicar boost uma vez por chunk

        # FATOR 4: Boost por tipo de tributo (se mencionado na query)
        tipo_tributo = chunk.metadata.get('tipo_tributo')
        if tipo_tributo and tipo_tributo.lower() in query_lower:
            score *= 1.4
            log.debug(f"    + Tributo match boost: 1.4 ('{tipo_tributo}')")

        # FATOR 5: Boost por decisão (se mencionado na query)
        decisao = chunk.metadata.get('decisao')
        if decisao:
            decisoes = ['provido', 'improvido', 'parcial', 'deferido', 'indeferido']
            for dec in decisoes:
                if dec in query_lower and dec in decisao.lower():
                    score *= 1.3
                    log.debug(f"    + Decisão match boost: 1.3 ('{decisao}')")
                    break

        # FATOR 6: Penalidade para chunks muito curtos (podem ser ruído)
        content_length = len(chunk.page_content)
        if content_length < 100:
            score *= 0.5
            log.debug(f"    - Penalty curto: 0.5 (length={content_length})")

        scored_chunks.append((score, chunk))
        log.debug(f"  Score final: {score:.2f}")

    # Ordenar por score decrescente
    scored_chunks.sort(key=lambda x: x[0], reverse=True)

    # Log dos top scores
    log.info(f"Top {min(top_k, len(scored_chunks))} chunks após reranking:")
    for i, (score, chunk) in enumerate(scored_chunks[:top_k]):
        source = chunk.metadata.get('source', 'unknown')
        secao = chunk.metadata.get('secao', 'unknown')
        log.info(f"  {i+1}. {source} [{secao}] - Score: {score:.2f}")

    # Retornar top-k
    return [chunk for score, chunk in scored_chunks[:top_k]]
