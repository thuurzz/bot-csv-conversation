import os
import streamlit as st
from dotenv import load_dotenv
import pandas as pd
import uuid
from pathlib import Path
from utils.session import init_session_state, get_username, clear_chat_history
from utils.file_manager import list_available_files, upload_file, get_file_preview, remove_file
from utils.chat import display_chat_messages, process_message, analyze_csv, check_backend_status

# Carregar variáveis de ambiente com caminho correto
dotenv_path = os.path.join(os.path.dirname(
    os.path.dirname(__file__)), 'config', '.env')
load_dotenv(dotenv_path)
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "uploads"))

# Garantir que a pasta de uploads existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Função para processar submissão da mensagem


def handle_message_submit():
    """
    Processa a submissão da mensagem quando o usuário pressiona Enter
    """
    if st.session_state.user_input:
        # Salvamos a mensagem em uma variável para processamento posterior
        st.session_state.submit_question = True
        # Não chamar st.rerun() dentro de callbacks


def file_selected():
    """
    Função chamada quando um arquivo é selecionado no dropdown
    """
    # Atualizar o arquivo selecionado na sessão
    st.session_state.selected_file = st.session_state.file_selector


def main():
    # Configuração da página
    st.set_page_config(
        page_title="Assistente de Análise CSV",
        page_icon="📊",
        layout="wide"
    )

    # Inicializar estado da sessão
    init_session_state()

    # Processar mensagem pendente (se houver)
    if st.session_state.submit_question:
        user_message = st.session_state.user_input
        process_message(user_message)
        # Limpar o campo de input após processar a mensagem
        st.session_state.user_input = ""
        # Resetar a flag
        st.session_state.submit_question = False

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
                # Selecionar automaticamente o novo arquivo enviado
                st.session_state.selected_file = uploaded_file.name
            else:
                st.error("Erro ao fazer upload do arquivo.")

        st.markdown("---")

        # Mostrar arquivos disponíveis
        st.subheader("📁 Arquivos Disponíveis")
        files = list_available_files()

        if files:
            # Se for o primeiro arquivo e nenhum foi selecionado, selecione-o automaticamente
            if len(files) == 1 and not st.session_state.selected_file:
                st.session_state.selected_file = files[0]

            # Usar o arquivo selecionado como valor inicial
            default_ix = 0
            if st.session_state.selected_file in files:
                default_ix = files.index(st.session_state.selected_file)

            # Usar key='file_selector' para a callback
            selected_file = st.selectbox(
                "Selecione um arquivo para consultas",
                files,
                index=default_ix,
                key="file_selector",
                on_change=file_selected
            )

            if selected_file:
                with st.expander("Detalhes do arquivo", expanded=True):
                    preview = get_file_preview(selected_file)
                    st.text(preview)

                # Botão para perguntar sobre o arquivo específico
                if st.button(f"Perguntar sobre {selected_file}"):
                    question = f"Me fale sobre o arquivo {selected_file}"
                    process_message(question)
                    # O st.rerun() não é necessário aqui, pois o processo de submissão
                    # já será acionado pela atualização do estado

                # Botão para remover o arquivo selecionado
                if st.button("🗑️ Remover arquivo selecionado", key="remove_selected_sidebar"):
                    if remove_file(selected_file):
                        st.success(
                            f"Arquivo '{selected_file}' removido com sucesso!")
                        st.session_state.selected_file = None
                        st.rerun()
                    else:
                        st.error(
                            f"Erro ao remover o arquivo '{selected_file}'.")
        else:
            st.info(
                "Nenhum arquivo disponível. Faça upload de um arquivo CSV para começar.")

    # Área principal - duas colunas
    col1, col2 = st.columns([2, 1])

    with col1:
        # Área do chat
        st.title("💬 Chat com o Assistente CSV")

        # Mostrar o arquivo selecionado ao usuário
        if st.session_state.selected_file:
            st.caption(
                f"📄 Arquivo selecionado: **{st.session_state.selected_file}**")

        display_chat_messages()

        # Campo de mensagem configurado para enviar somente quando pressionar Enter
        st.text_input(
            "Digite sua pergunta sobre os dados e pressione Enter para enviar...",
            key="user_input",
            placeholder="Ex: Quantas linhas tem o arquivo? Quais são as colunas?",
            on_change=handle_message_submit
        )

        # Dica para o usuário
        st.caption("💡 Pressione Enter para enviar sua pergunta")

        # Botões de sugestões
        st.write("Ou tente uma destas perguntas:")
        sugestoes_col1, sugestoes_col2 = st.columns(2)

        with sugestoes_col1:
            if st.button("Listar todos os arquivos"):
                process_message("Listar todos os arquivos CSV disponíveis")
                st.rerun()  # Recarregar a página para mostrar a resposta imediatamente

            if st.button("Mostrar estatísticas básicas"):
                process_message("Mostrar estatísticas básicas dos dados")
                st.rerun()  # Recarregar a página para mostrar a resposta imediatamente

        with sugestoes_col2:
            if st.button("Verificar colunas"):
                process_message("Quais são as colunas dos arquivos?")
                st.rerun()  # Recarregar a página para mostrar a resposta imediatamente

            if st.button("Limpar Chat"):
                clear_chat_history()
                st.rerun()  # Recarregar a página para limpar o histórico imediatamente

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
        3. Digite uma pergunta e pressione Enter para enviar
        4. O assistente analisará os dados e responderá
        
        **Recursos:**
        - Análise de dados CSV via perguntas em linguagem natural
        - Visualizações de dados interativas
        - Exportação de análises
        """)

        # Status do sistema com verificação real do backend
        st.subheader("📡 Status do Sistema")
        st.success("Frontend: Operacional")

        # Verificar status do backend
        backend_connected, backend_message = check_backend_status()
        if backend_connected:
            st.success(backend_message)
        else:
            st.error(backend_message)

        # Mostrar arquivos em tabela compacta
        if files:
            st.subheader("Arquivos Disponíveis")

            # Criando colunas para cada arquivo com botão de remover
            for file in files:
                col_file, col_remove = st.columns([3, 1])

                with col_file:
                    st.write(file)

                with col_remove:
                    if st.button("🗑️ Remover", key=f"remove_{file}"):
                        if remove_file(file):
                            st.success(
                                f"Arquivo '{file}' removido com sucesso!")
                            st.rerun()
                        else:
                            st.error(f"Erro ao remover arquivo '{file}'.")

            # Mostrar também em formato de tabela para referência
            st.caption("Lista completa de arquivos:")
            df_files = pd.DataFrame({"Arquivo": files})
            st.dataframe(df_files, hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
