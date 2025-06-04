import os
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import json
import logging

# Corrigindo import
from backend.config import get_config

# Configuração do logger
logger = logging.getLogger(__name__)

# Carregar configurações
config = get_config()
UPLOAD_FOLDER = config.UPLOAD_FOLDER


def get_csv_preview(filename: str, max_rows: int = 5) -> List[Dict[str, Any]]:
    """
    Obtém uma prévia dos dados de um arquivo CSV

    Args:
        filename: Nome do arquivo CSV
        max_rows: Número máximo de linhas a retornar

    Returns:
        List[Dict[str, Any]]: Lista de dicionários com os dados
    """
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        df = pd.read_csv(file_path)

        # Converter para dicionários e garantir valores serializáveis
        preview = df.head(max_rows).to_dict(orient='records')

        # Garantir que todos os valores são serializáveis
        for item in preview:
            for key, value in item.items():
                if pd.isna(value):
                    item[key] = None
                elif isinstance(value, np.integer):
                    item[key] = int(value)
                elif isinstance(value, np.floating):
                    item[key] = float(value)
                elif isinstance(value, np.ndarray):
                    item[key] = value.tolist()
                elif isinstance(value, pd.Timestamp):
                    item[key] = value.isoformat()

        return preview
    except Exception as e:
        logger.error(f"Erro ao obter prévia do arquivo {filename}: {str(e)}")
        return []


def analyze_csv_data(filename: str, query: str) -> Dict[str, Any]:
    """
    Analisa dados de um arquivo CSV com base em uma consulta

    Args:
        filename: Nome do arquivo CSV
        query: Consulta ou instrução para análise

    Returns:
        Dict[str, Any]: Resultado da análise
    """
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        df = pd.read_csv(file_path)

        # Lógica básica para analisar os dados com base na consulta
        # Esta é uma implementação simples para fins de demonstração
        result = {
            "description": f"Análise de '{query}' no arquivo {filename}",
            "data": None,
            "columns": list(df.columns),
            "summary": {}
        }

        query_lower = query.lower()

        # Análise estatística básica
        if "média" in query_lower or "media" in query_lower:
            # Encontrar colunas numéricas mencionadas
            numeric_columns = df.select_dtypes(include=['number']).columns
            stats = {}

            for col in numeric_columns:
                if col.lower() in query_lower:
                    stats[col] = {
                        "mean": float(df[col].mean()),
                        "min": float(df[col].min()),
                        "max": float(df[col].max()),
                        "median": float(df[col].median())
                    }

            if not stats:
                # Se nenhuma coluna específica foi mencionada, incluir todas as numéricas
                for col in numeric_columns:
                    stats[col] = {
                        "mean": float(df[col].mean()),
                        "min": float(df[col].min()),
                        "max": float(df[col].max()),
                        "median": float(df[col].median())
                    }

            result["data"] = stats
            result[
                "description"] = f"Estatísticas das colunas numéricas para a consulta: '{query}'"

        # Contagens por categoria
        elif "contar" in query_lower or "contagem" in query_lower:
            # Tentar encontrar as colunas mencionadas
            for col in df.columns:
                if col.lower() in query_lower:
                    value_counts = df[col].value_counts().head(10).to_dict()
                    result["data"] = [{"valor": k, "contagem": int(
                        v)} for k, v in value_counts.items()]
                    result["description"] = f"Contagem dos valores na coluna '{col}'"
                    break

            # Se nenhuma coluna específica foi encontrada
            if result["data"] is None:
                # Usar a primeira coluna categórica
                categorical_cols = df.select_dtypes(include=['object']).columns
                if len(categorical_cols) > 0:
                    col = categorical_cols[0]
                    value_counts = df[col].value_counts().head(10).to_dict()
                    result["data"] = [{"valor": k, "contagem": int(
                        v)} for k, v in value_counts.items()]
                    result["description"] = f"Contagem dos valores na coluna '{col}'"

        # Top N linhas
        elif "top" in query_lower or "maiores" in query_lower:
            # Tentar encontrar a coluna para ordenação
            sort_col = None
            for col in df.select_dtypes(include=['number']).columns:
                if col.lower() in query_lower:
                    sort_col = col
                    break

            if sort_col:
                # Extrair número N da consulta
                import re
                n_match = re.search(r'\b(\d+)\b', query)
                n = 5  # padrão
                if n_match:
                    n = int(n_match.group(1))

                top_data = df.sort_values(by=sort_col, ascending=False).head(n)

                # Converter para formato serializável
                records = top_data.to_dict(orient='records')
                for record in records:
                    for key, value in record.items():
                        if pd.isna(value):
                            record[key] = None
                        elif isinstance(value, np.integer):
                            record[key] = int(value)
                        elif isinstance(value, np.floating):
                            record[key] = float(value)
                        elif isinstance(value, np.ndarray):
                            record[key] = value.tolist()
                        elif isinstance(value, pd.Timestamp):
                            record[key] = value.isoformat()

                result["data"] = records
                result["description"] = f"Top {n} valores ordenados pela coluna '{sort_col}'"

        # Descrição geral do dataset
        else:
            # Estatísticas básicas
            num_desc = df.describe().to_dict()

            # Converter para formato serializável
            for col in num_desc:
                for stat, value in num_desc[col].items():
                    if isinstance(value, np.integer):
                        num_desc[col][stat] = int(value)
                    elif isinstance(value, np.floating):
                        num_desc[col][stat] = float(value)

            # Contagens de valores nulos
            null_counts = df.isnull().sum().to_dict()
            null_counts = {k: int(v) for k, v in null_counts.items()}

            # Tipos de dados
            dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}

            result["summary"] = {
                "numeric_stats": num_desc,
                "null_counts": null_counts,
                "dtypes": dtypes,
                "total_rows": len(df),
                "total_columns": len(df.columns)
            }

            # Pré-visualização dos dados
            result["data"] = get_csv_preview(filename, max_rows=5)
            result["description"] = f"Descrição geral dos dados para a consulta: '{query}'"

        return result

    except Exception as e:
        logger.error(f"Erro ao analisar dados: {str(e)}")
        return {
            "error": str(e),
            "description": f"Erro ao analisar os dados para a consulta: '{query}'",
        }
