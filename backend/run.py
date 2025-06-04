import uvicorn
import os
from dotenv import load_dotenv
import logging
import sys

# Adicionar o diretório raiz ao sys.path para permitir importações absolutas
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Carregar variáveis de ambiente
dotenv_path = os.path.join(os.path.dirname(
    os.path.dirname(__file__)), 'config', '.env')
load_dotenv(dotenv_path)

if __name__ == '__main__':
    # Verificar se a API key do OpenAI está configurada
    if not os.getenv("OPENAI_API_KEY"):
        logging.warning(
            "OPENAI_API_KEY não está configurada! O backend funcionará com respostas simuladas.")

    # Iniciar o servidor FastAPI usando o caminho de módulo absoluto
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
