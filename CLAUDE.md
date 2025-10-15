# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Descrição do Projeto

**RagBot 2.0** é um chatbot RAG (Retrieval-Augmented Generation) desenvolvido para análise inteligente de documentos legais, especificamente acórdãos da SEFAZ Acre. O sistema permite que usuários façam upload de múltiplos PDFs e conversem com o conteúdo através de perguntas em linguagem natural, recebendo respostas contextualizadas com citações das fontes.

### Objetivo
Facilitar a consulta e análise de grandes volumes de documentos legais através de interface conversacional, permitindo recuperação rápida de informações específicas sem necessidade de leitura manual completa dos documentos.

## Stack Tecnológica

### Backend (FastAPI)
- **FastAPI 0.116.1** - Framework web assíncrono para API REST
- **Uvicorn 0.35.0** - Servidor ASGI para FastAPI
- **Python 3.x** - Linguagem base

### RAG & LLM
- **LangChain 0.3.27** - Framework para orquestração RAG
  - `langchain-core 0.3.72` - Abstrações e tipos base
  - `langchain-community 0.3.27` - Integrações e loaders
  - `langchain-groq 0.3.6` - Cliente Groq API
  - `langchain-chroma 0.2.5` - Integração ChromaDB
  - `langchain-huggingface 0.3.1` - Modelos HuggingFace
  - `langchain-text-splitters 0.3.9` - Divisão de documentos
- **ChromaDB 1.0.15** - Banco de dados vetorial para embeddings
- **Groq 0.30.0** - Cliente para API Groq (LLM)

### Processamento de Documentos
- **PyPDF 5.9.0** - Extração de texto de PDFs
- **sentence-transformers 5.0.0** - Modelos de embeddings
- **transformers 4.54.1** - Biblioteca HuggingFace

### Frontend (Streamlit)
- **Streamlit 1.47.1** - Framework para interface web interativa
- **Requests 2.32.4** - Cliente HTTP para comunicação com API

### Utilidades
- **python-dotenv 1.1.1** - Gerenciamento de variáveis de ambiente
- **loguru 0.7.3** / **logging** - Sistema de logs

### Modelos
- **LLM**: LLaMA3-70B-8192 (via Groq API)
- **Embeddings**: all-MiniLM-L12-v2 (HuggingFace, 384 dimensões)

## Arquitetura RAG

### Visão Geral do Fluxo

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Streamlit  │  HTTP   │   FastAPI    │  Query  │   ChromaDB   │
│   Frontend   │ ◄─────► │   Backend    │ ◄─────► │  Vectorstore │
│  (Port 8501) │         │  (Port 8000) │         │              │
└──────────────┘         └──────────────┘         └──────────────┘
                                │
                                │ API Call
                                ▼
                         ┌──────────────┐
                         │   Groq API   │
                         │  (LLaMA3)    │
                         └──────────────┘
