import streamlit as st
import os
import pandas as pd
from dotenv import load_dotenv
from .file_manager import list_available_files
import requests
import json
import uuid

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


def format_response_for_display(response_text):
    """
    Formata a resposta do backend para melhor visualização no Streamlit

    Args:
        response_text: Resposta bruta do backend

    Returns:
        None (renderiza diretamente no Streamlit)
    """
    # Detectar se é uma resposta com dados tabulares
    if response_text.startswith("TABLE_RESPONSE:"):
        try:
            # Extrair resposta e dados da tabela
            content = response_text[len("TABLE_RESPONSE:"):]
            parts = content.split("|", 1)
            if len(parts) == 2:
                answer, json_data = parts

                # Converter JSON para DataFrame
                data = json.loads(json_data)
                df = pd.DataFrame(data)

                # Exibir apenas a resposta textual limpa (sem os dados JSON)
                st.write(answer)

                # Exibir tabela interativa sem título chamativo
                st.write("### 📊 Resultados:")

                # Métricas resumo simplificadas
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Registros", len(df))
                with col2:
                    st.metric("Colunas", len(df.columns))

                # Tabela principal
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True
                )

                # Botão de download simples com chave única
                csv = df.to_csv(index=False)
                download_key = f"download_format_{uuid.uuid4().hex[:8]}"
                st.download_button(
                    label="💾 Baixar CSV",
                    data=csv,
                    file_name="resultado.csv",
                    mime="text/csv",
                    key=download_key
                )
                return

        except Exception as e:
            st.error(f"Erro ao exibir dados tabulares: {str(e)}")
            # Fallback para texto simples
            st.write(response_text.replace("TABLE_RESPONSE:", ""))
            return

    # Detectar se é uma resposta com dados de texto formatados
    if response_text.startswith("TEXT_RESPONSE:"):
        try:
            # Extrair resposta e dados de texto
            content = response_text[len("TEXT_RESPONSE:"):]
            parts = content.split("|", 1)
            if len(parts) == 2:
                answer, text_data = parts

                # Exibir resposta textual
                st.write(answer)

                # Exibir dados em container com scroll
                st.write("### 📋 Resultado detalhado:")
                st.text(text_data)
                return

        except Exception as e:
            st.error(f"Erro ao exibir dados de texto: {str(e)}")
            # Fallback para texto simples
            st.write(response_text.replace("TEXT_RESPONSE:", ""))
            return

    # Detectar se é um resultado numérico simples
    if response_text.startswith("Resultado: ") and response_text.count("\n") == 0:
        # Extrair o número
        number = response_text.replace("Resultado: ", "")
        if number.replace(".", "").replace(",", "").replace("-", "").isdigit():
            st.metric(label="Resultado da Consulta", value=number)
            return

    # Formatação padrão para outros tipos de resposta
    lines = response_text.split('\n')

    # Se é uma resposta curta, mostrar como destaque
    if len(lines) == 1 and len(response_text) < 100:
        st.info(f"💬 {response_text}")
    else:
        # Para respostas longas, mostrar com formatação melhorada
        for line in lines:
            if line.strip():
                if line.startswith("- ") or line.startswith("• "):
                    st.write(f"• {line[2:]}")
                elif ":" in line and len(line.split(":")) == 2:
                    key, value = line.split(":", 1)
                    st.write(f"**{key.strip()}:** {value.strip()}")
                else:
                    st.write(line)


