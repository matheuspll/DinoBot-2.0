# 🤖 RagBot 2.0

Sistema RAG (Retrieval-Augmented Generation) para análise inteligente de documentos legais.

**Faça upload de PDFs e converse com o conteúdo através de perguntas em linguagem natural.**

## 🛠️ Stack

- **Backend**: FastAPI + LangChain + ChromaDB
- **Frontend**: Streamlit
- **LLM**: LLaMA3-70B (Groq API)
- **Embeddings**: all-MiniLM-L12-v2

## 🚀 Quick Start

### Pré-requisitos

- Python 3.8 ou superior
- Conta Groq (gratuita) - https://console.groq.com

### Instalação Automática (Recomendado)

```bash
# 1. Clone o repositório
git clone <seu-repo-url>
cd RagBot

# 2. Execute o script de setup
chmod +x setup.sh
./setup.sh

# 3. Configure sua API key
nano .env
# Adicione: GROQ_API_KEY=sua_chave_aqui
```

### Instalação Manual

```bash
# 1. Clone o repositório
git clone <seu-repo-url>
cd RagBot

# 2. Crie ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# 3. Instale dependências
pip install -r requirements.txt

# 4. Configure variáveis de ambiente
cp .env.example .env  # (ou crie manualmente)
nano .env
# Adicione: GROQ_API_KEY=sua_chave_aqui
```

### Obter GROQ_API_KEY

1. Acesse https://console.groq.com
2. Crie uma conta (gratuita)
3. Vá em "API Keys"
4. Clique em "Create API Key"
5. Copie a chave e cole no arquivo `.env`

## 🎯 Como Usar

### Iniciar o Sistema

**Terminal 1 - Backend:**
```bash
cd server
uvicorn main:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd client
streamlit run app.py
```

### Acessar a Aplicação

- **Frontend**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs

### Workflow

1. **Upload de PDFs**: Sidebar → Upload → Selecione múltiplos PDFs
2. **Aguarde Indexação**: Sistema processa e cria embeddings
3. **Faça Perguntas**: Digite na caixa de chat
4. **Veja Respostas**: Com citações das fontes

## 📁 Estrutura do Projeto

```
RagBot/
├── client/                 # Frontend Streamlit
│   ├── app.py             # Ponto de entrada
│   ├── config.py          # Configurações
│   ├── components/        # Componentes UI
│   └── utils/             # Utilitários (API client)
│
├── server/                # Backend FastAPI
│   ├── main.py           # API REST
│   ├── logger.py         # Sistema de logs
│   └── modules/          # Módulos RAG
│       ├── pdf_handlers.py
│       ├── load_vectorstore.py
│       ├── llm.py
│       └── query_handlers.py
│
├── acordaos_pdf/         # PDFs de teste (3 acórdãos)
├── requirements.txt      # Dependências Python
├── setup.sh             # Script de instalação
└── CLAUDE.md            # Documentação técnica completa
```

## ⚙️ Configuração Avançada

### Ajustar Parâmetros do RAG

**Tamanho dos chunks** (`server/modules/load_vectorstore.py`):
```python
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,      # Ajuste aqui
    chunk_overlap=100     # Ajuste aqui
)
```

**Número de chunks recuperados** (`server/modules/llm.py`):
```python
retriever = vectorstore.as_retriever(
    search_kwargs={'k': 3}  # Ajuste aqui
)
```

**Temperatura do LLM** (`server/modules/llm.py`):
```python
llm = ChatGroq(
    temperature=0.2  # 0=determinístico, 1=criativo
)
```

## 🧪 Testes

### Testar Backend
```bash
curl http://127.0.0.1:8000/test
# Resposta: {"message": "API is working!"}
```

### Limpar Dados
```bash
# Remover vectorstore (força reindexação)
rm -rf chroma_store/

# Remover PDFs salvos
rm -rf uploaded_pdfs/
```

## 📚 Documentação

Para documentação técnica completa, veja [`CLAUDE.md`](CLAUDE.md):
- Arquitetura RAG detalhada
- Fluxo de ingestão e query
- Convenções de código
- Troubleshooting

## 🐛 Troubleshooting

### "Chain não inicializada"
**Solução**: Faça upload de pelo menos um PDF primeiro.

### "GROQ_API_KEY not found"
**Solução**: Verifique se `.env` existe e contém `GROQ_API_KEY=sua_chave`

### Frontend não conecta ao backend
**Solução**: Verifique se backend está rodando em `http://127.0.0.1:8000`

### Respostas irrelevantes
**Solução**: Aumente `k` em `llm.py` ou `chunk_size` em `load_vectorstore.py`

## 📝 Licença

[Adicione sua licença aqui]

## 👥 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/NovaFeature`)
3. Commit suas mudanças (`git commit -m 'Add NovaFeature'`)
4. Push para a branch (`git push origin feature/NovaFeature`)
5. Abra um Pull Request

## 📧 Contato

[Adicione seu contato aqui]

---

**Desenvolvido com ❤️ para análise de documentos legais**
