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


def format_response_for_display(response_text):
    """
    Formata a resposta do backend para melhor visualização no Streamlit

    Args:
        response_text: Resposta bruta do backend

    Returns:
        None (renderiza diretamente no Streamlit)
    """
    # Detectar se é um resultado numérico simples
    if response_text.startswith("Resultado: ") and response_text.count("\n") == 0:
        # Extrair o número
        number = response_text.replace("Resultado: ", "")
        if number.replace(".", "").replace(",", "").replace("-", "").isdigit():
            st.metric(label="Resultado da Consulta", value=number)
            return

    # Detectar se contém uma tabela/DataFrame genérica
    if "|" in response_text and "\n" in response_text:
        try:
            # Tentar extrair e renderizar como DataFrame
            lines = response_text.split('\n')

            # Encontrar onde começa a tabela (procurar por linhas com separadores)
            table_start = -1
            for i, line in enumerate(lines):
                if "|" in line and len(line.split("|")) > 2:
                    table_start = i
                    break

            if table_start >= 0:
                # Mostrar texto antes da tabela (se houver)
                if table_start > 0:
                    intro_text = '\n'.join(lines[:table_start]).strip()
                    if intro_text and intro_text != "Resultado:":
                        st.write(intro_text)

                st.write("### 📊 Resultados encontrados:")

                # Processar as linhas da tabela de forma genérica
                table_lines = []
                headers = []
                data_started = False

                for line in lines[table_start:]:
                    line = line.strip()
                    if not line or line.startswith("+"):
                        continue

                    if "|" in line:
                        parts = [part.strip()
                                 for part in line.split("|") if part.strip()]

                        if parts and not data_started:
                            # Primeira linha com dados é o cabeçalho
                            headers = parts
                            data_started = True
                        elif parts and data_started and len(parts) == len(headers):
                            table_lines.append(parts)

                if table_lines and headers:
                    # Criar DataFrame genérico
                    df_display = pd.DataFrame(table_lines, columns=headers)

                    # Mostrar métricas resumo genéricas
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total de Registros", len(df_display))
                    with col2:
                        st.metric("Colunas", len(df_display.columns))
                    with col3:
                        # Tentar encontrar coluna numérica para estatística
                        numeric_cols = df_display.select_dtypes(
                            include=['number']).columns
                        if len(numeric_cols) > 0:
                            first_numeric = numeric_cols[0]
                            try:
                                mean_val = pd.to_numeric(
                                    df_display[first_numeric], errors='coerce').mean()
                                st.metric(
                                    f"Média ({first_numeric})", f"{mean_val:.2f}")
                            except:
                                st.metric("Dados", "Carregados")
                        else:
                            st.metric("Dados", "Carregados")

                    # Mostrar tabela interativa
                    st.dataframe(
                        df_display,
                        use_container_width=True,
                        hide_index=True
                    )

                    # Gráfico de distribuição genérico (primeira coluna categórica)
                    if len(df_display) > 1:
                        categorical_cols = df_display.select_dtypes(
                            include=['object']).columns
                        if len(categorical_cols) > 0:
                            first_cat_col = categorical_cols[0]
                            st.write(f"### 📈 Distribuição por {first_cat_col}")
                            col_counts = df_display[first_cat_col].value_counts(
                            )
                            st.bar_chart(col_counts)

                    return

        except Exception as e:
            print(f"Erro ao processar tabela: {e}")
            # Fallback para texto simples
            pass

    # Detectar listas ou contagens
    if response_text.startswith("Resultado: ") and "\n" in response_text:
        lines = response_text.split('\n')
        if len(lines) > 1:
            result_line = lines[0]
            rest_content = '\n'.join(lines[1:])

            # Mostrar resultado principal destacado
            if ":" in result_line:
                value = result_line.split(": ", 1)[1]
                st.success(f"✅ {value}")
            else:
                st.info(result_line)

            # Mostrar conteúdo adicional
            if rest_content.strip():
                with st.expander("📋 Detalhes adicionais"):
                    st.text(rest_content)
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
