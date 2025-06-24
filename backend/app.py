import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, BackgroundTasks, Query, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import json
from datetime import datetime
import shutil

# Importações corrigidas (sem imports relativos)
from backend.config import get_config
from backend.models import FileInfo, ChatRequest, ChatResponse, FileAnalysisRequest, FileAnalysisResponse
from backend.services.file_service import save_uploaded_file, list_csv_files, get_file_metadata
from backend.services.data_service import analyze_csv_data, get_csv_preview
from backend.services.ai_service import process_query_with_langchain

# Configuração do logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Garantir que a pasta de logs existe
os.makedirs('backend/logs', exist_ok=True)

# Inicializar a aplicação FastAPI
app = FastAPI(
    title="CSV Conversation API",
    description="API para interação com arquivos CSV usando linguagem natural",
    version="1.0.0"
)

# Carregar configurações
config = get_config()
UPLOAD_FOLDER = config.UPLOAD_FOLDER

# Adicionar middleware CORS para permitir requisições de diferentes origens
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Garantir que a pasta de uploads existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.get("/")
async def root():
    """
    Endpoint raiz para verificar se a API está funcionando
    """
    return {"status": "ok", "message": "CSV Conversation API está funcionando"}


@app.get("/api/health")
async def health_check():
    """
    Verificação de saúde da API
    """
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/api/files", response_model=List[FileInfo])
async def get_files():
    """
    Lista todos os arquivos CSV disponíveis
    """
    try:
        files = list_csv_files()
        return files
    except Exception as e:
        logger.error(f"Erro ao listar arquivos: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao listar arquivos: {str(e)}")


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Faz upload de um arquivo CSV ou ZIP contendo CSVs
    """
    try:
        if not (file.filename.lower().endswith('.csv') or file.filename.lower().endswith('.zip')):
            raise HTTPException(
                status_code=400, detail="Apenas arquivos CSV e ZIP são permitidos")

        file_info = await save_uploaded_file(file)
        return file_info
    except Exception as e:
        logger.error(f"Erro ao fazer upload do arquivo: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao fazer upload do arquivo: {str(e)}")


@app.get("/api/files/{filename}")
async def get_file_info(filename: str):
    """
    Obtém informações detalhadas sobre um arquivo CSV específico
    """
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404, detail=f"Arquivo '{filename}' não encontrado")

        file_info = get_file_metadata(filename)
        preview = get_csv_preview(filename)

        return {
            **file_info.dict(),
            "preview": preview
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter informações do arquivo: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao obter informações do arquivo: {str(e)}")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Processa uma pergunta sobre os dados CSV usando linguagem natural
    """
    try:
        # Verificar se arquivos são válidos
        file_paths = []
        for filename in request.files:
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if not os.path.exists(file_path):
                raise HTTPException(
                    status_code=404, detail=f"Arquivo '{filename}' não encontrado")
            file_paths.append(file_path)

        if not file_paths:
            raise HTTPException(
                status_code=400, detail="Nenhum arquivo selecionado para análise")

        # Processar a consulta usando langchain
        response = await process_query_with_langchain(request.message, file_paths, request.history)

        return ChatResponse(
            answer=response["answer"],
            # Query SQL/pandas gerada (se aplicável)
            query=response.get("query", ""),
            context=response.get("context", ""),  # Contexto utilizado
            natural_answer=response.get("natural_answer", None),
            files=request.files
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar consulta: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao processar consulta: {str(e)}")


@app.post("/api/analyze", response_model=FileAnalysisResponse)
async def analyze_file(request: FileAnalysisRequest):
    """
    Realiza uma análise detalhada em um arquivo CSV com base em uma consulta
    """
    try:
        file_path = os.path.join(UPLOAD_FOLDER, request.filename)
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404, detail=f"Arquivo '{request.filename}' não encontrado")

        # Analisar dados com pandas
        analysis_result = analyze_csv_data(request.filename, request.query)

        return FileAnalysisResponse(
            filename=request.filename,
            query=request.query,
            result=analysis_result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao analisar arquivo: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao analisar arquivo: {str(e)}")


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """
    Faz o download de um arquivo CSV específico
    """
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404, detail=f"Arquivo '{filename}' não encontrado")

        return FileResponse(path=file_path, filename=filename, media_type="text/csv")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao baixar arquivo: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao baixar arquivo: {str(e)}")
