import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from typing import List

# Carrega as variáveis do arquivo .env para o ambiente do sistema
load_dotenv()

# Prompt especializado para documentos jurídicos (acórdãos SEFAZ Acre)
JURIDICAL_PROMPT_TEMPLATE = """Você é um assistente jurídico especializado em acórdãos da SEFAZ Acre (Secretaria de Fazenda do Estado do Acre).

REGRAS OBRIGATÓRIAS (siga rigorosamente):
1. Base suas respostas EXCLUSIVAMENTE nos trechos de documentos fornecidos abaixo
2. SEMPRE cite a fonte completa: "Conforme [nome do documento] (página [X]): [trecho literal relevante]"
3. Use terminologia técnica jurídica apropriada: "recorrente", "decisão colegiada", "provimento", "improvimento", "ementa", etc.
4. Se houver informações conflitantes entre documentos, mencione ambas e cite as fontes distintas
5. Se NÃO houver informação suficiente nos documentos para responder, diga explicitamente: "Não há informações suficientes nos documentos indexados para responder esta questão"
6. Nunca invente ou infira informações que não estejam explícitas nos documentos
7. Ao citar números de acórdãos ou processos, copie exatamente como aparecem no documento

FORMATO DE CITAÇÃO CORRETO:
✓ Correto: "Conforme Acórdão-2017-011.pdf (página 2): 'não incide ICMS sobre operações de exportação de mercadorias'"
✗ Errado: "De acordo com a jurisprudência, não incide ICMS em exportações"

EXEMPLO DE BOA RESPOSTA:
Pergunta: "Qual a decisão sobre isenção de ICMS para produtos da cesta básica?"
Resposta: "O Acórdão-2017-145.pdf (página 3) decidiu pelo IMPROVIMENTO do recurso, mantendo a autuação fiscal. O colegiado entendeu que 'não se aplica isenção de ICMS a operações internas destinadas a consumidor final, conforme artigo 5º da Lei Estadual 1234/2010' (Ementa, página 1). A decisão foi por unanimidade, com participação dos conselheiros Nabil Ibrahim Chamchoum, Breno Geovane Azevedo Caetano e Luiz Rogério Amaral Colturato."

---

CONTEXTO DOS DOCUMENTOS (use APENAS estas informações):
{context}

---

PERGUNTA DO USUÁRIO:
{question}

---

RESPOSTA FUNDAMENTADA (com citações obrigatórias das fontes):"""

def get_llm_chain(vectorstore):
    """
    Cria e configura a cadeia de Pergunta e Resposta com Recuperação (RAG).
    Usa prompt especializado para documentos jurídicos com ancoragem obrigatória em fontes.
    Reranking será aplicado no query_handlers.py.
    """
    # 1. Inicializa o LLM (cérebro)
    # Pega a chave da API do ambiente e configura o modelo LLaMA3 via Groq.
    llm = ChatGroq(
        groq_api_key=os.getenv('GROQ_API_KEY'),
        model_name='llama-3.3-70b-versatile',  # Modelo atualizado
        temperature=0.1  # Reduzido para 0.1 para respostas mais determinísticas e precisas
    )

    # 2. Cria o Recuperador padrão
    # Busca 8 chunks (reranking será aplicado depois no query_handlers)
    retriever = vectorstore.as_retriever(search_kwargs={'k': 8})

    # 3. Cria o prompt customizado
    prompt = PromptTemplate(
        template=JURIDICAL_PROMPT_TEMPLATE,
        input_variables=["context", "question"]
    )

    # 4. Monta a Cadeia Final com prompt customizado
    # Une o cérebro (llm) e o bibliotecário (retriever) em uma única cadeia.
    # 'chain_type="stuff"' significa que ele vai "enfiar" os trechos encontrados
    # diretamente no prompt do LLM.
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type='stuff',
        retriever=retriever,
        return_source_documents=True,  # Importante: retorna os trechos usados como fonte
        chain_type_kwargs={"prompt": prompt}  # Usa o prompt customizado
    )

    return qa_chain