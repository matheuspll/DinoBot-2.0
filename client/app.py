# Em client/app.py

import streamlit as st
from components.upload import render_uploader
from components.history_download import render_history_download
from components.chatUI import render_chat

# Configuração da página (deve ser o primeiro comando do Streamlit)
st.set_page_config(page_title="RagBot 2.0 | converse com seus acórdãos", layout="wide")

# Título Principal da Aplicação
st.title("🤖 RagBot 2.0: Converse com seus Acórdãos")
st.caption("Desenvolvido para análise de documentos da SEFAZ Acre")

# Renderiza os componentes da barra lateral
with st.sidebar:
    render_uploader()
    st.divider() # Adiciona uma linha divisória
    render_history_download()

# Renderiza o componente principal do chat no corpo da página
render_chat()