```

### Fase 1: Ingestão e Indexação

**Fluxo**: PDF Upload → Extração → Chunking → Embedding → Armazenamento

1. **Upload de PDFs** (`server/main.py:65` - endpoint `/upload_pdfs/`)
   - Usuário faz upload de múltiplos PDFs via Streamlit
   - Frontend envia arquivos para API via `POST /upload_pdfs/`

2. **Processamento de PDFs** (`server/modules/pdf_handlers.py:13`)
   - Função: `process_uploaded_pdf(file: UploadFile)`
   - PDFs salvos em `./uploaded_pdfs/`
   - `PyPDFLoader` extrai texto de todas as páginas
   - Cada página → `Document` LangChain com metadata (source, page)

3. **Chunking de Documentos** (`server/modules/load_vectorstore.py:33`)
   - `RecursiveCharacterTextSplitter`:
     - **chunk_size**: 1000 caracteres
     - **chunk_overlap**: 100 caracteres
   - Overlap mantém contexto entre chunks adjacentes
   - Evita cortar frases/conceitos no meio

4. **Geração de Embeddings** (`server/modules/load_vectorstore.py:38`)
   - Modelo: `all-MiniLM-L12-v2` (HuggingFace)
   - Cada chunk de texto → vetor de 384 dimensões
   - Embeddings capturam significado semântico
   - Execução em CPU (configurável via `model_kwargs`)

5. **Armazenamento Vetorial** (`server/modules/load_vectorstore.py:44-57`)
   - ChromaDB persiste embeddings em `./chroma_store/`
   - Lógica incremental:
     - Se vectorstore existe: adiciona novos documentos
     - Se não existe: cria novo banco de dados
   - Mantém metadata para rastreabilidade das fontes

6. **Atualização da Chain** (`server/main.py:87`)
   - **CRÍTICO**: Chain RAG é recriada após cada upload
   - Garante que novas queries vejam documentos adicionados
   - Chain armazenada em variável global `chain`

### Fase 2: Recuperação e Geração (Query)

**Fluxo**: Pergunta → Embedding → Busca Semântica → Contexto → LLM → Resposta

1. **Pergunta do Usuário** (`client/components/chatUI.py:25`)
   - Usuário digita pergunta na interface de chat
   - Frontend envia via `POST /ask/` com Form data

2. **Validação** (`server/main.py:99`)
   - Verifica se `chain` está inicializada
   - Retorna HTTP 400 se vectorstore não está pronto

3. **Embedding da Query** (`server/modules/llm.py:24`)
   - Pergunta convertida em vetor usando MESMO modelo de embeddings
   - Consistência crucial para busca semântica funcionar

4. **Busca Semântica** (`server/modules/llm.py:24`)
   - Retriever configurado: `search_kwargs={'k': 3}`
   - ChromaDB busca 3 chunks mais similares
   - Usa similaridade coseno entre vetores
   - Retorna chunks ordenados por relevância

5. **Construção do Prompt** (`server/modules/llm.py:30`)
   - `RetrievalQA` com `chain_type='stuff'`
   - "Stuff" = insere todos os chunks recuperados no prompt
   - Prompt implícito: "Baseado no contexto: [chunks], responda: [pergunta]"

6. **Geração da Resposta** (`server/modules/llm.py:15`)
   - LLM: `ChatGroq` com `llama3-70b-8192`
   - **Temperature**: 0.2 (respostas mais determinísticas e focadas)
   - LLM recebe contexto + pergunta
   - Gera resposta fundamentada nos documentos

7. **Formatação** (`server/modules/query_handlers.py:26`)
   - Extrai resposta textual
   - Coleta fontes dos `source_documents`
   - Retorna JSON: `{"response": "...", "sources": [...]}`

8. **Exibição** (`client/components/chatUI.py:41`)
   - Resposta renderizada no chat
   - Fontes citadas abaixo para auditabilidade
   - Histórico salvo em `st.session_state.messages`

### Componentes Chave do RAG

**Vectorstore (ChromaDB)**
- Banco de dados vetorial persistente
- Armazena embeddings + metadata + texto original
- Permite buscas por similaridade eficientes

**Retriever**
- Interface entre vectorstore e chain
- Configurável: número de documentos (k), tipo de busca
- Retorna documentos ranqueados por relevância

**RetrievalQA Chain**
- Une retriever + LLM em pipeline único
- Orquestra: busca → formatação → geração
- Retorna respostas + documentos fonte

**Global Chain State**
- `chain` = variável global em `server/main.py`
- Inicializada no startup se vectorstore existe
- Recriada após uploads para incluir novos documentos

## Estrutura de Pastas

```
RagBot/
│
├── client/                          # Frontend Streamlit
│   ├── app.py                      # Ponto de entrada principal
│   │                               # - Configura página Streamlit
│   │                               # - Renderiza layout (sidebar + main)
│   │                               # - Orquestra componentes
│   │
│   ├── config.py                   # Configurações do cliente
│   │                               # - API_URL: endpoint do backend
│   │
│   ├── components/                 # Componentes UI modulares
│   │   ├── chatUI.py              # Interface de chat principal
│   │   │                          # - Gerencia histórico (session_state)
│   │   │                          # - Renderiza mensagens user/assistant
│   │   │                          # - Exibe fontes citadas
│   │   │                          # - Chama ask_question() da API
│   │   │
│   │   ├── upload.py              # Componente de upload de PDFs
│   │   │                          # - File uploader (múltiplos PDFs)
│   │   │                          # - Botão "Upload to DB"
│   │   │                          # - Chama upload_pdfs_api()
│   │   │
│   │   └── history_download.py    # Download do histórico
│   │                               # - Formata histórico do chat
│   │                               # - Botão para download como .txt
│   │
│   └── utils/
│       └── api.py                  # Cliente da API backend
│                                   # - upload_pdfs_api(): envia PDFs
│                                   # - ask_question(): envia perguntas
│
├── server/                          # Backend FastAPI
│   ├── main.py                     # Aplicação FastAPI principal
│   │                               # - Define endpoints: /upload_pdfs/, /ask/, /test
│   │                               # - Lifespan manager: inicializa chain no startup
│   │                               # - Variável global: chain (estado RAG)
│   │                               # - Middleware CORS para acesso cross-origin
│   │
│   ├── logger.py                   # Sistema de logging
│   │                               # - setup_logger(): configura logger
│   │                               # - Formato: [timestamp] [level] - message
│   │
│   ├── modules/                    # Módulos funcionais do RAG
│   │   │
│   │   ├── pdf_handlers.py        # Processamento de PDFs
│   │   │                          # - process_uploaded_pdf(): salva e extrai páginas
│   │   │                          # - Usa PyPDFLoader
│   │   │                          # - Salva em ./uploaded_pdfs/
│   │   │
│   │   ├── load_vectorstore.py    # Gerenciamento do vectorstore
│   │   │                          # - add_documents_to_vectorstore(): chunking + embedding + persist
│   │   │                          # - RecursiveCharacterTextSplitter
│   │   │                          # - ChromaDB em ./chroma_store/
│   │   │                          # - PERSIST_DIR: constante do caminho
│   │   │
│   │   ├── llm.py                 # Configuração da LLM chain
│   │   │                          # - get_llm_chain(): cria RetrievalQA
│   │   │                          # - ChatGroq com LLaMA3-70B
│   │   │                          # - Retriever com k=3
│   │   │                          # - Carrega GROQ_API_KEY do .env
│   │   │
│   │   └── query_handlers.py      # Execução de queries
│   │                               # - query_chain(): invoca chain e formata resposta
│   │                               # - Extrai response + sources
│   │
│   └── requirements.txt            # Dependências Python
│
├── uploaded_pdfs/                   # PDFs enviados (criado em runtime)
│                                   # - Armazena arquivos originais
│                                   # - Usado como referência de fonte
│
├── chroma_store/                    # Banco vetorial ChromaDB (criado em runtime)
│                                   # - Embeddings persistidos
│                                   # - Metadata dos documentos
│                                   # - Índices de busca
│
├── .env                            # Variáveis de ambiente (NÃO comitar!)
│                                   # - GROQ_API_KEY
│
├── .gitignore                      # Arquivos ignorados pelo git
│                                   # - venv/, .env, uploaded_pdfs/, chroma_store/
│
└── README.md                       # Instruções básicas de setup
```

### Arquivos Críticos

**server/main.py** - Coração do backend
- Inicialização da chain no startup (lifespan manager)
- Endpoints REST
- Variável global `chain` mantém estado

**server/modules/load_vectorstore.py** - Gestão do conhecimento
- Lógica de chunking
- Criação/atualização do vectorstore
- Configuração de embeddings

**server/modules/llm.py** - Configuração RAG
- Define modelo LLM
- Configura retriever (k=3)
- Monta RetrievalQA chain

**client/components/chatUI.py** - Interface principal
- Gerencia histórico com session_state
- Loop de conversação
- Exibição de respostas + fontes

## Configuração

### Variáveis de Ambiente

Criar arquivo `.env` na raiz do projeto:

```bash
# Obrigatório: Chave da API Groq para acesso ao LLaMA3
GROQ_API_KEY=gsk_your_groq_api_key_here
```

**Como obter GROQ_API_KEY:**
1. Criar conta em https://console.groq.com
2. Acessar API Keys
3. Gerar nova chave
4. Copiar e colar no .env

### Configurações do Cliente

**client/config.py:**
```python
API_URL = "http://127.0.0.1:8000"  # URL do backend
```

**Modificar quando deploying:**
- Desenvolvimento: `http://127.0.0.1:8000`
- Produção: `https://seu-dominio.com`

