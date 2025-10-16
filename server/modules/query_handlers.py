# Em server/modules/query_handlers.py

from langchain.chains import RetrievalQA
from logger import setup_logger
from modules.reranker import rerank_by_relevance

log = setup_logger()

def query_chain(chain: RetrievalQA, user_input: str) -> dict:
    """
    Executa a cadeia RAG com a pergunta do usuário e formata a resposta.
    Aplica reranking aos documentos recuperados antes de enviar ao LLM.

    Args:
        chain: A instância da cadeia RetrievalQA.
        user_input: A pergunta do usuário.

    Returns:
        Um dicionário com a resposta e as fontes, ou gera uma exceção em caso de erro.
    """
    try:
        log.debug(f"Executando a cadeia para a entrada: '{user_input}'")

        # 1. Busca vetorial inicial (recupera k=8 docs)
        docs_initial = chain.retriever.get_relevant_documents(user_input)
        log.debug(f"Documentos recuperados inicialmente: {len(docs_initial)}")

        # 2. Aplica reranking (retorna top 5)
        docs_reranked = rerank_by_relevance(docs_initial, user_input, top_k=5)
        log.info(f"Documentos após reranking: {len(docs_reranked)}")

        # 3. Sobrescreve temporariamente os docs recuperados
        # Cria um dicionário com inputs formatados para o chain
        formatted_inputs = {
            "query": user_input,
            "source_documents": docs_reranked
        }

        # 4. Executa o LLM com docs reranqueados
        # Vamos usar combine_documents_chain diretamente
        context = "\n\n".join([doc.page_content for doc in docs_reranked])
        llm_inputs = {
            "context": context,
            "question": user_input
        }

        llm_result = chain.combine_documents_chain.invoke(
            {"input_documents": docs_reranked, "question": user_input}
        )

        # 5. Formata a resposta de forma limpa
        response = {
            "response": llm_result.get("output_text", "Não foi possível gerar uma resposta."),
            "sources": [
                doc.metadata.get("source", "Fonte desconhecida")
                for doc in docs_reranked
            ]
        }

        log.debug(f"Resposta da cadeia: {response}")
        return response

    except Exception as e:
        log.exception("Ocorreu um erro ao executar a cadeia de consulta.")
        # Relança a exceção para que o endpoint do FastAPI possa tratá-la.
        raise