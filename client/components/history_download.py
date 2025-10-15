# Em components/history_download.py

import streamlit as st

def render_history_download():
    """
    Renderiza um botão na barra lateral para baixar o histórico do chat,
    se um histórico existir no st.session_state.
    """
    # Verifica se a chave 'messages' existe e não está vazia no session_state
    if "messages" in st.session_state and st.session_state.messages:
        
        # Formata o histórico do chat para um formato de texto legível
        formatted_chat_history = "\n\n".join(
            [f"{msg['role'].upper()}: {msg['content']}" for msg in st.session_state.messages]
        )
        
        # Coloca o botão na barra lateral para manter a consistência da UI
        st.sidebar.download_button(
            label="Download Chat History",
            data=formatted_chat_history,
            file_name="chat_history.txt",
            mime="text/plain"
        )