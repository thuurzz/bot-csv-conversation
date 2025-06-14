import os
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
import logging
import json
from pathlib import Path
import re

# Importações do LangChain
from langchain import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain.callbacks import get_openai_callback
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain.output_parsers.pydantic import PydanticOutputParser
from langchain.schema import StrOutputParser
from pydantic import BaseModel, Field

# Corrigindo import
from backend.config import get_config

# Configuração do logger
logger = logging.getLogger(__name__)

# Carregar configurações
config = get_config()
UPLOAD_FOLDER = config.UPLOAD_FOLDER

# Chave da API do OpenAI - deve vir das variáveis de ambiente
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Modelo para saída estruturada


class QueryResult(BaseModel):
    answer: str = Field(description="Resposta à consulta do usuário")
    query: str = Field(
        description="Query em pandas para executar nos dados (se aplicável)")
    context: str = Field(
        description="Informações contextuais sobre a resposta")

    # Validator para garantir que answer seja sempre string
    def __init__(self, **data):
        # Converter answer para string se for uma lista
        if 'answer' in data and isinstance(data['answer'], (list, tuple)):
            data['answer'] = "\n".join(map(str, data['answer']))
        super().__init__(**data)


# Parser para saída estruturada
parser = PydanticOutputParser(pydantic_object=QueryResult)