### Configurações do RAG

**Parâmetros ajustáveis:**

| Parâmetro | Arquivo | Linha | Valor Padrão | Descrição |
|-----------|---------|-------|--------------|-----------|
| `chunk_size` | `load_vectorstore.py` | 33 | 1000 | Tamanho dos chunks (caracteres) |
| `chunk_overlap` | `load_vectorstore.py` | 33 | 100 | Sobreposição entre chunks |
| `k` (retrieval) | `llm.py` | 24 | 3 | Número de chunks recuperados |
| `temperature` | `llm.py` | 18 | 0.2 | Criatividade (0=determinístico, 1=criativo) |
| `model_name` | `llm.py` | 17 | llama3-70b-8192 | Modelo LLM |
| `embedding_model` | `load_vectorstore.py` | 39 | all-MiniLM-L12-v2 | Modelo de embeddings |

## Comandos Úteis

### Setup Inicial

```bash
# 1. Criar ambiente virtual
python -m venv venv

# 2. Ativar ambiente virtual
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 3. Instalar dependências
pip install -r server/requirements.txt

# 4. Criar arquivo .env
echo "GROQ_API_KEY=sua_chave_aqui" > .env
```

### Desenvolvimento

**Rodar Backend (FastAPI):**
```bash
# Entrar no diretório do servidor
cd server

# Rodar com reload automático (desenvolvimento)
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Rodar sem reload (produção)
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Rodar Frontend (Streamlit):**
```bash
# Em terminal separado, entrar no diretório do cliente
cd client

