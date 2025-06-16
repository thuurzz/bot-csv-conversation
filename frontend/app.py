import os
import streamlit as st
from dotenv import load_dotenv
import pandas as pd
import uuid
from pathlib import Path
from utils.session import init_session_state, get_username, clear_chat_history
from utils.file_manager import list_available_files, upload_file, get_file_preview, remove_file, remove_all_files
from utils.chat import display_chat_messages, process_message, check_backend_status

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
        uploaded_file = st.file_uploader(
            "Escolha um arquivo CSV ou ZIP contendo CSVs",
            type=["csv", "zip"],
            help="Você pode enviar arquivos CSV individuais ou um arquivo ZIP contendo múltiplos CSVs"
        )

        # Upload de arquivo
        if uploaded_file:
            # Verificar se este arquivo já foi processado nesta sessão
            file_key = f"{uploaded_file.name}_{uploaded_file.size}"

            if "processed_uploads" not in st.session_state:
                st.session_state.processed_uploads = set()

            if file_key not in st.session_state.processed_uploads:
                success, processed_files = upload_file(uploaded_file)
                if success:
                    st.success(
                        f"Arquivo '{uploaded_file.name}' enviado com sucesso!")
                    # Marcar este arquivo como processado
                    st.session_state.processed_uploads.add(file_key)
                    # Selecionar o primeiro arquivo processado
                    if processed_files:
                        st.session_state.selected_file = processed_files[0]
                    # Recarregar APENAS uma vez
                    st.rerun()
                else:
                    st.error("Erro ao fazer upload do arquivo.")
            # Se já foi processado, não fazer nada (evita loop infinito)

        st.markdown("---")

        # Mostrar arquivos disponíveis
        st.subheader("📁 Arquivos Disponíveis")
        files = list_available_files()

        if files:
            # Botão para remover todos os arquivos
            st.warning(
                f"📊 Total: {len(files)} arquivo(s) na base de conhecimento")

            if st.button("🗑️ LIMPAR TODA A BASE DE CONHECIMENTO", type="secondary", use_container_width=True):
                success, removed_count = remove_all_files()
                if success:
                    st.success(
                        f"✅ Base de conhecimento limpa! {removed_count} arquivo(s) removido(s).")
                    st.rerun()
                else:
                    st.error("❌ Erro ao limpar a base de conhecimento.")

            st.markdown("---")

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

            # Mostrar lista compacta de arquivos na sidebar
            st.markdown("---")
            st.caption("📋 Lista de arquivos:")
            for file in files:
                st.text(f"• {file}")

        else:
            st.info(
                "Nenhum arquivo disponível. Faça upload de um arquivo CSV para começar.")

        st.markdown("---")

        # Status do Sistema na Sidebar
        st.subheader("📡 Status da Conexão")

        # Verificar status do backend
        backend_connected, backend_message = check_backend_status()
        if backend_connected:
            st.success(f"Backend: {backend_message}")
        else:
            st.error(f"Backend: {backend_message}")

        # Botão para recarregar o status abaixo da mensagem
        if st.button("🔄 Testar conexão", help="Verificar conexão novamente", key="refresh_backend_status"):
            st.rerun()

    # Área principal - Layout mais focado no chat
    st.title("💬 Chat com o Assistente CSV")

    # Expander com instruções sempre disponível
    with st.expander("❓ Como usar", expanded=False):
        st.markdown("""
        **Como usar o Assistente CSV:**
        
        1. **Upload de Arquivos**: Faça upload de arquivos CSV ou ZIP na barra lateral
        2. **Seleção**: Selecione um arquivo para análise na lista disponível
        3. **Perguntas**: Digite perguntas em linguagem natural sobre seus dados
        4. **Resultados**: O assistente analisará os dados e fornecerá respostas detalhadas
        
        **Exemplos de perguntas:**
        - "Quantas linhas tem o arquivo?"
        - "Quais são as colunas disponíveis?"
        - "Mostre as primeiras 10 linhas"
        - "Calcule a média da coluna X"
        - "Crie um gráfico das vendas por mês"
        
        **Recursos disponíveis:**
        - Análise estatística automática
        - Geração de gráficos e visualizações
        - Filtros e consultas personalizadas
        - Histórico de conversas
        """)

    # Mostrar o arquivo selecionado ao usuário
    if st.session_state.selected_file:
        st.info(f"📄 Arquivo selecionado: **{st.session_state.selected_file}**")

    # Área do chat - agora ocupa mais espaço
    display_chat_messages()

    # Campo de mensagem
    st.text_input(
        "Digite sua pergunta sobre os dados e pressione Enter para enviar...",
        key="user_input",
        placeholder="Ex: Quantas linhas tem o arquivo? Quais são as colunas?",
        on_change=handle_message_submit
    )

    # Dica para o usuário
    st.caption("💡 Pressione Enter para enviar sua pergunta")

    # Botões de sugestões em layout horizontal
    st.write("**Sugestões rápidas:**")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("📋 Listar arquivos", use_container_width=True):
            process_message("Listar todos os arquivos CSV disponíveis")
            st.rerun()

    with col2:
        if st.button("📊 Estatísticas", use_container_width=True):
            process_message("Mostrar estatísticas básicas dos dados")
            st.rerun()

    with col3:
        if st.button("🏷️ Verificar colunas", use_container_width=True):
            process_message("Quais são as colunas dos arquivos?")
            st.rerun()

    with col4:
        if st.button("🧹 Limpar Chat", use_container_width=True):
            clear_chat_history()
            st.rerun()


if __name__ == "__main__":
    main()
