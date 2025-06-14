import streamlit as st
import os
import pandas as pd
from dotenv import load_dotenv
from .file_manager import list_available_files
import requests
import json

# Carregar variáveis de ambiente com caminho correto
dotenv_path = os.path.join(os.path.dirname(
    os.path.dirname(os.path.dirname(__file__))), 'config', '.env')
load_dotenv(dotenv_path)
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads"))
MODEL_NAME = os.getenv("MODEL_NAME", "default-model")

# Obter configuração do backend
_BACKEND_HOST = os.getenv("BACKEND_HOST", "localhost")
BACKEND_PORT = os.getenv("BACKEND_PORT", "8000")

# Se o BACKEND_HOST for 0.0.0.0 (endereço de escuta), usar localhost para conexão
BACKEND_HOST = "localhost" if _BACKEND_HOST == "0.0.0.0" else _BACKEND_HOST


def check_backend_status():
    """
    Verifica se o backend está conectado usando a rota de health check

    Returns:
        tuple: (status_conectado: bool, mensagem: str)
    """
    try:
        # Montar a URL com a garantia de que o protocolo está incluído
        if BACKEND_HOST.startswith(('http://', 'https://')):
            url = f"{BACKEND_HOST}:{BACKEND_PORT}/api/health"
        else:
            url = f"http://{BACKEND_HOST}:{BACKEND_PORT}/api/health"

        print(f"Tentando conectar ao backend: {url}")  # Log para debug
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            data = response.json()
            timestamp = data.get("timestamp", "")
            return True, f"Backend: Conectado (última verificação: {timestamp})"
        else:
            return False, f"Backend: Não conectado (erro de resposta: {response.status_code})"
    except requests.RequestException as e:
        return False, f"Backend: Não conectado (falha na conexão: {str(e)})"
    except Exception as e:
        return False, f"Backend: Erro de conexão ({str(e)})"


def display_chat_messages():
    """
    Exibe o histórico de mensagens do chat na interface
    """
    # Adicionar botão para limpar o histórico
    if st.button("Limpar histórico", key="clear_chat"):
        st.session_state.messages = [
            {"role": "assistant", "content": "Histórico de chat limpo. Como posso ajudar?"}
        ]
        st.rerun()

    # Mostrar todas as mensagens do histórico
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])


def process_message(user_input):
    """
    Processa uma mensagem do usuário e gera uma resposta

    Args:
        user_input: Texto da mensagem do usuário
    """
    if not user_input:
        return

    # Adiciona a mensagem do usuário ao histórico
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Simula o processamento pelo modelo (placeholder para integração futura com backend)
    response = generate_response(user_input)

    # Adiciona a resposta do modelo ao histórico
    st.session_state.messages.append(
        {"role": "assistant", "content": response})


def generate_response(user_input):
    """
    Gera uma resposta com base na pergunta do usuário usando o backend.
    Faz uma chamada ao backend para processamento da consulta.

    Args:
        user_input: Texto da pergunta do usuário

    Returns:
        str: Resposta gerada
    """
    # Lista de arquivos disponíveis
    available_files = list_available_files()

    # Verifica se há arquivos disponíveis
    if not available_files:
        return ("Parece que você ainda não enviou nenhum arquivo CSV. "
                "Por favor, faça upload de um arquivo na barra lateral para que "
                "eu possa ajudar a analisar seus dados.")

    # Verificar se há um arquivo selecionado para priorizar
    selected_file = st.session_state.get('selected_file')
    prioritized_files = available_files

    if selected_file and selected_file in available_files:
        # Movendo o arquivo selecionado para o início da lista para priorizar
        prioritized_files = [selected_file] + \
            [f for f in available_files if f != selected_file]
        print(f"Arquivo priorizado para consulta: {selected_file}")

    try:
        # Verifica se o backend está acessível
        backend_connected, _ = check_backend_status()

        if backend_connected:
            # Preparar a URL para a chamada da API
            if BACKEND_HOST.startswith(('http://', 'https://')):
                url = f"{BACKEND_HOST}:{BACKEND_PORT}/api/chat"
            else:
                url = f"http://{BACKEND_HOST}:{BACKEND_PORT}/api/chat"

            # Dados para a requisição
            payload = {
                "message": user_input,
                "files": prioritized_files  # Usando a lista com arquivo selecionado priorizado
            }

            # Fazer a chamada para o backend
            print(f"Enviando consulta para o backend: {url}")
            response = requests.post(url, json=payload, timeout=30)

            if response.status_code == 200:
                # Processar a resposta do backend
                data = response.json()
                answer = data.get("answer", "")

                # Registrar informações adicionais para debug
                query = data.get("query", "")
                if query:
                    print(f"Query gerada pelo backend: {query}")

                return answer
            else:
                return f"Erro ao processar a consulta (código {response.status_code}). Por favor, tente novamente mais tarde."

        # Se o backend não estiver disponível, usar a lógica local de fallback
        print("Backend não disponível. Usando respostas locais de fallback.")

        # Resposta simples com base em palavras-chave (fallback)
        user_input_lower = user_input.lower()

        if "listar" in user_input_lower and ("arquivo" in user_input_lower or "csv" in user_input_lower):
            files_list = ", ".join(prioritized_files)
            return f"Os arquivos CSV disponíveis são: {files_list}"

        elif "coluna" in user_input_lower or "dados" in user_input_lower:
            # Usar o arquivo selecionado se disponível, ou o primeiro da lista
            target_file = selected_file if selected_file else prioritized_files[0]
            try:
                sample_file = os.path.join(UPLOAD_FOLDER, target_file)
                df = pd.read_csv(sample_file)
                columns = ", ".join(df.columns)
                return f"O arquivo '{target_file}' contém as seguintes colunas: {columns}"
            except Exception as e:
                return f"Ocorreu um erro ao ler o arquivo: {str(e)}"

        # Resposta padrão de fallback
        target_file = selected_file if selected_file else "nenhum arquivo específico"
        return (f"Não consegui conectar ao backend para processamento avançado. "
                f"Você está consultando sobre {target_file}. "
                f"Você tem {len(available_files)} arquivo(s) disponível(is). "
                "Tente fazer perguntas mais específicas sobre os dados.")

    except Exception as e:
        print(f"Erro ao gerar resposta: {str(e)}")
        return f"Ocorreu um erro ao processar sua pergunta: {str(e)}"


def analyze_csv(filename, query):
    """
    Analisa um arquivo CSV com base em uma consulta
    Esta função será expandida quando o backend estiver implementado

    Args:
        filename: Nome do arquivo CSV a ser analisado
        query: Consulta do usuário

    Returns:
        str: Resultado da análise
    """
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(file_path):
            return f"Arquivo '{filename}' não encontrado."

        # Lê o CSV
        df = pd.read_csv(file_path)

        # Análise básica (placeholder)
        result = f"Análise do arquivo '{filename}':\n"
        result += f"- Total de linhas: {len(df)}\n"
        result += f"- Total de colunas: {len(df.columns)}\n"
        result += f"- Colunas: {', '.join(df.columns)}\n"

        # Estatísticas numéricas básicas
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            result += "\nEstatísticas numéricas básicas:\n"
            # Limitando a 3 colunas para não sobrecarregar
            for col in numeric_cols[:3]:
                result += f"- {col}: média={df[col].mean():.2f}, min={df[col].min():.2f}, max={df[col].max():.2f}\n"

        return result

    except Exception as e:
        return f"Erro ao analisar o arquivo: {str(e)}"