# Rodar Streamlit
streamlit run app.py

# Rodar em porta específica
streamlit run app.py --server.port 8501
```

**Rodar ambos simultaneamente:**
```bash
# Terminal 1: Backend
cd server && uvicorn main:app --reload

# Terminal 2: Frontend
cd client && streamlit run app.py
```

### Testes e Debug

**Testar API:**
```bash
# Health check
curl http://127.0.0.1:8000/test

# Ver documentação interativa
# Abrir no navegador: http://127.0.0.1:8000/docs
```

**Debug com logs detalhados:**
```python
# Em logger.py, ajustar nível:
logger.setLevel(logging.DEBUG)  # Já configurado
```

**Limpar dados:**
```bash
# Remover vectorstore (força reindexação)
rm -rf chroma_store/

# Remover PDFs salvos
rm -rf uploaded_pdfs/
```

### Gerenciamento de Dependências

**Atualizar requirements.txt:**
```bash
pip freeze > server/requirements.txt
```

**Instalar nova dependência:**
```bash
pip install nome-do-pacote
pip freeze > server/requirements.txt
```

## Convenções de Código

### Estilo Python

**Seguir PEP 8:**
- Indentação: 4 espaços
- Linhas: máximo 100 caracteres (preferencialmente 88)
- Imports: agrupados (stdlib, third-party, local)
- Naming:
  - Funções/variáveis: `snake_case`
  - Classes: `PascalCase`
  - Constantes: `UPPER_SNAKE_CASE`

**Exemplo:**
```python
from typing import List
from langchain_core.documents import Document

PERSIST_DIR = "./chroma_store"  # Constante

def process_documents(documents: List[Document]) -> None:
    """Processa lista de documentos."""
    pass
```

### Organização de Módulos

**Backend (server/):**
- Um módulo = uma responsabilidade
- Funções devem ser puras quando possível
- Evitar lógica de negócio em `main.py`
- Módulos em `modules/` para funcionalidades RAG

**Frontend (client/):**
- Componentes em `components/`
- Cada componente = uma função `render_*()`
- Utilitários em `utils/`
- Configurações em `config.py`

### Nomenclatura de Funções

**Padrões existentes:**
- `process_*` - Transformação de dados (ex: `process_uploaded_pdf`)
- `add_*_to_*` - Adiciona item a coleção (ex: `add_documents_to_vectorstore`)
- `get_*` - Retorna objeto configurado (ex: `get_llm_chain`)
- `query_*` - Executa consulta (ex: `query_chain`)
- `render_*` - Renderiza UI (ex: `render_chat`)
- `setup_*` - Inicialização (ex: `setup_logger`)

### Type Hints

**Sempre usar type hints:**
```python
from typing import List, Optional
from langchain_core.documents import Document

