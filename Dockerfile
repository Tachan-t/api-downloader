FROM python:3.10-slim

# Instala o FFmpeg no servidor Linux
RUN apt-get update && apt-get install -y ffmpeg

# Configura a pasta de trabalho
WORKDIR /app

# Copia os arquivos e instala as bibliotecas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto do seu código
COPY api_downloader.py .

# Roda o servidor usando o Gunicorn na porta que o Render pedir
CMD ["gunicorn", "-b", "0.0.0.0:10000", "api_downloader:app"]