# Bot de Conversação CSV

Sistema full stack para análise de dados CSV através de perguntas em linguagem natural, utilizando uma interface de chat inteligente com IA.

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
- Chave de API OpenAI (para funcionalidades completas de IA)

## Configuração

1. Clone o repositório
2. Ative o ambiente virtual:
   ```
   python -m venv .venv
   source .venv/bin/activate  # No Linux/MacOS
   .venv\Scripts\activate     # No Windows
   ```
3. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
4. Configure as variáveis de ambiente no arquivo `config/.env`:
   ```
   OPENAI_API_KEY=sua_api_key_aqui
   UPLOAD_FOLDER=./../uploads
   MODEL_NAME=gpt-4o
   DEBUG=True
   BACKEND_HOST=0.0.0.0
   BACKEND_PORT=8000
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

Se estive em ambiente linux, você pode usar o comando:

```bash
cd backend
python3 run.py
```

A API estará disponível em: http://localhost:8000
Documentação interativa da API: http://localhost:8000/docs

## Funcionalidades

### Frontend (Streamlit)

- **Sessão de usuário**: Identificação e persistência de sessão entre reinicializações
- **Upload inteligente**: Suporte para arquivos CSV individuais e arquivos ZIP com múltiplos CSVs
- **Chat interativo**: Interface de conversação natural com histórico persistente
- **Seleção de arquivos**: Escolha dinâmica de quais arquivos usar nas consultas
- **Visualização de dados**: Preview dos dados com informações sobre estrutura e conteúdo
- **Status do sistema**: Monitoramento em tempo real do backend e conectividade
- **Sugestões de perguntas**: Botões com exemplos de consultas comuns
- **Fallback inteligente**: Respostas básicas quando o backend não está disponível

### Backend (FastAPI)

- **API RESTful**: Endpoints documentados com Swagger/OpenAPI
- **Processamento de IA**: Integração completa com LangChain e OpenAI GPT-4o
- **Execução segura**: Ambiente controlado para execução de código pandas
- **Gerenciamento de arquivos**: Upload, validação, listagem e remoção de CSVs
- **Suporte a ZIP**: Extração automática e processamento de arquivos compactados
- **Logging detalhado**: Rastreamento completo de todas as operações
- **Tratamento de erros**: Respostas informativas com sugestões de correção
- **Análise de múltiplos arquivos**: Processamento simultâneo de vários CSVs

## Fluxo Detalhado: Da Pergunta à Resposta

### Visão Geral

O sistema converte perguntas em linguagem natural em código pandas executável, proporcionando análises precisas dos dados CSV. Aqui está como funciona cada etapa:

### 1. Interface do Usuário (Frontend)

**Local:** `frontend/app.py` e `frontend/utils/chat.py`

- Usuário digita pergunta no campo de texto
- Sistema valida entrada e adiciona ao histórico da conversa
- Preparação da requisição com arquivos selecionados e contexto

### 2. Chamada para o Backend

**Endpoint:** `POST /api/chat`

A requisição inclui:

```json
{
  "message": "Quantas linhas tem o arquivo?",
  "files": ["arquivo1.csv", "arquivo2.csv"],
  "history": [{"role": "user", "content": "..."}, ...]
}
```

### 3. Processamento com IA (Coração do Sistema)

**Local:** `backend/services/ai_service.py`

#### 3.1 Carregamento e Análise dos Dados

- **Leitura dos CSVs**: Cada arquivo é carregado com `pandas.read_csv()`
- **Extração de metadados**:
  - Número de linhas e colunas
  - Tipos de dados de cada coluna
  - Amostras dos dados (primeiras 10 linhas)
  - Valores únicos para colunas categóricas
  - Estatísticas descritivas
- **Preparação do contexto**: Estruturação das informações para o modelo de IA

#### 3.2 Consulta ao Modelo LLM

**Modelo usado:** GPT-4o (OpenAI) com temperatura 0.0 (determinístico)

**Única chamada LLM por pergunta** - O sistema envia:

- Pergunta do usuário
- Histórico da conversa (últimas 10 mensagens)
- Metadados completos de todos os CSVs
- Instruções específicas sobre como gerar código pandas

**Resposta estruturada recebida:**

```python
{
  "answer": "Resposta em linguagem natural",
  "query": "código pandas para executar",
  "context": "informações contextuais"
}
```

#### 3.3 Execução Segura do Código

**Ambiente controlado:** O código pandas é executado em um ambiente seguro com:

- Funções built-in permitidas (`len`, `sum`, `max`, etc.)
- Bibliotecas pandas e numpy disponíveis
- Dataframes carregados como `df`, `df_1`, `df_2`, etc.
- Prevenção contra código malicioso

**Tipos de execução:**

- **Queries simples**: `eval()` para expressões diretas
- **Queries complexas**: `exec()` para código com assignments

### 4. Formatação dos Resultados

O sistema formata automaticamente baseado no tipo de resultado:

- **Números**: Formatação especial para cálculos de tempo/estatísticas
- **DataFrames**: Exibição de até 20 linhas ou resumo para datasets grandes
- **Series**: Conversão para formato legível
- **Tuplas**: Formatação para pares nome/valor
- **Erros**: Mensagens claras com sugestões de correção

### 5. Retorno e Exibição

- Backend retorna resposta JSON formatada
- Frontend exibe resultado no chat com formatação adequada
- Histórico é atualizado para contexto futuro

### Exemplo Prático Completo

**Pergunta:** "Qual é a média de idade dos pacientes?"

1. **Frontend** → Envia para `/api/chat` com arquivo selecionado
2. **Backend** → Carrega CSV, extrai que existe coluna "idade"
3. **IA** → Interpreta pergunta → gera `df['idade'].mean()`
4. **Execução** → Executa código → retorna 45.2
5. **Formatação** → "A média de idade dos pacientes é 45.2 anos"
6. **Interface** → Exibe resposta formatada no chat

### Tratamento de Cenários Especiais

**Sem API OpenAI configurada:**

- Sistema usa `simulate_response()` com lógica baseada em palavras-chave
- Fornece respostas básicas mas funcionais

**Erro na execução:**

- Mensagem de erro clara com sugestões específicas
- Exemplos de perguntas que funcionam bem
- Contexto sobre o que pode ter dado errado

**Backend indisponível:**

- Frontend detecta automaticamente
- Ativa modo fallback com respostas locais básicas
- Mantém funcionalidades essenciais ativas

### Monitoramento e Logs

O sistema registra detalhadamente:

- Todas as consultas recebidas
- Tokens utilizados e custos estimados
- Tempo de execução de cada etapa
- Erros e suas causas
- Resultados gerados

## Suporte a Arquivos ZIP

Funcionalidade avançada para processamento em lote:

- **Extração automática**: Descompactação e validação de todos os CSVs
- **Validação de conteúdo**: Verificação de integridade de cada arquivo
- **Prevenção de conflitos**: Renomeação automática de arquivos duplicados
- **Suporte a estruturas**: Funciona com CSVs em subdiretórios
- **Feedback detalhado**: Relatório completo do processo de extração

## Integração com LangChain

Arquitetura moderna de IA:

1. **Prompt Engineering**: Templates otimizados para análise de dados
2. **Output Parsing**: Respostas estruturadas com validação Pydantic
3. **Chain Composition**: Pipeline eficiente de processamento
4. **Callback Tracking**: Monitoramento de uso e custos
5. **Error Handling**: Recuperação inteligente de falhas

## Variáveis de Ambiente

Configure no arquivo `config/.env`:

```bash
# IA e Processamento
OPENAI_API_KEY=sua_chave_openai_aqui
MODEL_NAME=gpt-4o