def process_pdf(file: UploadFile) -> List[Document] | None:
    """Type hints tornam código mais claro e detectam bugs."""
    pass
```

### Docstrings

**Formato:**
```python
def function_name(param: Type) -> ReturnType:
    """
    Breve descrição em uma linha.

    Descrição mais detalhada se necessário.

    Args:
        param: Descrição do parâmetro.

    Returns:
        Descrição do que é retornado.
    """
    pass
```

### Logging

**Níveis de log:**
```python
log.debug("Informação detalhada para debug")
log.info("Confirmação de operação normal")
log.warning("Algo inesperado mas não crítico")
log.error("Erro que impediu operação")
log.exception("Erro com stacktrace completo")
```

**Quando logar:**
- `INFO`: Início/fim de operações importantes
- `WARNING`: Fallbacks, dados faltantes não críticos
- `ERROR`: Falhas que impedem operação
- `DEBUG`: Detalhes internos (valores de variáveis)

### Tratamento de Erros

**Padrões:**
```python
# Em endpoints FastAPI: usar HTTPException
from fastapi import HTTPException

if chain is None:
    raise HTTPException(
        status_code=400,
        detail="Chain não inicializada. Faça upload de PDFs."
    )

# Em funções: logar e repassar ou retornar None
try:
    result = operation()
except Exception as e:
    log.exception(f"Erro em operation: {e}")
    raise  # ou return None
```

### Estrutura de Endpoints

**Padrão FastAPI:**
```python
@app.post("/endpoint/")
async def endpoint_name(param: Type = Form(...)):
    """
    Docstring descrevendo o endpoint.
    """
    global chain  # Se necessário

    # 1. Validação
    if not valid:
        raise HTTPException(status_code=400, detail="...")

    # 2. Logging
    log.info(f"Operação iniciada: {param}")

    # 3. Processamento
    try:
        result = process(param)
    except Exception as e:
        log.exception("Erro no processamento")
        raise HTTPException(status_code=500, detail=str(e))

    # 4. Retorno
    log.info("Operação concluída com sucesso")
    return {"message": "Sucesso", "data": result}
```

### Componentes Streamlit

**Padrão:**
```python
def render_component_name():
    """
    Renderiza [descrição do componente].
    """
    # 1. Inicializar session_state se necessário
    if "key" not in st.session_state:
        st.session_state.key = default_value

    # 2. UI
    st.header("Título")
    user_input = st.input_widget()

    # 3. Lógica de interação
    if st.button("Ação"):
        result = api_call(user_input)
        st.success("Sucesso!")
```

## Notas Importantes

### 🔴 Pontos Críticos

1. **Chain Global State**
   - A variável `chain` em `server/main.py` é global e stateful
   - DEVE ser recriada após cada upload de PDFs (linha 87)
   - Sem isso, novas queries não veem documentos adicionados

2. **Consistência de Embeddings**
   - SEMPRE usar o MESMO modelo de embeddings
   - Atualmente: `all-MiniLM-L12-v2`
   - Mudar modelo requer reindexação completa (deletar `chroma_store/`)

3. **GROQ_API_KEY Obrigatória**
   - Sistema não funciona sem a chave
   - Carregar com `python-dotenv` antes de inicializar LLM
   - Nunca comitar `.env` no git

4. **Ordem de Inicialização**
   - Backend DEVE iniciar antes do frontend
   - Frontend assume que `http://127.0.0.1:8000` está disponível

5. **ChromaDB Persistence**
   - ChromaDB persiste automaticamente em disco
   - Diretório `chroma_store/` contém índices e dados
   - Deletar = perder todo o conhecimento indexado

### ⚠️ Limitações Conhecidas

1. **Modelo de Embeddings em CPU**
   - `all-MiniLM-L12-v2` roda em CPU por padrão
   - Para GPU: modificar `model_kwargs={'device': 'cuda'}`
   - Upload de muitos PDFs pode ser lento

