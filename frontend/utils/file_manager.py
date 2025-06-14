import os
import streamlit as st
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
import zipfile
import tempfile

# Carregar variáveis de ambiente com caminho correto
dotenv_path = os.path.join(os.path.dirname(
    os.path.dirname(os.path.dirname(__file__))), 'config', '.env')
load_dotenv(dotenv_path)
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads"))


def upload_file(uploaded_file):
    """
    Salva um arquivo enviado pelo Streamlit na pasta de uploads.
    Agora suporta arquivos ZIP contendo CSVs.

    Args:
        uploaded_file: Arquivo enviado pelo Streamlit via file_uploader

    Returns:
        tuple: (bool, list) - (sucesso, lista de arquivos processados)
    """
    try:
        # Garantir que a pasta de uploads existe
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        # Verificar se é um arquivo ZIP
        if uploaded_file.name.lower().endswith('.zip'):
            return handle_zip_upload(uploaded_file)

        # Verificar se é realmente um CSV válido
        elif uploaded_file.name.lower().endswith('.csv'):
            success = handle_csv_upload(uploaded_file)
            return success, [uploaded_file.name] if success else []
        else:
            st.error("Apenas arquivos CSV e ZIP são suportados.")
            return False, []

    except Exception as e:
        st.error(f"Erro ao salvar arquivo: {str(e)}")
        return False, []


def handle_csv_upload(uploaded_file):
    """
    Processa upload de arquivo CSV individual
    """
    try:
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
        st.error(f"Erro ao processar arquivo CSV: {str(e)}")
        return False


def handle_zip_upload(uploaded_file):
    """
    Processa upload de arquivo ZIP contendo CSVs
    VERSÃO SIMPLIFICADA PARA EVITAR LOOP INFINITO

    Returns:
        tuple: (bool, list) - (sucesso, lista de arquivos extraídos)
    """
    try:
        # Criar um arquivo temporário para o ZIP
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
            temp_zip.write(uploaded_file.getbuffer())
            temp_zip_path = temp_zip.name

        extracted_files = []
        max_files = 50  # LIMITE MÁXIMO DE ARQUIVOS PARA EVITAR LOOP INFINITO

        # Extrair arquivos CSV do ZIP
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            # Listar arquivos no ZIP
            file_list = zip_ref.namelist()
            csv_files = [f for f in file_list if f.lower().endswith(
                '.csv') and not f.startswith('__MACOSX/')]

            if not csv_files:
                st.error("Nenhum arquivo CSV encontrado no ZIP.")
                os.unlink(temp_zip_path)
                return False, []

            # LIMITAR NÚMERO DE ARQUIVOS PARA EVITAR PROBLEMAS
            if len(csv_files) > max_files:
                st.warning(
                    f"ZIP contém {len(csv_files)} arquivos CSV. Processando apenas os primeiros {max_files} para evitar problemas.")
                csv_files = csv_files[:max_files]

            st.info(f"Processando {len(csv_files)} arquivo(s) CSV do ZIP...")

            # Extrair cada arquivo CSV com lógica MUITO SIMPLES
            for idx, csv_file in enumerate(csv_files):
                try:
                    # Nome do arquivo sem diretórios
                    original_name = os.path.basename(csv_file)

                    # GERAR NOME ÚNICO DE FORMA MUITO SIMPLES
                    import time
                    timestamp = int(time.time())
                    unique_suffix = f"_{timestamp}_{idx}"

                    # Separar nome e extensão
                    if '.' in original_name:
                        name_part, ext_part = original_name.rsplit('.', 1)
                        final_filename = f"{name_part}{unique_suffix}.{ext_part}"
                    else:
                        final_filename = f"{original_name}{unique_suffix}"

                    # Extrair arquivo do ZIP
                    file_content = zip_ref.read(csv_file)

                    # Verificar se é um CSV válido
                    try:
                        import io
                        df = pd.read_csv(io.BytesIO(file_content))

                        # Salvar o arquivo CSV
                        output_path = os.path.join(
                            UPLOAD_FOLDER, final_filename)
                        with open(output_path, 'wb') as f:
                            f.write(file_content)

                        # Criar arquivo de prévia
                        preview_path = os.path.join(
                            UPLOAD_FOLDER, f"preview_{final_filename}.info")
                        with open(preview_path, "w") as f:
                            f.write(
                                f"Arquivo: {final_filename} (extraído de {uploaded_file.name})\n")
                            f.write(f"Arquivo original: {original_name}\n")
                            f.write(f"Linhas: {len(df)}\n")
                            f.write(f"Colunas: {', '.join(df.columns)}\n")
                            f.write(
                                f"Tamanho: {df.memory_usage(deep=True).sum() / (1024*1024):.2f} MB\n")

                        extracted_files.append(final_filename)

                        # Adicionar à sessão
                        if "uploaded_files" in st.session_state:
                            st.session_state.uploaded_files.add(final_filename)

                        # Mostrar progresso
                        if idx % 10 == 0:
                            st.info(
                                f"Processados {idx + 1}/{len(csv_files)} arquivos...")

                    except Exception as e:
                        st.warning(
                            f"Arquivo {csv_file} não é um CSV válido e foi ignorado: {str(e)}")
                        continue

                except Exception as e:
                    st.warning(f"Erro ao extrair {csv_file}: {str(e)}")
                    continue

        # Limpar arquivo temporário
        os.unlink(temp_zip_path)

        if extracted_files:
            st.success(
                f"ZIP processado com sucesso! {len(extracted_files)} arquivo(s) CSV extraído(s).")
            return True, extracted_files
        else:
            st.error("Nenhum arquivo CSV válido foi extraído do ZIP.")
            return False, []

    except Exception as e:
        st.error(f"Erro ao processar arquivo ZIP: {str(e)}")
        return False, []


