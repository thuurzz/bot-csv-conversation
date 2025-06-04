import os
import streamlit as st
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

# Carregar variáveis de ambiente com caminho correto
dotenv_path = os.path.join(os.path.dirname(
    os.path.dirname(os.path.dirname(__file__))), 'config', '.env')
load_dotenv(dotenv_path)
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads"))


def upload_file(uploaded_file):
    """
    Salva um arquivo enviado pelo Streamlit na pasta de uploads

    Args:
        uploaded_file: Arquivo enviado pelo Streamlit via file_uploader

    Returns:
        bool: True se o upload foi bem-sucedido, False caso contrário
    """
    try:
        # Garantir que a pasta de uploads existe
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        # Caminho completo para o arquivo de saída
        file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)

        # Verificar se é realmente um CSV válido
        try:
            df = pd.read_csv(uploaded_file)
            # Salvar uma prévia dos dados
            preview_path = os.path.join(
                UPLOAD_FOLDER, f"preview_{uploaded_file.name}.info")
            with open(preview_path, "w") as f:
                f.write(f"Arquivo: {uploaded_file.name}\n")
                f.write(f"Linhas: {len(df)}\n")
                f.write(f"Colunas: {', '.join(df.columns)}\n")
                f.write(
                    f"Tamanho: {df.memory_usage(deep=True).sum() / (1024*1024):.2f} MB\n")
        except Exception as e:
            st.error(f"Erro ao processar CSV: {str(e)}")
            return False

        # Salvar o arquivo
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Adiciona à lista de arquivos enviados pelo usuário
        if "uploaded_files" in st.session_state:
            st.session_state.uploaded_files.add(uploaded_file.name)

        return True
    except Exception as e:
        st.error(f"Erro ao salvar arquivo: {str(e)}")
        return False


def list_available_files():
    """
    Lista todos os arquivos CSV disponíveis na pasta de uploads

    Returns:
        list: Lista com nomes dos arquivos CSV disponíveis
    """
    try:
        files = []
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        # Listar arquivos CSV da pasta de uploads
        for file in os.listdir(UPLOAD_FOLDER):
            if file.lower().endswith('.csv'):
                files.append(file)

        return sorted(files)
    except Exception as e:
        st.error(f"Erro ao listar arquivos: {str(e)}")
        return []


def get_file_preview(filename):
    """
    Retorna uma prévia das informações de um arquivo CSV

    Args:
        filename: Nome do arquivo CSV

    Returns:
        str: Texto com informações sobre o arquivo
    """
    preview_path = os.path.join(UPLOAD_FOLDER, f"preview_{filename}.info")

    if os.path.exists(preview_path):
        with open(preview_path, "r") as f:
            return f.read()

    # Se não tem prévia, gera informações básicas
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            info = f"Arquivo: {filename}\n"
            info += f"Linhas: {len(df)}\n"
            info += f"Colunas: {', '.join(df.columns)}\n"
            return info
        except:
            return f"Arquivo: {filename}"

    return "Arquivo não encontrado"


def remove_file(filename):
    """
    Remove um arquivo CSV e seu arquivo de prévia da pasta de uploads

    Args:
        filename: Nome do arquivo CSV a ser removido

    Returns:
        bool: True se o arquivo foi removido com sucesso, False caso contrário
    """
    try:
        # Caminho completo para o arquivo CSV
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        # Caminho para o arquivo de prévia
        preview_path = os.path.join(UPLOAD_FOLDER, f"preview_{filename}.info")

        # Verifica se o arquivo existe antes de tentar removê-lo
        if not os.path.exists(file_path):
            st.error(f"Arquivo {filename} não encontrado.")
            return False

        # Remove o arquivo CSV
        os.remove(file_path)

        # Remove também o arquivo de prévia se existir
        if os.path.exists(preview_path):
            os.remove(preview_path)

        # Atualiza a sessão se necessário
        if "uploaded_files" in st.session_state and filename in st.session_state.uploaded_files:
            st.session_state.uploaded_files.remove(filename)

        # Se este era o arquivo selecionado, limpa a seleção
        if "selected_file" in st.session_state and st.session_state.selected_file == filename:
            st.session_state.selected_file = None

        return True

    except Exception as e:
        st.error(f"Erro ao remover arquivo: {str(e)}")
        return False
