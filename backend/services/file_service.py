import os
import pandas as pd
from datetime import datetime
from fastapi import UploadFile, HTTPException
from typing import List
import shutil
import logging
import sys

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
    Salva um arquivo enviado e retorna suas informações

    Args:
        file: Objeto UploadFile do FastAPI

    Returns:
        FileInfo: Informações do arquivo salvo
    """
    try:
        # Garantir que a pasta de uploads existe
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
        logger.error(f"Erro ao salvar arquivo: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao salvar arquivo: {str(e)}")


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
