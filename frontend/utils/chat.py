import streamlit as st
import os
import pandas as pd
from dotenv import load_dotenv
from .file_manager import list_available_files

# Carregar variáveis de ambiente com caminho correto
dotenv_path = os.path.join(os.path.dirname(
    os.path.dirname(os.path.dirname(__file__))), 'config', '.env')
load_dotenv(dotenv_path)
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads"))
MODEL_NAME = os.getenv("MODEL_NAME", "default-model")


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
    Gera uma resposta com base na pergunta do usuário.
    Este é um placeholder simples - será substituído por chamadas ao backend.

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

    # Resposta simples com base em palavras-chave (será substituída por um modelo real)
    user_input_lower = user_input.lower()

    if "listar" in user_input_lower and ("arquivo" in user_input_lower or "csv" in user_input_lower):
        files_list = ", ".join(available_files)
        return f"Os arquivos CSV disponíveis são: {files_list}"

    elif "coluna" in user_input_lower or "dados" in user_input_lower:
        # Exemplo simples - mostrar colunas do primeiro arquivo
        try:
            sample_file = os.path.join(UPLOAD_FOLDER, available_files[0])
            df = pd.read_csv(sample_file)
            columns = ", ".join(df.columns)
            return f"O arquivo '{available_files[0]}' contém as seguintes colunas: {columns}"
        except Exception as e:
            return f"Ocorreu um erro ao ler o arquivo: {str(e)}"

    # Resposta padrão
    return ("Estou aqui para ajudar com a análise dos seus dados CSV. "
            "No momento, sou apenas uma simulação para a interface front-end. "
            "Em breve, estarei conectado a um modelo de IA no backend para "
            "responder perguntas sobre seus dados de forma mais avançada.")


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