# Configurações do Sistema
UPLOAD_FOLDER=./../uploads
DEBUG=True

# Configurações de Rede
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
```

## Exemplos de Perguntas Suportadas

**Análise básica:**

- "Quantas linhas tem o arquivo?"
- "Quais são as colunas disponíveis?"
- "Mostre as primeiras 10 linhas"

**Estatísticas:**

- "Qual é a média da coluna idade?"
- "Qual o valor máximo de vendas?"
- "Mostre estatísticas descritivas"

**Filtragem e agrupamento:**

- "Quantos registros têm status 'ativo'?"
- "Agrupe por categoria e some as vendas"
- "Filtre dados do último mês"

**Análise avançada:**

- "Qual categoria teve mais vendas?"
- "Calcule a correlação entre preço e quantidade"
- "Encontre valores duplicados"

## Limitações e Considerações

- **Segurança**: Execução em ambiente controlado previne código malicioso
- **Performance**: Otimizado para arquivos de até 100MB
- **Custos**: Uma chamada LLM por pergunta mantém custos controlados
- **Privacidade**: Dados são processados localmente, apenas metadados são enviados para IA

## Próximos Passos

- [ ] Implementar autenticação de usuários
- [ ] Adicionar visualizações gráficas dos dados
- [ ] Suporte para mais formatos (Excel, JSON, Parquet)
- [ ] Interface para ajuste fino dos prompts
- [ ] Cache inteligente de consultas frequentes
- [ ] Exportação de relatórios em PDF
- [ ] Integração com bancos de dados