def display_chat_messages():
    """
    Exibe o histórico de mensagens do chat na interface com formatação melhorada
    """
    # Adicionar botão para limpar o histórico
    if st.button("🗑️ Limpar histórico", key="clear_chat"):
        st.session_state.messages = [
            {"role": "assistant", "content": "Histórico de chat limpo. Como posso ajudar?"}
        ]
        st.rerun()

    # Mostrar todas as mensagens do histórico
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                # Usar formatação melhorada para respostas do assistente
                format_response_for_display(message["content"])
            else:
                # Mensagens do usuário ficam simples
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

    # Gerar resposta do backend
    response_data = generate_response(user_input)

    # Verificar se a resposta contém dados estruturados
    if isinstance(response_data, dict):
        # Se tem dados tabulares, armazenar de forma especial
        if "table_data" in response_data:
            # Criar uma mensagem especial que será detectada na exibição
            message_content = f"TABLE_RESPONSE:{response_data['answer']}|{response_data['table_data']}"
            st.session_state.messages.append(
                {"role": "assistant", "content": message_content})
        elif "text_data" in response_data:
            # Para dados de texto formatados
            message_content = f"TEXT_RESPONSE:{response_data['answer']}|{response_data['text_data']}"
            st.session_state.messages.append(
                {"role": "assistant", "content": message_content})
        else:
            # Resposta normal
            st.session_state.messages.append(
                {"role": "assistant", "content": response_data.get('answer', str(response_data))})
    else:
        # Resposta simples (string)
        st.session_state.messages.append(
            {"role": "assistant", "content": response_data})


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

            # Dados para a requisição - incluindo histórico de conversas
            # Filtrar apenas mensagens de usuário e assistente, excluindo a mensagem de boas-vindas
            history_to_send = []
            if "messages" in st.session_state and len(st.session_state.messages) > 1:
                # Pular a primeira mensagem (boas-vindas) e incluir as anteriores
                # Começar do índice 1
                for msg in st.session_state.messages[1:]:
                    history_to_send.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

            payload = {
                "message": user_input,
                "files": prioritized_files,  # Usando a lista com arquivo selecionado priorizado
                "history": history_to_send  # Incluindo histórico de conversas
            }

            # Fazer a chamada para o backend
            print(f"Enviando consulta para o backend: {url}")
            response = requests.post(url, json=payload, timeout=30)

            if response.status_code == 200:
                # Processar a resposta do backend
                data = response.json()
                answer = data.get("answer", "")
                context = data.get("context", "")

                # Verificar se há dados tabulares estruturados no contexto
                if "TABLE_DATA:" in context:
                    # Retornar dados estruturados em vez de exibir diretamente
                    table_data_start = context.find(
                        "TABLE_DATA:") + len("TABLE_DATA:")
                    json_data = context[table_data_start:].split("\n")[
                        0].strip()
                    return {
                        "answer": answer,
                        "table_data": json_data
                    }
                elif "TEXT_DATA:" in context:
                    # Retornar dados de texto estruturados
                    text_data_start = context.find(
                        "TEXT_DATA:") + len("TEXT_DATA:")
                    text_data = context[text_data_start:].split("\n\n")[
                        0].strip()
                    return {
                        "answer": answer,
                        "text_data": text_data
                    }

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


def display_table_data(context, answer):
    """
    Exibe dados tabulares estruturados usando componentes Streamlit nativos
    """
    try:
        # Extrair JSON dos dados da tabela
        table_data_start = context.find("TABLE_DATA:") + len("TABLE_DATA:")
        json_data = context[table_data_start:].split("\n")[0].strip()

        # Converter JSON para DataFrame
        data = json.loads(json_data)
        df = pd.DataFrame(data)

        # Exibir resposta textual
        st.write(answer)

        # Exibir tabela interativa
        st.write("### 📊 Resultados:")

        # Métricas resumo simplificadas
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Registros", len(df))
        with col2:
            st.metric("Colunas", len(df.columns))

        # Tabela principal
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        # Botão de download simples com chave única
        csv = df.to_csv(index=False)
        download_key = f"download_display_{uuid.uuid4().hex[:8]}"
        st.download_button(
            label="💾 Baixar CSV",
            data=csv,
            file_name="resultado.csv",
            mime="text/csv",
            key=download_key
        )

    except Exception as e:
        st.error(f"Erro ao exibir dados tabulares: {str(e)}")
        st.write(answer)


def display_text_data(context, answer):
    """
    Exibe dados de texto formatados
    """
    try:
        # Extrair dados de texto
        text_data_start = context.find("TEXT_DATA:") + len("TEXT_DATA:")
        text_data = context[text_data_start:].split("\n\n")[0].strip()

        # Exibir resposta textual
        st.write(answer)

        # Exibir dados em container com scroll
        st.write("### 📋 Resultado detalhado:")
        st.text(text_data)

    except Exception as e:
        st.error(f"Erro ao exibir dados de texto: {str(e)}")
        st.write(answer)
