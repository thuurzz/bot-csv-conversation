import os
import pandas as pd
from datetime import datetime
from fastapi import UploadFile, HTTPException
from typing import List
import shutil
import logging
import sys
import zipfile
import tempfile
import io

# Corrigindo imports
from backend.models import FileInfo
from backend.config import get_config

# Configuração do logger
logger = logging.getLogger(__name__)

# Carregar configurações
config = get_config()
UPLOAD_FOLDER = config.UPLOAD_FOLDER


async def save_uploaded_file(file: UploadFile) -> FileInfo:
    """
    Salva um arquivo enviado e retorna suas informações.
    Agora suporta arquivos ZIP contendo CSVs.

    Args:
        file: Objeto UploadFile do FastAPI

    Returns:
        FileInfo: Informações do arquivo salvo
    """
    try:
        # Garantir que a pasta de uploads existe
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        # Verificar se é um arquivo ZIP
        if file.filename.lower().endswith('.zip'):
            return await handle_zip_upload(file)
        elif file.filename.lower().endswith('.csv'):
            return await handle_csv_upload(file)
        else:
            raise HTTPException(
                status_code=400, detail="Apenas arquivos CSV e ZIP são permitidos")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao salvar arquivo: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao salvar arquivo: {str(e)}")


async def handle_csv_upload(file: UploadFile) -> FileInfo:
    """
    Processa upload de arquivo CSV individual
    """
    try:
        # Criar caminho completo do arquivo
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)

        # Salvar o arquivo
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Obter informações do arquivo
        file_stat = os.stat(file_path)

        # Verificar se é um CSV válido e obter informações adicionais
        try:
            df = pd.read_csv(file_path)
            rows = len(df)
            columns = list(df.columns)

            # Salvar uma prévia das informações do arquivo
            preview_path = os.path.join(
                UPLOAD_FOLDER, f"preview_{file.filename}.info")
            with open(preview_path, "w") as f:
                f.write(f"Arquivo: {file.filename}\n")
                f.write(f"Linhas: {rows}\n")
                f.write(f"Colunas: {', '.join(columns)}\n")
                f.write(f"Tamanho: {file_stat.st_size / 1024:.2f} KB\n")

                # Incluir alguns tipos de dados
                f.write("Tipos de dados:\n")
                for col, dtype in df.dtypes.items():
                    f.write(f"- {col}: {dtype}\n")
        except Exception as e:
            logger.error(f"Erro ao processar o arquivo CSV: {str(e)}")
            raise HTTPException(
                status_code=400, detail=f"Arquivo não é um CSV válido: {str(e)}")

        # Retornar informações do arquivo
        return FileInfo(
            filename=file.filename,
            size_bytes=file_stat.st_size,
            created_at=datetime.fromtimestamp(file_stat.st_ctime),
            rows=rows,
            columns=columns
        )
    except Exception as e:
        logger.error(f"Erro ao processar arquivo CSV: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao processar arquivo CSV: {str(e)}")


