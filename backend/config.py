import os
from pathlib import Path
from dotenv import load_dotenv

# Diretório raiz do projeto
BASE_DIR = Path(__file__).parent.parent

# Carregar variáveis de ambiente
dotenv_path = os.path.join(BASE_DIR, 'config', '.env')
load_dotenv(dotenv_path)

# Configurações


class Config:
    # Diretório para uploads de arquivos
    UPLOAD_FOLDER = os.getenv(
        "UPLOAD_FOLDER", os.path.join(BASE_DIR, "uploads"))

    # Nome/modelo da IA para processamento
    MODEL_NAME = os.getenv("MODEL_NAME", "default-model")

    # Modo debug
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

    # Tamanho máximo de arquivo para upload (10MB por padrão)
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

    # Tipos de arquivo permitidos
    ALLOWED_EXTENSIONS = {'csv'}

# Configurações de desenvolvimento


class DevelopmentConfig(Config):
    DEBUG = True

# Configurações de produção


class ProductionConfig(Config):
    DEBUG = False


# Dicionário de configurações
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}


def get_config():
    """Retorna a configuração apropriada com base no ambiente"""
    env = os.getenv("ENV", "development")
    return config.get(env, config["default"])
