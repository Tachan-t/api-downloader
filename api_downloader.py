from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import threading
import uuid
import os
import tempfile
import glob

app = Flask(__name__)
CORS(app)

tarefas = {}

def hook_progresso(d, task_id):
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
        baixado = d.get('downloaded_bytes', 0)
        if total > 0:
            porcentagem = (baixado / total) * 100
            tarefas[task_id]['progresso'] = porcentagem
            tarefas[task_id]['status'] = 'downloading'
            
    elif d['status'] == 'finished':
        tarefas[task_id]['status'] = 'processing'

def trabalhador_download(url, formato, task_id):
    tarefas[task_id] = {'status': 'starting', 'progresso': 0}
    
    # 🔥 CLOUD: Usa a pasta temporária do sistema operacional (Linux ou Windows)
    pasta_temp = tempfile.gettempdir()
    
    # Colocamos o task_id no nome para não misturar se duas pessoas baixarem ao mesmo tempo
    template_saida = os.path.join(pasta_temp, f"{task_id}_%(title)s.%(ext)s")

    opts = {
        'outtmpl': template_saida,
        'progress_hooks': [lambda d: hook_progresso(d, task_id)],
        'quiet': True,
        'no_warnings': True,
        
        # 🔥 O PASSAPORTE: O yt-dlp vai ler este arquivo para se autenticar
        'cookiefile': 'cookies.txt', 
        
        'extractor_args': {
            'youtube': ['player_client=android,web']
        }
    }

    if formato == 'audio':
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
    elif formato == '720p':
        opts['format'] = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        opts['merge_output_format'] = 'mp4'
    else:
        opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        opts['merge_output_format'] = 'mp4'

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            # Baixa o vídeo e pega as informações
            info = ydl.extract_info(url, download=True)
            arquivo_esperado = ydl.prepare_filename(info)
            
            # Como o FFmpeg pode mudar a extensão (ex: .webm para .mp3), 
            # buscamos o arquivo real que foi gerado começando com o nosso task_id
            nome_base = os.path.splitext(arquivo_esperado)[0]
            arquivos_encontrados = glob.glob(f"{nome_base}*")
            
            if arquivos_encontrados:
                tarefas[task_id]['arquivo'] = arquivos_encontrados[0]
                tarefas[task_id]['status'] = 'completed'
            else:
                tarefas[task_id]['status'] = 'error'
                tarefas[task_id]['erro'] = "Arquivo final não encontrado."

    except Exception as e:
        tarefas[task_id]['status'] = 'error'
        tarefas[task_id]['erro'] = str(e)

@app.route('/api/download', methods=['POST'])
def iniciar_download():
    dados = request.json
    url = dados.get('url')
    formato = dados.get('formato', 'best')
    task_id = str(uuid.uuid4())
    
    thread = threading.Thread(target=trabalhador_download, args=(url, formato, task_id))
    thread.start()
    
    return jsonify({'task_id': task_id})

@app.route('/api/status/<task_id>', methods=['GET'])
def checar_status(task_id):
    return jsonify(tarefas.get(task_id, {'status': 'not_found'}))

# 🔥 NOVA ROTA CLOUD: Envia o arquivo do servidor para o navegador do usuário
@app.route('/api/baixar-arquivo/<task_id>', methods=['GET'])
def enviar_arquivo(task_id):
    if task_id in tarefas and 'arquivo' in tarefas[task_id]:
        caminho = tarefas[task_id]['arquivo']
        if os.path.exists(caminho):
            # as_attachment=True força o navegador a fazer o download em vez de tentar tocar o vídeo
            return send_file(caminho, as_attachment=True)
    return "Arquivo não encontrado ou expirado", 404

if __name__ == '__main__':
    print("🚀 API Cloud-Ready rodando na porta 5000...")
    app.run(port=5000, host='0.0.0.0') # host='0.0.0.0' é necessário para nuvem