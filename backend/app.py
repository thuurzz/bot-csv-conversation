import os
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import pandas as pd
from config import get_config
import logging
import json

# Configuração do logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backend.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Inicialização do app Flask
app = Flask(__name__)
config = get_config()

# Configurações do Flask
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

# Garantir que diretórios existam
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def allowed_file(filename):
    """Verifica se a extensão do arquivo é permitida"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint para verificar se a API está funcionando"""
    return jsonify({'status': 'ok', 'message': 'API está funcionando'})


@app.route('/api/files', methods=['GET'])
def list_files():
    """Lista todos os arquivos CSV disponíveis"""
    try:
        files = []
        for file in os.listdir(app.config['UPLOAD_FOLDER']):
            if file.lower().endswith('.csv'):
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file)
                file_stat = os.stat(file_path)
                files.append({
                    'name': file,
                    'size': file_stat.st_size,
                    'created': file_stat.st_ctime
                })
        return jsonify({'files': files})
    except Exception as e:
        logger.error(f"Erro ao listar arquivos: {str(e)}")
        return jsonify({'error': 'Erro ao listar arquivos'}), 500


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload de um arquivo CSV"""
    # Verificar se a requisição tem o arquivo
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400

    file = request.files['file']

    # Se o usuário não selecionou um arquivo
    if file.filename == '':
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400

    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # Salvar o arquivo
            file.save(file_path)

            # Verificar se é um CSV válido
            df = pd.read_csv(file_path)

            # Salvar preview
            preview_path = os.path.join(
                app.config['UPLOAD_FOLDER'], f"preview_{filename}.info")
            with open(preview_path, "w") as f:
                f.write(f"Arquivo: {filename}\n")
                f.write(f"Linhas: {len(df)}\n")
                f.write(f"Colunas: {', '.join(df.columns)}\n")
                f.write(
                    f"Tamanho: {df.memory_usage(deep=True).sum() / (1024*1024):.2f} MB\n")

            return jsonify({'success': True, 'filename': filename, 'rows': len(df), 'columns': len(df.columns)})

        except Exception as e:
            logger.error(f"Erro ao processar upload: {str(e)}")
            return jsonify({'error': f'Erro ao processar arquivo: {str(e)}'}), 500

    return jsonify({'error': 'Tipo de arquivo não permitido'}), 400


@app.route('/api/file/<filename>', methods=['GET'])
def get_file_info(filename):
    """Retorna informações sobre um arquivo específico"""
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'Arquivo não encontrado'}), 404

        df = pd.read_csv(file_path)
        info = {
            'filename': filename,
            'rows': len(df),
            'columns': list(df.columns),
            'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
            'preview': df.head(5).to_dict(orient='records')
        }

        # Adicionar estatísticas básicas para colunas numéricas
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            info['stats'] = {}
            for col in numeric_cols:
                info['stats'][col] = {
                    'mean': float(df[col].mean()),
                    'min': float(df[col].min()),
                    'max': float(df[col].max()),
                    'median': float(df[col].median())
                }

        return jsonify(info)

    except Exception as e:
        logger.error(f"Erro ao obter informações do arquivo: {str(e)}")
        return jsonify({'error': f'Erro ao processar arquivo: {str(e)}'}), 500


@app.route('/api/chat', methods=['POST'])
def chat_with_data():
    """Endpoint para processar perguntas sobre os dados"""
    try:
        data = request.json
        if not data or 'message' not in data:
            return jsonify({'error': 'Nenhuma mensagem fornecida'}), 400

        message = data['message']

        # Placeholder para integração com modelo de IA
        # Aqui será implementada a lógica para processar perguntas usando um modelo

        # Resposta simulada
        response = {
            'answer': f'Você perguntou: "{message}". Esta é uma resposta simulada do backend.'
        }

        # Adicionar mais informações dependendo do conteúdo da mensagem
        if 'lista' in message.lower() or 'arquivo' in message.lower():
            files = [f for f in os.listdir(
                app.config['UPLOAD_FOLDER']) if f.endswith('.csv')]
            response['files'] = files
            response['answer'] = f"Encontrei {len(files)} arquivos: {', '.join(files)}"

        return jsonify(response)

    except Exception as e:
        logger.error(f"Erro no processamento do chat: {str(e)}")
        return jsonify({'error': f'Erro no processamento: {str(e)}'}), 500


@app.route('/api/analyze', methods=['POST'])
def analyze_data():
    """Endpoint para análise mais detalhada de dados"""
    try:
        data = request.json
        if not data or 'filename' not in data or 'query' not in data:
            return jsonify({'error': 'Parâmetros incompletos'}), 400

        filename = data['filename']
        query = data['query']

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'Arquivo não encontrado'}), 404

        # Processamento básico (placeholder)
        df = pd.read_csv(file_path)

        # Simulação de análise básica
        result = {
            'filename': filename,
            'analysis': f"Análise para a consulta: {query}",
            'rows': len(df),
            'columns': len(df.columns),
            'column_names': list(df.columns)
        }

        # Aqui será expandido com análise real baseada na consulta

        return jsonify(result)

    except Exception as e:
        logger.error(f"Erro na análise de dados: {str(e)}")
        return jsonify({'error': f'Erro na análise: {str(e)}'}), 500

# Rota para servir arquivos de upload (para download)


@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """Endpoint para download de arquivos"""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        logger.error(f"Erro ao baixar arquivo: {str(e)}")
        return jsonify({'error': f'Erro ao baixar arquivo: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=config.DEBUG, host='0.0.0.0', port=5000)
