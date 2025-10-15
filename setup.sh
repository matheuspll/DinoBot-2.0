#!/bin/bash

# RagBot 2.0 - Setup Script
# Este script configura o ambiente de desenvolvimento completo

set -e  # Para execução em caso de erro

echo "╔════════════════════════════════════════════════╗"
echo "║     🤖 RagBot 2.0 - Setup Automático          ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para prints coloridos
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Verificar se Python 3 está instalado
print_info "Verificando instalação do Python..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 não encontrado! Por favor, instale Python 3.8 ou superior."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2)
print_success "Python $PYTHON_VERSION encontrado"

# Criar ambiente virtual
print_info "Criando ambiente virtual (venv)..."
if [ -d "venv" ]; then
    print_warning "Diretório 'venv' já existe. Removendo..."
    rm -rf venv
fi

python3 -m venv venv
print_success "Ambiente virtual criado com sucesso"

# Ativar ambiente virtual
print_info "Ativando ambiente virtual..."
source venv/bin/activate

# Verificar se ativou corretamente
if [ -z "$VIRTUAL_ENV" ]; then
    print_error "Falha ao ativar ambiente virtual!"
    exit 1
fi
print_success "Ambiente virtual ativado: $VIRTUAL_ENV"

# Atualizar pip
print_info "Atualizando pip para a versão mais recente..."
python -m pip install --upgrade pip --quiet
PIP_VERSION=$(pip --version | cut -d ' ' -f 2)
print_success "pip atualizado para versão $PIP_VERSION"

# Instalar dependências
print_info "Instalando dependências do requirements.txt..."
echo ""
print_warning "Este processo pode levar alguns minutos (especialmente PyTorch)..."
echo ""

pip install -r requirements.txt

print_success "Todas as dependências instaladas com sucesso!"

# Verificar arquivo .env
echo ""
print_info "Verificando configuração do ambiente..."
if [ ! -f ".env" ]; then
    print_warning "Arquivo .env não encontrado!"
    echo ""
    echo "Criando arquivo .env template..."
    cat > .env << 'EOF'
# RagBot 2.0 - Configurações de Ambiente

# Obrigatório: Chave da API Groq para acesso ao LLaMA3
# Obtenha sua chave em: https://console.groq.com/keys
GROQ_API_KEY=your_groq_api_key_here
EOF
    print_success "Arquivo .env criado"
    echo ""
    print_warning "AÇÃO NECESSÁRIA: Edite o arquivo .env e adicione sua GROQ_API_KEY"
    echo "                 Obtenha sua chave em: https://console.groq.com/keys"
else
    print_success "Arquivo .env encontrado"

    # Verificar se a chave está configurada
    if grep -q "your_groq_api_key_here" .env; then
        print_warning "GROQ_API_KEY ainda não foi configurada no arquivo .env"
        echo "                 Edite .env e adicione sua chave de: https://console.groq.com/keys"
    else
        print_success "GROQ_API_KEY configurada"
    fi
fi

# Criar diretórios necessários (serão criados em runtime, mas bom ter)
print_info "Criando diretórios do projeto..."
mkdir -p uploaded_pdfs
mkdir -p chroma_store
print_success "Diretórios criados"

# Verificar instalação das dependências críticas
echo ""
print_info "Verificando instalações críticas..."

python -c "import fastapi; print('FastAPI:', fastapi.__version__)" && print_success "FastAPI OK" || print_error "FastAPI falhou"
python -c "import streamlit; print('Streamlit:', streamlit.__version__)" && print_success "Streamlit OK" || print_error "Streamlit falhou"
python -c "import langchain; print('LangChain:', langchain.__version__)" && print_success "LangChain OK" || print_error "LangChain falhou"
python -c "import chromadb; print('ChromaDB:', chromadb.__version__)" && print_success "ChromaDB OK" || print_error "ChromaDB falhou"

echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║     ✅ Setup Concluído com Sucesso!           ║"
echo "╚════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}Próximos Passos:${NC}"
echo ""
echo "1. Configure sua GROQ_API_KEY no arquivo .env:"
echo "   ${YELLOW}nano .env${NC}"
echo "   Obtenha sua chave em: https://console.groq.com/keys"
echo ""
echo "2. Ative o ambiente virtual (em novos terminais):"
echo "   ${YELLOW}source venv/bin/activate${NC}"
echo ""
echo "3. Inicie o backend FastAPI:"
echo "   ${YELLOW}cd server${NC}"
echo "   ${YELLOW}uvicorn main:app --reload${NC}"
echo ""
echo "4. Em outro terminal, inicie o frontend Streamlit:"
echo "   ${YELLOW}cd client${NC}"
echo "   ${YELLOW}streamlit run app.py${NC}"
echo ""
echo "5. Acesse a aplicação:"
echo "   Frontend: ${BLUE}http://localhost:8501${NC}"
echo "   API Docs: ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo -e "${GREEN}Desenvolvimento Feliz! 🚀${NC}"
echo ""
