import os
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
import logging
import json
from pathlib import Path
import re

# Importações do LangChain - versões atualizadas
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_community.callbacks.manager import get_openai_callback
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# Corrigindo import
from backend.config import get_config

# Configuração do logger com mais detalhes
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backend/logs/api.log'),
        logging.StreamHandler()  # Para mostrar no console
    ]
)
logger = logging.getLogger(__name__)

# Definir nível de log específico para este módulo
logger.setLevel(logging.INFO)

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
    """
    try:
        # Log inicial da consulta
        logger.info(f"🔍 === NOVA CONSULTA RECEBIDA ===")
        logger.info(f"Pergunta do usuário: {message}")
        logger.info(
            f"Arquivos selecionados: {[Path(fp).name for fp in file_paths]}")

        # Verificar se temos a chave da API
        if not OPENAI_API_KEY:
            logger.warning(
                "OPENAI_API_KEY não está configurada. Usando resposta simulada.")
            return simulate_response(message, file_paths, history)

        # Coletar informações sobre os arquivos CSV
        file_infos = []
        dataframes = {}

        logger.info(f"📊 === CARREGANDO DADOS DOS ARQUIVOS ===")
        for file_path in file_paths:
            filename = Path(file_path).name
            try:
                df = pd.read_csv(file_path)
                dataframes[filename] = df

                logger.info(
                    f"✅ Arquivo '{filename}' carregado: {len(df)} linhas, {len(df.columns)} colunas")

                # Análise mais detalhada dos dados para melhor contexto
                sample_data = df.head(10).to_string()  # Mais dados de exemplo
                unique_counts = {}
                for col in df.columns:
                    if df[col].dtype == 'object':
                        # Primeiros 10 valores únicos
                        unique_vals = df[col].dropna().unique()[:10]
                        unique_counts[col] = list(unique_vals)

                file_info = {
                    "filename": filename,
                    "total_rows": len(df),
                    "columns": list(df.columns),
                    "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                    "sample_data": sample_data,
                    "unique_values": unique_counts,
                    "summary_stats": df.describe(include='all').to_string() if len(df) > 0 else "DataFrame vazio"
                }
                file_infos.append(file_info)
            except Exception as e:
                logger.error(f"❌ Erro ao ler o arquivo {filename}: {str(e)}")
                file_infos.append({
                    "filename": filename,
                    "error": str(e)
                })

        # Preparar histórico para o prompt
        history_text = ""
        if history and len(history) > 0:
            logger.info(
                f"📚 Incluindo histórico de {len(history)} mensagens anteriores")
            history_text = "Histórico da conversa:\n"
            for msg in history[-10:]:
                if isinstance(msg, dict):
                    role = "Usuário" if msg.get(
                        "role") == "user" else "Assistente"
                    content = msg.get("content", "")
                else:
                    role = "Usuário" if getattr(
                        msg, 'role', 'user') == "user" else "Assistente"
                    content = getattr(msg, 'content', str(msg))
                history_text += f"{role}: {content}\n"
            history_text += "\n"

        # Prompt melhorado com instruções mais específicas
        template = """
        Você é um assistente especializado em análise de dados CSV. Analise os dados fornecidos e responda à pergunta do usuário.

        {history}

        DADOS DISPONÍVEIS:
        {file_info}

        PERGUNTA DO USUÁRIO: {message}

        INSTRUÇÕES IMPORTANTES:
        1. Analise os dados reais fornecidos acima
        2. Se precisar gerar código pandas, use apenas operações simples e seguras
        3. O dataframe principal está disponível como 'df'
        4. Para contar valores, use df['coluna'].value_counts() ou len(df)
        5. Para filtrar, use df[df['coluna'] == 'valor']
        6. Seja preciso com os dados reais mostrados

        RESPONDA NO FORMATO:
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
            temperature=0.0,  # Mais determinístico
            api_key=OPENAI_API_KEY
        )

        # Criar e executar a cadeia
        chain = prompt | model | parser

        logger.info(f"🤖 === CONSULTANDO MODELO DE IA ===")
        # Obter resposta
        with get_openai_callback() as cb:
            response = chain.invoke({
                "history": history_text,
                "file_info": file_info_str,
                "message": message
            })
            logger.info(f"📊 Tokens utilizados: {cb.total_tokens}")
            logger.info(f"💰 Custo estimado: ${cb.total_cost:.6f}")

        logger.info(f"🎯 === RESPOSTA DO MODELO ===")
        logger.info(f"Resposta: {response.answer}")
        logger.info(f"Query gerada: {response.query}")
        logger.info(f"Contexto: {response.context}")

        # Executar a query se fornecida
        if response.query and response.query.strip():
            logger.info(f"⚙️ === INICIANDO EXECUÇÃO DA QUERY ===")
            query_executed_successfully = False
            try:
                # Execução mais segura da query
                result = execute_pandas_query(response.query, dataframes)

                if result is not None:
                    logger.info(f"✅ Query executada com sucesso!")
                    query_executed_successfully = True

                    # Atualizar a resposta com o resultado real
                    if isinstance(result, (int, float)):
                        # Tratamento especial para cálculos de tempo/atraso
                        if "atraso" in response.query.lower() or "tempo" in response.query.lower():
                            if result < 0:
                                response.answer = f"Em média, as cirurgias começam {abs(result):.1f} minutos ANTES do horário agendado (não há atraso, mas sim antecipação)."
                            elif result == 0:
                                response.answer = f"Em média, as cirurgias começam exatamente no horário agendado (atraso médio de 0 minutos)."
                            else:
                                response.answer = f"Em média, as cirurgias atrasam {result:.1f} minutos para começar."
                        else:
                            response.answer = f"Resultado: {result}"
                        logger.info(f"📈 Resultado numérico: {result}")
                    elif isinstance(result, pd.DataFrame):
                        if len(result) <= 20:  # Se for pequeno, mostrar tudo
                            response.answer = f"Resultado:\n{result.to_string()}"
                        else:
                            response.answer = f"Resultado (primeiras 10 linhas):\n{result.head(10).to_string()}\n\nTotal de {len(result)} registros encontrados."
                        logger.info(
                            f"📊 DataFrame resultado com {len(result)} linhas")
                    elif isinstance(result, pd.Series):
                        response.answer = f"Resultado:\n{result.to_string()}"
                        logger.info(
                            f"📋 Series resultado com {len(result)} valores")
                    elif isinstance(result, tuple):
                        # Formatação especial para tuplas (como nome do médico + quantidade)
                        if len(result) == 2:
                            response.answer = f"Resultado: {result[0]} com {result[1]} ocorrências"
                        else:
                            response.answer = f"Resultado: {result}"
                        logger.info(f"📄 Tupla resultado: {result}")
                    else:
                        response.answer = f"Resultado: {result}"
                        logger.info(
                            f"📄 Outro tipo de resultado: {type(result)}")

                    response.context += f"\n\nQuery executada com sucesso: {response.query}"

            except Exception as e:
                logger.error(f"❌ Erro ao executar query: {str(e)}")
                query_executed_successfully = False

                # IMPORTANTE: Se a query falhou, não retornar dados inventados
                # Retornar uma mensagem de erro clara
                error_message = (
                    f"❌ Não consegui processar sua consulta devido a um erro técnico:\n\n"
                    f"**Erro:** {str(e)}\n\n"
                    f"**Sugestões:**\n"
                    f"• Tente reformular sua pergunta de forma mais específica\n"
                    f"• Verifique se os nomes das colunas estão corretos\n"
                    f"• Para cálculos de tempo, seja mais explícito sobre o formato desejado\n\n"
                    f"**Exemplo de perguntas que funcionam bem:**\n"
                    f"• 'Quantas cirurgias foram realizadas?'\n"
                    f"• 'Qual médico fez mais cirurgias?'\n"
                    f"• 'Liste as cirurgias de ortopedia'"
                )

                return {
                    "answer": error_message,
                    "query": response.query,
                    "context": f"Erro na execução da query: {str(e)}"
                }
        else:
            logger.info(f"ℹ️ Nenhuma query foi gerada ou necessária")

        logger.info(f"🏁 === CONSULTA FINALIZADA ===")
        logger.info(f"Resposta final: {response.answer[:200]}...")

        return {
            "answer": str(response.answer),
            "query": response.query,
            "context": response.context
        }

    except Exception as e:
        logger.error(f"💥 Erro geral ao processar consulta: {str(e)}")
        return simulate_response(message, file_paths, history)


