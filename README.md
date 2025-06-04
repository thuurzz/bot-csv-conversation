# Bot de Conversação CSV

Um assistente de IA para analisar e consultar dados CSV via interface de chat.

## Estrutura do Projeto

```
bot-csv-conversation/
├── frontend/             # Interface do usuário com Streamlit
│   ├── app.py            # Aplicação principal
│   └── utils/            # Módulos auxiliares
│       ├── chat.py       # Gerenciamento do chat
│       ├── file_manager.py # Gerenciamento de arquivos
│       └── session.py    # Gerenciamento de sessão
├── backend/              # Lógica de processamento (a ser implementado)
├── config/               # Configurações do projeto
│   └── .env              # Variáveis de ambiente
├── data/                 # Armazenamento persistente
├── uploads/              # Arquivos CSV enviados pelos usuários
└── .venv/                # Ambiente virtual Python
```

## Requisitos

- Python 3.8+
- Streamlit
- Pandas
- python-dotenv

## Configuração

1. Clone o repositório
2. Ative o ambiente virtual:
   ```
   source .venv/bin/activate
   ```
3. Instale as dependências:
   ```
   pip install streamlit pandas python-dotenv
   ```

## Execução

Para iniciar a aplicação frontend:

```bash
cd frontend
streamlit run app.py
```

## Funcionalidades

- **Sessão de usuário**: Identificação de usuários e persistência de sessão
- **Chat**: Interface para conversar com modelos de IA
- **Upload de arquivos CSV**: Envio e gerenciamento de arquivos para análise
- **Consulta de dados**: Interrogação de dados via linguagem natural (a ser implementado)

## Variáveis de Ambiente

Edite o arquivo `config/.env` para configurar:

- `UPLOAD_FOLDER`: Diretório para armazenar os arquivos CSV
- `MODEL_NAME`: Nome do modelo de IA a ser utilizado
- `DEBUG`: Modo de depuração (True/False)
