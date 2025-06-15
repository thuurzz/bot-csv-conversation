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

# Garantir que o diretório de logs existe - CORRIGIDO para usar o diretório correto
logs_dir = Path(__file__).parent.parent / "logs"  # Usar a pasta logs/ da raiz
logs_dir.mkdir(parents=True, exist_ok=True)

# Configuração do logger principal
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(logs_dir / 'api.log'),
        logging.StreamHandler()  # Para mostrar no console
    ]
)
logger = logging.getLogger(__name__)

# Logger específico para interações com IA
ai_logger = logging.getLogger('ai_interactions')
ai_logger.setLevel(logging.INFO)

# Remover handlers existentes para evitar duplicação
for handler in ai_logger.handlers[:]:
    ai_logger.removeHandler(handler)

# Handler para arquivo de logs de IA separado
ai_log_file = logs_dir / 'ai_interactions.log'
ai_handler = logging.FileHandler(ai_log_file)
ai_formatter = logging.Formatter(
    '%(asctime)s - AI_INTERACTION - %(levelname)s - %(message)s')
ai_handler.setFormatter(ai_formatter)
ai_logger.addHandler(ai_handler)

# Evitar propagação para o logger pai
ai_logger.propagate = False

# Definir nível de log específico para este módulo
logger.setLevel(logging.INFO)