def execute_pandas_query(query: str, dataframes: Dict[str, pd.DataFrame]):
    """
    Executa uma query pandas de forma mais segura
    """
    try:
        # Limpar o código
        code = clean_code_block(query)

        # Log da query que será executada
        logger.info(f"=== EXECUTANDO QUERY ===")
        logger.info(f"Query original: {query}")
        logger.info(f"Query limpa: {code}")

        # Log dos dataframes disponíveis
        for filename, df in dataframes.items():
            logger.info(
                f"Dataframe '{filename}': {len(df)} linhas, {len(df.columns)} colunas")
            logger.info(f"Colunas: {list(df.columns)}")
            logger.info(f"Primeiras 3 linhas:\n{df.head(3).to_string()}")

        # Preparar ambiente seguro com TODAS as funções built-in necessárias
        safe_builtins = {
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            'sum': sum,
            'min': min,
            'max': max,
            'abs': abs,
            'round': round,
            'sorted': sorted,
            'enumerate': enumerate,
            'range': range,
            'zip': zip,
        }

        safe_globals = {
            'pd': pd,
            'np': np,
            '__builtins__': safe_builtins
        }

        # Adicionar dataframes
        local_vars = {}
        for i, (filename, df) in enumerate(dataframes.items()):
            # Fazer uma cópia para não modificar o original
            local_vars[f'df_{i+1}'] = df.copy()

        # Se há apenas um dataframe, disponibilizar como 'df'
        if len(dataframes) == 1:
            local_vars['df'] = list(dataframes.values())[0].copy()
            logger.info(
                f"Dataframe principal 'df' configurado com {len(local_vars['df'])} linhas")

        exec_globals = {**safe_globals, **local_vars}

        # Verificar se é uma query de múltiplas linhas ou com assignments
        has_assignment = '=' in code and not any([
            code.strip().startswith('('),
            '==' in code,  # Comparações não são assignments
            '!=' in code,  # Comparações não são assignments
            '>=' in code,  # Comparações não são assignments
            '<=' in code,  # Comparações não são assignments
        ])
        has_multiple_statements = ';' in code or '\n' in code.strip()

        if has_assignment or has_multiple_statements:
            # Para queries complexas, usar exec
            logger.info(f"Executando query complexa com exec: {code}")

            # Executar e capturar resultado
            local_namespace = exec_globals.copy()
            exec(code, local_namespace)

            # Tentar encontrar variáveis de resultado comuns
            result_vars = ['result', 'media_atraso',
                           'atraso_medio', 'resposta', 'output']
            result = None

            for var in result_vars:
                if var in local_namespace:
                    result = local_namespace[var]
                    logger.info(
                        f"Resultado encontrado na variável '{var}': {result}")
                    break

            # Se não encontrou resultado em variáveis, tentar o último valor definido
            if result is None:
                # Procurar por variáveis que não estavam no namespace original
                new_vars = {k: v for k, v in local_namespace.items()
                            if k not in exec_globals and not k.startswith('__')}
                if new_vars:
                    # Pegar a última variável criada
                    last_var = list(new_vars.keys())[-1]
                    result = new_vars[last_var]
                    logger.info(
                        f"Resultado encontrado na última variável criada '{last_var}': {result}")

        else:
            # Para queries simples, usar eval
            logger.info(f"Executando query simples com eval: {code}")
            result = eval(code, exec_globals)

        # Log do resultado
        logger.info(f"=== RESULTADO DA QUERY ===")
        logger.info(f"Tipo do resultado: {type(result)}")

        if isinstance(result, (int, float, str)):
            logger.info(f"Valor: {result}")
        elif isinstance(result, pd.DataFrame):
            logger.info(
                f"DataFrame resultado: {len(result)} linhas, {len(result.columns)} colunas")
            if len(result) <= 10:
                logger.info(f"Resultado completo:\n{result.to_string()}")
            else:
                logger.info(
                    f"Primeiras 5 linhas:\n{result.head(5).to_string()}")
        elif isinstance(result, pd.Series):
            logger.info(f"Series resultado: {len(result)} valores")
            if len(result) <= 20:
                logger.info(f"Resultado completo:\n{result.to_string()}")
            else:
                logger.info(
                    f"Primeiros 10 valores:\n{result.head(10).to_string()}")
        elif isinstance(result, tuple):
            logger.info(f"Tupla resultado: {result}")
        else:
            # Limitar log se for muito grande
            logger.info(f"Resultado: {str(result)[:500]}...")

        logger.info(f"=== FIM DA EXECUÇÃO ===")
        return result

    except Exception as e:
        logger.error(f"=== ERRO NA EXECUÇÃO DA QUERY ===")
        logger.error(f"Query: {code}")
        logger.error(f"Erro: {str(e)}")
        logger.error(f"=== FIM DO ERRO ===")
        raise e


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