2. **Sem Autenticação**
   - API não tem autenticação
   - Qualquer cliente pode acessar
   - Não usar em produção sem adicionar auth

3. **CORS Aberto**
   - `allow_origins=["*"]` permite qualquer origem
   - OK para desenvolvimento
   - Em produção: especificar origens permitidas

4. **Sem Rate Limiting**
   - Groq API tem limites de requisições
   - Sistema não implementa retry ou rate limiting
   - Pode falhar em uso intenso

5. **Session State Volátil**
   - Histórico do chat vive apenas em `st.session_state`
   - Refresh da página = perde histórico
   - Para persistência: salvar em banco de dados

### 🛠️ Debugging Comum

**Problema: "Chain não inicializada"**
- Causa: Vectorstore não existe
- Solução: Fazer upload de pelo menos um PDF

**Problema: "Embeddings incompatíveis"**
- Causa: Mudou modelo de embeddings mas vectorstore antigo existe
- Solução: `rm -rf chroma_store/` e reindexar

**Problema: Frontend não conecta ao backend**
- Causa: Backend não está rodando ou porta errada
- Solução: Verificar `client/config.py` e rodar backend

**Problema: Respostas irrelevantes**
- Causa: k muito baixo ou chunks muito pequenos
- Solução: Aumentar k em `llm.py:24` ou chunk_size em `load_vectorstore.py:33`

**Problema: Erro "GROQ_API_KEY not found"**
- Causa: Arquivo `.env` não existe ou está mal formatado
- Solução: Criar `.env` com formato correto

### 📈 Melhorias Futuras Sugeridas

1. **Autenticação e Autorização**
   - Adicionar FastAPI OAuth2 ou JWT
   - Separar documentos por usuário

2. **Persistência de Histórico**
   - Salvar conversas em banco de dados
   - Permitir retomar conversas antigas

3. **Rate Limiting**
   - Implementar slowapi ou similar
   - Prevenir abuso da API Groq

4. **Testes Automatizados**
   - Unit tests para funções de processamento
   - Integration tests para endpoints
   - Framework: pytest

5. **Melhor Tratamento de Chunks**
   - Considerar semantic chunking
   - Implementar re-ranking de resultados

6. **Monitoring**
   - Adicionar métricas (latência, uso)
   - Dashboard de observabilidade

7. **Deployment**
   - Dockerizar aplicação
   - CI/CD pipeline
   - Environment configs (dev/staging/prod)

### 🔧 Modificações Comuns

**Mudar modelo LLM:**
```python
# Em server/modules/llm.py:17
llm = ChatGroq(
    groq_api_key=os.getenv('GROQ_API_KEY'),
    model_name='llama3-8b-8192',  # Modelo menor/mais rápido
    temperature=0.2
)
```

**Ajustar número de chunks recuperados:**
```python
# Em server/modules/llm.py:24
retriever = vectorstore.as_retriever(search_kwargs={'k': 5})  # Mais contexto
```

**Usar GPU para embeddings:**
```python
# Em server/modules/load_vectorstore.py:39
embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L12-v2",
    model_kwargs={'device': 'cuda'}  # Requer CUDA instalado
)
```

**Adicionar novo endpoint:**
```python
# Em server/main.py
@app.get("/list_documents/")
async def list_documents():
    """Lista todos os PDFs indexados."""
    if not os.path.exists(UPLOAD_DIR):
        return {"documents": []}
    files = os.listdir(UPLOAD_DIR)
    return {"documents": [f for f in files if f.endswith('.pdf')]}
```

### 📚 Recursos Adicionais

**Documentação Oficial:**
- LangChain: https://python.langchain.com/docs/
- FastAPI: https://fastapi.tiangolo.com/
- Streamlit: https://docs.streamlit.io/
- ChromaDB: https://docs.trychroma.com/
- Groq: https://console.groq.com/docs/

**Conceitos RAG:**
- RAG Overview: https://www.pinecone.io/learn/retrieval-augmented-generation/
- Vector Embeddings: https://www.pinecone.io/learn/vector-embeddings/
- Semantic Search: https://www.sbert.net/examples/applications/semantic-search/README.html

---

**Última atualização**: 2025-10-12
**Versão**: 2.0
