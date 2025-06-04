import streamlit as st
import uuid


def init_session_state():
    """
    Inicializa variáveis de estado na sessão do Streamlit se não existirem
    """
    if "username" not in st.session_state:
        # Gera um nome de usuário anônimo se não estiver definido
        st.session_state.username = f"Usuário_{uuid.uuid4().hex[:6]}"

    if "messages" not in st.session_state:
        # Inicializa o histórico de mensagens com uma mensagem de boas-vindas
        st.session_state.messages = [
            {"role": "assistant", "content": "Olá! Sou seu assistente para análise de dados CSV. Como posso ajudar hoje?"}
        ]

    if "uploaded_files" not in st.session_state:
        # Rastreia os arquivos que o usuário já fez upload
        st.session_state.uploaded_files = set()

    if "selected_file" not in st.session_state:
        # Armazena o arquivo atualmente selecionado para consultas
        st.session_state.selected_file = None

    if "submit_question" not in st.session_state:
        # Flag para controlar o envio de perguntas
        st.session_state.submit_question = False


def get_username():
    """
    Retorna o nome de usuário atual e permite alteração
    """
    username = st.text_input("Seu nome de usuário:",
                             value=st.session_state.username)

    # Atualizar nome de usuário se foi alterado
    if username != st.session_state.username:
        st.session_state.username = username

    return st.session_state.username


def clear_chat_history():
    """
    Limpa o histórico de mensagens
    """
    st.session_state.messages = [
        {"role": "assistant", "content": "Histórico de chat limpo. Como posso ajudar?"}
    ]