async def handle_zip_upload(file: UploadFile) -> FileInfo:
    """
    Processa upload de arquivo ZIP contendo CSVs
    """
    try:
        # Criar um arquivo temporário para o ZIP
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
            shutil.copyfileobj(file.file, temp_zip)
            temp_zip_path = temp_zip.name

        extracted_files = []
        total_rows = 0
        all_columns = set()

        # Extrair arquivos CSV do ZIP
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            # Listar arquivos no ZIP
            file_list = zip_ref.namelist()
            csv_files = [f for f in file_list if f.lower().endswith(
                '.csv') and not f.startswith('__MACOSX/')]

            if not csv_files:
                os.unlink(temp_zip_path)
                raise HTTPException(
                    status_code=400, detail="Nenhum arquivo CSV encontrado no ZIP")

            logger.info(
                f"Encontrados {len(csv_files)} arquivo(s) CSV no ZIP: {', '.join(csv_files)}")

            # Extrair cada arquivo CSV
            for csv_file in csv_files:
                try:
                    # Nome do arquivo sem diretórios
                    clean_filename = os.path.basename(csv_file)

                    # Evitar sobrescrever arquivos existentes
                    counter = 1
                    original_name = clean_filename
                    while os.path.exists(os.path.join(UPLOAD_FOLDER, clean_filename)):
                        name_parts = original_name.rsplit('.', 1)
                        if len(name_parts) == 2:
                            clean_filename = f"{name_parts[0]}_{counter}.{name_parts[1]}"
                        else:
                            clean_filename = f"{original_name}_{counter}"
                        counter += 1

                    # Extrair arquivo do ZIP
                    file_content = zip_ref.read(csv_file)

                    # Verificar se é um CSV válido
                    try:
                        # Usar BytesIO para ler o conteúdo como CSV
                        df = pd.read_csv(io.BytesIO(file_content))

                        # Salvar o arquivo CSV
                        output_path = os.path.join(
                            UPLOAD_FOLDER, clean_filename)
                        with open(output_path, 'wb') as f:
                            f.write(file_content)

                        # Obter estatísticas do arquivo
                        file_stat = os.stat(output_path)

                        # Criar arquivo de prévia
                        preview_path = os.path.join(
                            UPLOAD_FOLDER, f"preview_{clean_filename}.info")
                        with open(preview_path, "w") as f:
                            f.write(
                                f"Arquivo: {clean_filename} (extraído de {file.filename})\n")
                            f.write(f"Linhas: {len(df)}\n")
                            f.write(f"Colunas: {', '.join(df.columns)}\n")
                            f.write(
                                f"Tamanho: {file_stat.st_size / 1024:.2f} KB\n")

                            # Incluir alguns tipos de dados
                            f.write("Tipos de dados:\n")
                            for col, dtype in df.dtypes.items():
                                f.write(f"- {col}: {dtype}\n")

                        extracted_files.append(clean_filename)
                        total_rows += len(df)
                        all_columns.update(df.columns)

                    except Exception as e:
                        logger.warning(
                            f"Arquivo {csv_file} não é um CSV válido e foi ignorado: {str(e)}")
                        continue

                except Exception as e:
                    logger.warning(f"Erro ao extrair {csv_file}: {str(e)}")
                    continue

        # Limpar arquivo temporário
        os.unlink(temp_zip_path)

        if not extracted_files:
            raise HTTPException(
                status_code=400, detail="Nenhum arquivo CSV válido foi extraído do ZIP")

        logger.info(
            f"ZIP processado com sucesso! {len(extracted_files)} arquivo(s) CSV extraído(s): {', '.join(extracted_files)}")

        # Retornar informações resumidas do ZIP
        return FileInfo(
            filename=f"{file.filename} ({len(extracted_files)} CSVs extraídos)",
            size_bytes=sum(os.path.getsize(os.path.join(UPLOAD_FOLDER, f))
                           for f in extracted_files),
            created_at=datetime.now(),
            rows=total_rows,
            columns=list(all_columns)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar arquivo ZIP: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao processar arquivo ZIP: {str(e)}")


def list_csv_files() -> List[FileInfo]:
    """
    Lista todos os arquivos CSV na pasta de uploads

    Returns:
        List[FileInfo]: Lista com informações dos arquivos CSV
    """
    try:
        files = []

        # Garantir que a pasta de uploads existe
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        # Listar arquivos na pasta de uploads
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename.lower().endswith('.csv'):
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file_stat = os.stat(file_path)

                # Obter informações básicas do arquivo
                file_info = FileInfo(
                    filename=filename,
                    size_bytes=file_stat.st_size,
                    created_at=datetime.fromtimestamp(file_stat.st_ctime)
                )

                # Tentar ler o arquivo CSV para obter mais informações
                try:
                    df = pd.read_csv(file_path)
                    file_info.rows = len(df)
                    file_info.columns = list(df.columns)
                except Exception as e:
                    logger.warning(
                        f"Não foi possível ler o arquivo {filename}: {str(e)}")

                files.append(file_info)

        return files
    except Exception as e:
        logger.error(f"Erro ao listar arquivos: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao listar arquivos: {str(e)}")


def get_file_metadata(filename: str) -> FileInfo:
    """
    Obtém metadados detalhados de um arquivo CSV

    Args:
        filename: Nome do arquivo CSV

    Returns:
        FileInfo: Informações do arquivo
    """
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404, detail=f"Arquivo '{filename}' não encontrado")

        # Obter informações básicas do arquivo
        file_stat = os.stat(file_path)

        # Criar objeto FileInfo
        file_info = FileInfo(
            filename=filename,
            size_bytes=file_stat.st_size,
            created_at=datetime.fromtimestamp(file_stat.st_ctime)
        )

        # Tentar ler o arquivo CSV para obter mais informações
        try:
            df = pd.read_csv(file_path)
            file_info.rows = len(df)
            file_info.columns = list(df.columns)
        except Exception as e:
            logger.warning(
                f"Não foi possível ler o arquivo {filename}: {str(e)}")

        return file_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter metadados do arquivo: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao obter metadados do arquivo: {str(e)}")
