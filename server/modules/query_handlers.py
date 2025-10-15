# Em server/modules/query_handlers.py

from langchain.chains import RetrievalQA
from logger import setup_logger # CORRIGIDO

log = setup_logger() # CORRIGIDO

def query_chain(chain: RetrievalQA, user_input: str) -> dict:
    """
    Executa a cadeia RAG com a pergunta do usuário e formata a resposta.

    Args:
        chain: A instância da cadeia RetrievalQA.
        user_input: A pergunta do usuário.

    Returns:
        Um dicionário com a resposta e as fontes, ou gera uma exceção em caso de erro.
    """
    try:
        log.debug(f"Executando a cadeia para a entrada: '{user_input}'")
        
        # A forma moderna de invocar a cadeia usando .invoke()
        result = chain.invoke(user_input) # MELHORADO
        
        # Formata a resposta de forma limpa
        response = {
            "response": result.get("result", "Não foi possível gerar uma resposta."),
            "sources": [
                doc.metadata.get("source", "Fonte desconhecida") 
                for doc in result.get("source_documents", [])
            ]
        }
        
        log.debug(f"Resposta da cadeia: {response}")
        return response
        
    except Exception as e:
        log.exception("Ocorreu um erro ao executar a cadeia de consulta.")
        # Relança a exceção para que o endpoint do FastAPI possa tratá-la.
        raise