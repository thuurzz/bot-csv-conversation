# Bot de Conversação CSV

Sistema full stack para análise de dados CSV através de perguntas em linguagem natural, utilizando uma interface de chat.

## Estrutura do Projeto

```
bot-csv-conversation/
├── frontend/             # Interface do usuário com Streamlit
│   ├── app.py            # Aplicação principal
│   └── utils/            # Módulos auxiliares
│       ├── chat.py       # Gerenciamento do chat
│       ├── file_manager.py # Gerenciamento de arquivos
│       └── session.py    # Gerenciamento de sessão
├── backend/              # API com FastAPI
│   ├── app.py            # Endpoints da API
│   ├── models.py         # Modelos Pydantic
│   ├── config.py         # Configurações
│   ├── run.py            # Script para iniciar o servidor
│   └── services/         # Serviços
│       ├── ai_service.py    # Integração com LangChain/IA
│       ├── data_service.py  # Análise de dados
│       └── file_service.py  # Gerenciamento de arquivos
├── config/               # Configurações do projeto
│   └── .env              # Variáveis de ambiente
├── data/                 # Armazenamento persistente
├── uploads/              # Arquivos CSV enviados pelos usuários
└── requirements.txt      # Dependências do projeto
```

## Requisitos

- Python 3.8+
- Dependências listadas em `requirements.txt`

## Configuração

1. Clone o repositório
2. Ative o ambiente virtual:
   ```
   python -m venv .venv
   source .venv/bin/activate  # No Linux/MacOS
   ```
3. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
4. Configure as variáveis de ambiente no arquivo `config/.env`, incluindo a API key do OpenAI para utilizar os modelos de IA:
   ```
   OPENAI_API_KEY=sua_api_key_aqui
   ```

## Execução

### Frontend (Streamlit)

Para iniciar a aplicação frontend:

```bash
cd frontend
streamlit run app.py
```

A interface do Streamlit ficará disponível em: http://localhost:8501

### Backend (FastAPI)

Para iniciar o servidor backend:

```bash
cd backend
python run.py
```

A API estará disponível em: http://localhost:8000

Documentação interativa da API: http://localhost:8000/docs

## Funcionalidades

### Frontend (Streamlit)

- **Sessão de usuário**: Identificação e persistência de sessão
- **Upload de arquivos CSV**: Interface para envio e visualização de arquivos
- **Chat interativo**: Interface para conversar com o assistente de IA
- **Visualização de dados**: Exibição de informações sobre os arquivos

### Backend (FastAPI)

- **Gerenciamento de arquivos**: Upload, listagem e download de CSVs
- **Análise de dados**: Processamento de dados usando pandas
- **Integração com LangChain**: Processamento de perguntas em linguagem natural
- **API RESTful**: Endpoints documentados para integração

## Fluxo de Funcionamento

1. **Upload de arquivos**:

   - O usuário faz upload de arquivos CSV através da interface frontend
   - Os arquivos são salvos no servidor e os metadados são extraídos

2. **Seleção de arquivos**:

   - O usuário seleciona quais arquivos deseja usar nas consultas
   - A lista de arquivos selecionados é enviada junto com a consulta

3. **Processamento de consultas**:

   - O usuário envia uma pergunta em linguagem natural
   - O backend usa LangChain com um modelo de IA para:
     - Interpretar a pergunta
     - Gerar código pandas para responder à consulta
     - Executar o código
     - Formatar o resultado

4. **Exibição de resultados**:
   - O frontend recebe a resposta formatada
   - Exibe o resultado para o usuário, junto com contexto adicional

## Integração com LangChain

O sistema utiliza o LangChain para:

1. Gerar código pandas dinamicamente a partir de consultas em linguagem natural
2. Executar o código de forma segura
3. Formatar os resultados para apresentação ao usuário

Quando a variável de ambiente `OPENAI_API_KEY` está configurada, o sistema usa o modelo especificado para análise avançada. Caso contrário, fornece respostas simuladas.

## Variáveis de Ambiente

Edite o arquivo `config/.env` para configurar:

- `UPLOAD_FOLDER`: Diretório para armazenar os arquivos CSV
- `MODEL_NAME`: Nome do modelo de IA a ser utilizado
- `DEBUG`: Modo de depuração (True/False)
- `OPENAI_API_KEY`: Chave da API OpenAI para os modelos de IA
- `BACKEND_HOST`: Host para o servidor backend
- `BACKEND_PORT`: Porta para o servidor backend

## Próximos passos

- Implementar autenticação de usuários
- Adicionar visualizações gráficas dos dados
- Suporte para mais formatos de arquivos além de CSV
- Interface para ajuste fino dos prompts de IA