# Teste inicial do logging
logger.info("=== AI SERVICE INICIADO ===")
ai_logger.info("=== LOGGER DE IA CONFIGURADO E FUNCIONANDO ===")

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
        # Log inicial da consulta - SIMPLIFICADO
        logger.info(
            f"🔍 Nova consulta: '{message[:50]}{'...' if len(message) > 50 else ''}'")
        logger.info(f"📁 Arquivos: {len(file_paths)} arquivo(s)")

        # Verificar se temos a chave da API
        if not OPENAI_API_KEY:
            logger.warning(
                "OPENAI_API_KEY não está configurada. Usando resposta simulada.")
            return simulate_response(message, file_paths, history)

        # Coletar informações sobre os arquivos CSV
        file_infos = {}
        dataframes = {}

        logger.info(f"📊 Carregando {len(file_paths)} arquivo(s)...")
        for file_path in file_paths:
            filename = Path(file_path).name
            try:
                df = pd.read_csv(file_path)
                dataframes[filename] = df

                logger.info(
                    f"✅ {filename}: {len(df)} linhas, {len(df.columns)} colunas")

                # Análise REDUZIDA dos dados - apenas estrutura, não valores
                # APENAS 2 linhas de exemplo, sem estatísticas que revelem resultados
                # Reduzido de 10 para 2 linhas
                sample_data = df.head(2).to_string()

                # INFORMAÇÕES BÁSICAS apenas - sem estatísticas que revelem resultados
                file_info = {
                    "filename": filename,
                    "total_rows": len(df),
                    "columns": list(df.columns),
                    "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                    "sample_data": sample_data,
                    "structure_info": f"Dataset com {len(df)} registros e {len(df.columns)} colunas. Tipos: {df.dtypes.value_counts().to_dict()}"
                }
                file_infos[filename] = file_info
            except Exception as e:
                logger.error(f"❌ Erro ao ler o arquivo {filename}: {str(e)}")
                file_infos[filename] = {
                    "error": str(e)
                }

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
        2. Use EXATAMENTE os nomes das colunas como mostrado nos dados
        3. NUNCA truncar ou abreviar nomes de colunas - use o nome completo
        4. O dataframe principal está disponível como 'df'
        5. Se há múltiplos arquivos, use df_1, df_2, etc. para acessar específicos
        6. Para contar valores, use df['coluna'].value_counts() ou len(df)
        7. Para filtrar, use df[df['coluna'] == 'valor']
        8. Seja preciso com os dados reais mostrados
        9. Se a pergunta envolve múltiplos arquivos, considere usar df_1, df_2, etc. ou fazer merge/join se apropriado
        10. Se perguntado sobre valores, nas querys formate o resultado como valor monetário (ex: R$ 1.234,56) ou percentual (ex: 12,34%)

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
            model="gpt-4o",
            temperature=0.0,  # Mais determinístico
            api_key=OPENAI_API_KEY
        )

        # Criar e executar a cadeia
        chain = prompt | model | parser

        # NOVO: Log detalhado do que está sendo enviado para o modelo
        formatted_prompt = prompt.format(
            history=history_text,
            file_info=file_info_str,
            message=message,
            format_instructions=parser.get_format_instructions()
        )

        # Log do prompt completo que será enviado
        try:
            log_file_path = logs_dir / 'ai_interactions.log'
            with open(log_file_path, 'a', encoding='utf-8') as log_file:
                log_file.write(f"\n{'='*80}\n")
                log_file.write(f"TIMESTAMP: {pd.Timestamp.now()}\n")
                log_file.write(f"PERGUNTA DO USUÁRIO: {message}\n")
                log_file.write(
                    f"ARQUIVOS: {[Path(fp).name for fp in file_paths]}\n")
                log_file.write(
                    f"TAMANHO DO PROMPT: {len(formatted_prompt)} caracteres\n")
                log_file.write(f"{'='*80}\n")
                log_file.write(f"PROMPT COMPLETO ENVIADO PARA O MODELO:\n")
                log_file.write(f"{'='*80}\n")
                log_file.write(formatted_prompt)
                log_file.write(f"\n{'='*80}\n\n")
                log_file.flush()  # Forçar gravação
        except Exception as e:
            logger.error(f"Erro ao escrever log manual: {e}")

        logger.info(f"🤖 === CONSULTANDO MODELO DE IA ===")
        logger.info(f"📏 Tamanho do prompt: {len(formatted_prompt)} caracteres")

        # Obter resposta
        with get_openai_callback() as cb:
            response = chain.invoke({
                "history": history_text,
                "file_info": file_info_str,
                "message": message
            })
            logger.info(f"📊 Tokens utilizados: {cb.total_tokens}")
            logger.info(f"💰 Custo estimado: ${cb.total_cost:.6f}")

            # Log da resposta recebida do modelo - INCLUINDO TODAS AS INFORMAÇÕES
            try:
                log_file_path = logs_dir / 'ai_interactions.log'
                with open(log_file_path, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"RESPOSTA RECEBIDA DO MODELO:\n")
                    log_file.write(f"{'='*50}\n")
                    log_file.write(f"Answer: {response.answer}\n")
                    log_file.write(f"Query: {response.query}\n")
                    log_file.write(f"Context: {response.context}\n")
                    log_file.write(f"Tokens utilizados: {cb.total_tokens}\n")
                    log_file.write(f"Custo estimado: ${cb.total_cost:.6f}\n")
                    log_file.write(f"{'='*50}\n")
                    log_file.flush()  # Forçar gravação
            except Exception as e:
                logger.error(f"Erro ao escrever log da resposta: {e}")

        logger.info(f"🎯 === RESPOSTA DO MODELO ===")
        logger.info(f"Resposta: {response.answer}")
        logger.info(f"Query gerada: {response.query}")
        logger.info(f"Contexto: {response.context}")

        # Executar a query se fornecida
        if response.query and response.query.strip():
            logger.info(
                f"⚙️ Executando query: {response.query[:100]}{'...' if len(response.query) > 100 else ''}")
            query_executed_successfully = False
            try:
                # Execução mais segura da query
                result = execute_pandas_query(response.query, dataframes)

                if result is not None:
                    logger.info(
                        f"✅ Query executada com sucesso! Tipo: {type(result).__name__}")
                    query_executed_successfully = True

                    # Log do resultado da query executada
                    try:
                        log_file_path = logs_dir / 'ai_interactions.log'
                        with open(log_file_path, 'a', encoding='utf-8') as log_file:
                            log_file.write(
                                f"RESULTADO DA EXECUÇÃO DA QUERY:\n")
                            log_file.write(f"{'='*50}\n")
                            log_file.write(
                                f"Query executada: {response.query}\n")
                            log_file.write(
                                f"Tipo do resultado: {type(result)}\n")

                            if isinstance(result, (int, float)):
                                log_file.write(f"Valor numérico: {result}\n")
                            elif isinstance(result, pd.DataFrame):
                                log_file.write(
                                    f"DataFrame: {len(result)} linhas, {len(result.columns)} colunas\n")
                                if len(result) <= 10:
                                    log_file.write(
                                        f"Resultado completo:\n{result.to_string()}\n")
                                else:
                                    log_file.write(
                                        f"Primeiras 5 linhas:\n{result.head(5).to_string()}\n")
                            elif isinstance(result, pd.Series):
                                log_file.write(
                                    f"Series: {len(result)} valores\n")
                                if len(result) <= 20:
                                    log_file.write(
                                        f"Resultado:\n{result.to_string()}\n")
                                else:
                                    log_file.write(
                                        f"Primeiros 10 valores:\n{result.head(10).to_string()}\n")
                            else:
                                log_file.write(
                                    f"Resultado: {str(result)[:500]}\n")

                            log_file.write(f"Status: Execução bem-sucedida\n")
                            log_file.write(f"{'='*50}\n\n")
                            log_file.flush()
                    except Exception as e:
                        logger.error(f"Erro ao escrever log do resultado: {e}")

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
                        logger.info(f"📈 Resultado: {result}")
                    elif isinstance(result, pd.DataFrame):
                        if len(result) <= 20:  # Se for pequeno, mostrar tudo
                            response.answer = f"Resultado:\n{result.to_string()}"
                        else:
                            response.answer = f"Resultado (primeiras 10 linhas):\n{result.head(10).to_string()}\n\nTotal de {len(result)} registros encontrados."
                        logger.info(
                            f"📊 DataFrame: {len(result)} linhas")
                    elif isinstance(result, pd.Series):
                        response.answer = f"Resultado:\n{result.to_string()}"
                        logger.info(
                            f"📋 Series: {len(result)} valores")
                    elif isinstance(result, tuple):
                        # Formatação especial para tuplas (como nome do médico + quantidade)
                        if len(result) == 2:
                            response.answer = f"Resultado: {result[0]} com {result[1]} ocorrências"
                        else:
                            response.answer = f"Resultado: {result}"
                        logger.info(f"📄 Tupla: {result}")
                    else:
                        response.answer = f"Resultado: {result}"
                        logger.info(f"📄 Resultado: {type(result).__name__}")

                    response.context += f"\n\nQuery executada com sucesso: {response.query}"

            except Exception as e:
                logger.error(
                    f"❌ Erro na execução: {str(e)[:100]}{'...' if len(str(e)) > 100 else ''}")
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
            logger.info(f"ℹ️ Nenhuma query gerada")

        logger.info(f"🏁 Consulta finalizada - resposta gerada com sucesso")
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

        # Log simplificado para console - sem poluir com detalhes
        logger.info(f"⚙️ Executando query pandas...")

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

        # SEMPRE disponibilizar 'df' como o dataframe principal
        # Se há apenas um dataframe, usar esse
        # Se há múltiplos, usar o primeiro como padrão
        main_df = list(dataframes.values())[0].copy()
        local_vars['df'] = main_df

        # Log simplificado dos dataframes disponíveis
        if len(dataframes) == 1:
            logger.info(
                f"📊 Dataframe único: {len(main_df)} linhas, {len(main_df.columns)} colunas")
        else:
            logger.info(
                f"📊 Múltiplos dataframes: {len(dataframes)} arquivos carregados")

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

        else:
            # Para queries simples, usar eval
            result = eval(code, exec_globals)

        # Log simplificado do resultado - apenas tipo e resumo
        logger.info(f"✅ Query executada: {type(result).__name__}")

        return result

    except Exception as e:
        logger.error(
            f"❌ Erro na execução da query: {str(e)[:100]}{'...' if len(str(e)) > 100 else ''}")
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
