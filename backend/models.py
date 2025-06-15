from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class FileInfo(BaseModel):
    """Informações sobre um arquivo CSV"""
    filename: str
    size_bytes: int
    created_at: datetime
    rows: Optional[int] = None
    columns: Optional[List[str]] = None

    class Config:
        schema_extra = {
            "example": {
                "filename": "example.csv",
                "size_bytes": 1024,
                "created_at": "2025-06-03T12:00:00",
                "rows": 100,
                "columns": ["column1", "column2", "column3"]
            }
        }


class ChatMessage(BaseModel):
    """Modelo para uma mensagem individual do chat"""
    role: str = Field(..., description="Papel: 'user' ou 'assistant'")
    content: str = Field(..., description="Conteúdo da mensagem")


class ChatRequest(BaseModel):
    """Modelo para requisição de chat com dados CSV"""
    message: str = Field(...,
                         description="Pergunta atual em linguagem natural")
    files: List[str] = Field(...,
                             description="Lista de nomes dos arquivos CSV a serem consultados")
    history: Optional[List[ChatMessage]] = Field(
        default=[], description="Histórico de mensagens anteriores")

    class Config:
        schema_extra = {
            "example": {
                "message": "Qual é a média da coluna 'vendas'?",
                "files": ["vendas.csv"],
                "history": [
                    {"role": "user", "content": "Quantas linhas tem o arquivo?"},
                    {"role": "assistant", "content": "O arquivo tem 1000 linhas."}
                ]
            }
        }


class ChatResponse(BaseModel):
    """Modelo para resposta do chat com dados CSV"""
    answer: str = Field(..., description="Resposta à pergunta")
    query: Optional[str] = Field(
        None, description="Query gerada para análise (se aplicável)")
    context: Optional[str] = Field(
        None, description="Contexto adicional para a resposta")
    files: List[str] = Field(..., description="Arquivos utilizados na análise")

    class Config:
        schema_extra = {
            "example": {
                "answer": "A média da coluna 'vendas' é 5420.35.",
                "query": "df['vendas'].mean()",
                "context": "Analisamos os dados de vendas do arquivo e calculamos a média.",
                "files": ["vendas.csv"]
            }
        }


class FileAnalysisRequest(BaseModel):
    """Modelo para requisição de análise detalhada de arquivo"""
    filename: str = Field(...,
                          description="Nome do arquivo CSV a ser analisado")
    query: str = Field(..., description="Consulta ou instrução para análise")

    class Config:
        schema_extra = {
            "example": {
                "filename": "vendas.csv",
                "query": "Mostrar as 5 maiores vendas por região"
            }
        }


class FileAnalysisResponse(BaseModel):
    """Modelo para resposta de análise detalhada de arquivo"""
    filename: str
    query: str
    result: Dict[str, Any]

    class Config:
        schema_extra = {
            "example": {
                "filename": "vendas.csv",
                "query": "Mostrar as 5 maiores vendas por região",
                "result": {
                    "data": [
                        {"região": "Sul", "valor": 10500},
                        {"região": "Sudeste", "valor": 9200},
                        {"região": "Nordeste", "valor": 8700},
                        {"região": "Centro-Oeste", "valor": 7900},
                        {"região": "Norte", "valor": 6500}
                    ],
                    "columns": ["região", "valor"],
                    "description": "As 5 maiores vendas agrupadas por região"
                }
            }
        }
