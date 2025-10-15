# Em components/chat.py

import streamlit as st
from utils.api import ask_question

def render_chat():
    """
    Renderiza a interface de chat principal, incluindo o histórico,
    a entrada do usuário e as respostas do assistente.
    """
    st.subheader("💬 Converse com seus documentos")

    # Inicializa o histórico do chat com uma mensagem de boas-vindas
    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant", 
            "content": "Olá! Faça o upload dos seus PDFs e me faça uma pergunta sobre eles."
        }]

    # Renderiza o histórico de mensagens existente
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).markdown(msg["content"])

    # Captura a entrada do usuário
    user_input = st.chat_input("Digite sua pergunta aqui...")
    if user_input:
        # Exibe a mensagem do usuário e a salva no histórico
        st.chat_message("user").markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Adiciona o indicador de carregamento enquanto espera a resposta
        with st.spinner("O assistente está pensando..."):
            response = ask_question(user_input)
            
            if response.status_code == 200:
                data = response.json()
                answer = data["response"]
                sources = data.get("sources", [])

                # Exibe a resposta do assistente
                st.chat_message("assistant").markdown(answer)
                
                # Exibe as fontes, se houver
                if sources:
                    sources_text = "📄 **Fontes:**\n" + "\n".join([f"- `{src}`" for src in sources])
                    st.markdown(sources_text)
                
                # Salva a resposta do assistente no histórico (sem as fontes)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            else:
                st.error(f"Erro ao contatar a API: {response.text}")