async def process_query_with_langchain(message: str, file_paths: List[str], history: List[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Processa uma consulta em linguagem natural usando LangChain e modelos de IA

    Args:
        message: A mensagem/pergunta do usuário em linguagem natural
        file_paths: Lista de caminhos para os arquivos CSV a serem analisados
        history: Lista de mensagens anteriores da conversa

    Returns:
        Dict[str, str]: Resposta processada pelo modelo
    """
    try:
        # Verificar se temos a chave da API
        if not OPENAI_API_KEY:
            logger.warning(
                "OPENAI_API_KEY não está configurada. Usando resposta simulada.")
            return simulate_response(message, file_paths, history)

        # Coletar informações sobre os arquivos CSV
        file_infos = []
        dataframes = {}

        for file_path in file_paths:
            filename = Path(file_path).name
            try:
                df = pd.read_csv(file_path)
                dataframes[filename] = df

                # Coletar informações sobre o dataframe
                file_info = {
                    "filename": filename,
                    "shape": df.shape,
                    "columns": list(df.columns),
                    "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                    "head": df.head(3).to_string(),
                    "describe": df.describe().to_string() if len(df) > 0 else "DataFrame vazio"
                }
                file_infos.append(file_info)
            except Exception as e:
                logger.error(f"Erro ao ler o arquivo {filename}: {str(e)}")
                file_infos.append({
                    "filename": filename,
                    "error": str(e)
                })

        # Preparar histórico para o prompt
        history_text = ""
        if history and len(history) > 0:
            history_text = "Histórico da conversa:\n"
            for msg in history[-10:]:  # Usar apenas as últimas 10 mensagens para não sobrecarregar
                # Verificar se é um objeto ChatMessage ou um dict
                if hasattr(msg, 'role') and hasattr(msg, 'content'):
                    # É um objeto ChatMessage (Pydantic)
                    role = "Usuário" if msg.role == "user" else "Assistente"
                    content = msg.content
                else:
                    # É um dict (fallback)
                    role = "Usuário" if msg.get("role") == "user" else "Assistente"
                    content = msg.get("content", "")
                history_text += f"{role}: {content}\n"
            history_text += "\n"

        # Criar prompt para o modelo
        template = """
        Você é um assistente especializado em análise de dados que responde perguntas sobre dados contidos em arquivos CSV.
        
        {history}Informações sobre os arquivos disponíveis:
        {file_info}
        
        Quando necessário, gere código Python usando pandas para responder à pergunta do usuário.
        Se a pergunta não puder ser respondida com os dados disponíveis, explique o motivo.
        
        IMPORTANTE: Use o contexto da conversa anterior para fornecer respostas mais precisas e contextualizadas.
        
        Pergunta atual do usuário:
        {message}
        
        IMPORTANTE: Sempre responda com texto em formato string, não em listas. Estas respostas serão processadas por um parser que espera uma string e usado como query em pandas.
        
        Responda usando este formato:
        {format_instructions}
        """

        file_info_str = json.dumps(file_infos, indent=2)

        prompt = PromptTemplate(
            template=template,
            input_variables=["history", "file_info", "message"],
            partial_variables={
                "format_instructions": parser.get_format_instructions()}
        )

        # Configurar modelo
        model = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=OPENAI_API_KEY
        )

        # Criar e executar a cadeia
        chain = prompt | model | parser

        # Obter resposta
        with get_openai_callback() as cb:
            try:
                response = chain.invoke({
                    "history": history_text,
                    "file_info": file_info_str,
                    "message": message
                })
                logger.info(f"Token usage: {cb.total_tokens}")

                # Garantir que a resposta.answer seja sempre string
                if isinstance(response.answer, list):
                    response.answer = "\n".join(map(str, response.answer))

            except Exception as e:
                logger.error(f"Erro na invocação do modelo: {str(e)}")
                # Tentar recuperar o conteúdo da resposta do modelo
                try:
                    # Tentar analisar o erro para extrair a resposta
                    error_str = str(e)
                    match = re.search(
                        r'{"answer": (\[.*?\]|".*?"), "query": .*?}', error_str, re.DOTALL)

                    if match:
                        # Tentar parsear o JSON completo
                        try:
                            raw_json_str = match.group(0)
                            raw_response = json.loads(raw_json_str)

                            answer_content = raw_response.get('answer', '')
                            if isinstance(answer_content, list):
                                answer_string = "\n".join(
                                    map(str, answer_content))
                            else:
                                answer_string = str(answer_content)

                            # Criar resposta manualmente
                            response = QueryResult(
                                answer=answer_string,
                                query=raw_response.get('query', ''),
                                context=raw_response.get('context', '')
                            )
                            logger.info(
                                f"Recuperada resposta do erro: {answer_string[:100]}...")

                        except json.JSONDecodeError as json_err:
                            logger.error(
                                f"Erro ao decodificar JSON da resposta: {json_err}")
                            return simulate_response(message, file_paths, history)
                    else:
                        # Não encontramos um padrão de resposta no erro
                        return simulate_response(message, file_paths, history)

                except Exception as extract_err:
                    logger.error(
                        f"Erro ao tentar extrair resposta do erro: {str(extract_err)}")
                    return simulate_response(message, file_paths, history)

        # Verificar se a resposta contém código pandas e tentar executá-lo
        if response.query and not response.query.lower().startswith("não é possível"):
            try:
                # Extrair e executar o código pandas
                code_to_run = clean_code_block(response.query)

                # Variáveis disponíveis para o código (dataframes)
                local_vars = {
                    f"df_{i+1}": df for i, (_, df) in enumerate(dataframes.items())
                }

                # Se só existe um dataframe, torná-lo disponível como 'df'
                if len(dataframes) == 1:
                    local_vars["df"] = list(dataframes.values())[0]

                # Executar o código
                result = eval(
                    code_to_run, {"pd": pd, "np": np, "__builtins__": {}}, local_vars)

                # Adicionar resultado à resposta
                if isinstance(result, pd.DataFrame):
                    response.context += f"\n\nResultado da consulta (primeiras 5 linhas):\n{result.head(5).to_string()}"
                elif isinstance(result, (np.ndarray, pd.Series, list)):
                    # Formatar arrays ou listas de forma mais legível
                    formatted_result = "\n".join(
                        [f"- {item}" for item in result])
                    # Adicionar resultado à resposta
                    response.answer = f"{response.answer}\n\nValores encontrados:\n{formatted_result}"
                    response.context += f"\n\nResultado da consulta:\n{formatted_result}"
                else:
                    response.context += f"\n\nResultado da consulta: {result}"
                    # Para outros resultados que não são DataFrames, incluí-los também na resposta
                    response.answer += f"\n\nResultado: {result}"
            except Exception as e:
                logger.error(f"Erro ao executar código gerado: {str(e)}")
                response.context += f"\n\nErro ao executar o código gerado: {str(e)}"

        # Garantir novamente que answer seja sempre uma string
        if isinstance(response.answer, list):
            response.answer = "\n".join(map(str, response.answer))
        else:
            response.answer = str(response.answer)

        return {
            "answer": response.answer,
            "query": response.query,
            "context": response.context
        }

    except Exception as e:
        logger.error(f"Erro ao processar consulta com LangChain: {str(e)}")
        return simulate_response(message, file_paths, history)


def clean_code_block(code: str) -> str:
    """Remove marcadores de blocos de código Markdown, se presentes."""
    code = code.strip()
    if code.startswith("```python"):
        code = code[9:]
    elif code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]
    return code.strip()


def simulate_response(message: str, file_paths: List[str], history: List[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Gera uma resposta simulada quando o modelo de IA não está disponível

    Args:
        message: A mensagem/pergunta do usuário
        file_paths: Lista de caminhos para os arquivos CSV
        history: Lista de mensagens anteriores da conversa

    Returns:
        Dict[str, str]: Resposta simulada
    """
    # Coletar informações básicas sobre os arquivos
    file_names = [Path(path).name for path in file_paths]
    file_info = []

    for path in file_paths:
        try:
            filename = Path(path).name
            df = pd.read_csv(path)
            file_info.append({
                "filename": filename,
                "rows": len(df),
                "columns": list(df.columns)
            })
        except Exception as e:
            file_info.append({
                "filename": Path(path).name,
                "error": str(e)
            })

    query_lower = message.lower()

    # Verificar contexto do histórico para respostas mais inteligentes
    context_from_history = ""
    if history and len(history) > 0:
        last_messages = [msg.get("content", "") for msg in history[-3:]]
        context_from_history = f" (Com base na conversa anterior sobre: {', '.join(last_messages[-1:])})"

    # Gerar uma resposta com base em palavras-chave
    if any(word in query_lower for word in ["média", "media", "average", "mean"]):
        return {
            "answer": f"Para calcular a média, eu precisaria analisar os dados numéricos nos arquivos: {', '.join(file_names)}.{context_from_history}",
            "query": "df.select_dtypes(include=['number']).mean()",
            "context": "Esta é uma resposta simulada. Quando a API OpenAI estiver configurada, fornecerei análises reais dos dados."
        }
    elif any(word in query_lower for word in ["contar", "count", "quantos", "quanto"]):
        return {
            "answer": f"Para contar ocorrências, eu analisaria a frequência de valores nos arquivos: {', '.join(file_names)}.{context_from_history}",
            "query": "df.value_counts()",
            "context": "Esta é uma resposta simulada. Quando a API OpenAI estiver configurada, fornecerei análises reais dos dados."
        }
    elif any(word in query_lower for word in ["mostrar", "show", "exibir", "listar", "list"]):
        return {
            "answer": f"Aqui estaria uma prévia dos dados dos arquivos: {', '.join(file_names)}.{context_from_history}",
            "query": "df.head(5)",
            "context": "Esta é uma resposta simulada. Quando a API OpenAI estiver configurada, fornecerei análises reais dos dados."
        }
    else:
        # Resumo dos arquivos disponíveis
        files_info = "\n".join([f"- {info['filename']}: {info.get('rows', 'N/A')} linhas, {len(info.get('columns', []))} colunas"
                                for info in file_info])

        return {
            "answer": f"Posso analisar os seguintes arquivos CSV:\n{files_info}{context_from_history}",
            "query": "",
            "context": "Esta é uma resposta simulada. Por favor, configure a variável de ambiente OPENAI_API_KEY para habilitar respostas reais do modelo de IA."
        }