def generate_unique_filename(filename, existing_files, used_names, max_attempts=1000):
    """
    Gera um nome de arquivo único de forma segura, evitando loops infinitos

    Args:
        filename: Nome original do arquivo
        existing_files: Set de arquivos já existentes na pasta
        used_names: Set de nomes já usados nesta sessão
        max_attempts: Número máximo de tentativas para evitar loop infinito

    Returns:
        str: Nome único para o arquivo
    """
    import uuid
    from datetime import datetime

    # Se o nome original está disponível, use-o
    if filename not in existing_files and filename not in used_names:
        return filename

    # Separar nome e extensão
    name_parts = filename.rsplit('.', 1)
    if len(name_parts) == 2:
        base_name, extension = name_parts
    else:
        base_name, extension = filename, ""

    # Tentar com contador sequencial (limitado para evitar loop infinito)
    for counter in range(1, max_attempts + 1):
        if extension:
            new_filename = f"{base_name}_{counter}.{extension}"
        else:
            new_filename = f"{base_name}_{counter}"

        if new_filename not in existing_files and new_filename not in used_names:
            return new_filename

    # Se ainda não encontrou nome único, usar timestamp + uuid (última opção)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]

    if extension:
        return f"{base_name}_{timestamp}_{unique_id}.{extension}"
    else:
        return f"{base_name}_{timestamp}_{unique_id}"


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


def remove_all_files():
    """
    Remove todos os arquivos CSV e arquivos de prévia da pasta de uploads

    Returns:
        tuple: (bool, int) - (sucesso, quantidade de arquivos removidos)
    """
    try:
        removed_count = 0

        # Garantir que a pasta de uploads existe
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        # Listar todos os arquivos na pasta de uploads
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)

            # Remover apenas arquivos (não diretórios)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    removed_count += 1
                except Exception as e:
                    st.warning(f"Erro ao remover {filename}: {str(e)}")

        # Limpar estado da sessão
        if "uploaded_files" in st.session_state:
            st.session_state.uploaded_files.clear()

        if "selected_file" in st.session_state:
            st.session_state.selected_file = None

        return True, removed_count

    except Exception as e:
        st.error(f"Erro ao remover todos os arquivos: {str(e)}")
        return False, 0
