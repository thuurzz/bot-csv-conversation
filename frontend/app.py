import os
import streamlit as st
from dotenv import load_dotenv
import pandas as pd
import uuid
from pathlib import Path
from utils.session import init_session_state, get_username, clear_chat_history
from utils.file_manager import list_available_files, upload_file, get_file_preview
from utils.chat import display_chat_messages, process_message, analyze_csv

# Carregar variáveis de ambiente com caminho correto
dotenv_path = os.path.join(os.path.dirname(
    os.path.dirname(__file__)), 'config', '.env')
load_dotenv(dotenv_path)
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "uploads"))

# Garantir que a pasta de uploads existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def main():
    # Configuração da página
    st.set_page_config(
        page_title="Assistente de Análise CSV",
        page_icon="📊",
        layout="wide"
    )

    # Inicializar estado da sessão
    init_session_state()

    # Sidebar
    with st.sidebar:
        st.title("📊 Assistente CSV")

        # Área de login/usuário
        st.subheader("👤 Perfil do Usuário")
        username = get_username()
        st.write(f"Conectado como: **{username}**")

        st.markdown("---")

        # Seção de Upload
        st.subheader("📤 Upload de Arquivos")
        uploaded_file = st.file_uploader("Escolha um arquivo CSV", type="csv")

        # Upload de arquivo
        if uploaded_file:
            if upload_file(uploaded_file):
                st.success(
                    f"Arquivo '{uploaded_file.name}' enviado com sucesso!")
            else:
                st.error("Erro ao fazer upload do arquivo.")

        st.markdown("---")

        # Mostrar arquivos disponíveis
        st.subheader("📁 Arquivos Disponíveis")
        files = list_available_files()

        if files:
            selected_file = st.selectbox(
                "Selecione um arquivo para ver detalhes", files)
            if selected_file:
                with st.expander("Detalhes do arquivo", expanded=True):
                    preview = get_file_preview(selected_file)
                    st.text(preview)

                # Botão para perguntar sobre o arquivo específico
                if st.button(f"Perguntar sobre {selected_file}"):
                    question = f"Me fale sobre o arquivo {selected_file}"
                    process_message(question)
                    st.rerun()
        else:
            st.info(
                "Nenhum arquivo disponível. Faça upload de um arquivo CSV para começar.")

    # Área principal - duas colunas
    col1, col2 = st.columns([2, 1])

    with col1:
        # Área do chat
        st.title("💬 Chat com o Assistente CSV")

        display_chat_messages()

        # Campo de mensagem
        user_input = st.text_input("Digite sua pergunta sobre os dados...", key="user_input",
                                   placeholder="Ex: Quantas linhas tem o arquivo? Quais são as colunas?")

        # Botões de sugestões
        st.write("Ou tente uma destas perguntas:")
        sugestoes_col1, sugestoes_col2 = st.columns(2)

        with sugestoes_col1:
            if st.button("Listar todos os arquivos"):
                process_message("Listar todos os arquivos CSV disponíveis")
                st.rerun()

            if st.button("Mostrar estatísticas básicas"):
                process_message("Mostrar estatísticas básicas dos dados")
                st.rerun()

        with sugestoes_col2:
            if st.button("Verificar colunas"):
                process_message("Quais são as colunas dos arquivos?")
                st.rerun()

            if st.button("Limpar Chat"):
                clear_chat_history()
                st.rerun()

        # Processamento da mensagem
        if user_input:
            process_message(user_input)
            # Limpar o campo de entrada após enviar
            st.session_state.user_input = ""
            # Rerun para atualizar a interface
            st.rerun()

    with col2:
        # Informações sobre o projeto
        st.title("ℹ️ Sobre")
        st.info("""
        **Bot de Conversação CSV**
        
        Este assistente permite fazer perguntas sobre seus dados CSV 
        usando linguagem natural.
        
        **Como usar:**
        1. Faça upload de arquivos CSV na barra lateral
        2. Selecione um arquivo para ver detalhes
        3. Digite uma pergunta ou use as sugestões
        4. O assistente analisará os dados e responderá
        
        **Em breve:**
        - Integração com backend para análises avançadas
        - Visualizações de dados interativas
        - Exportação de análises
        """)

        # Status da conexão com backend (para futuras implementações)
        st.subheader("📡 Status do Sistema")
        st.success("Frontend: Operacional")
        st.error("Backend: Não conectado (em desenvolvimento)")

        # Mostrar arquivos em tabela compacta
        if files:
            st.subheader("Arquivos Disponíveis")
            df_files = pd.DataFrame({"Arquivo": files})
            st.dataframe(df_files, hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
