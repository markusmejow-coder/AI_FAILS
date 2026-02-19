FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg fonts-dejavu fonts-liberation python3-pil && rm -rf /var/lib/apt/lists/*

# Die dicken Google-Pakete sind raus, nur das winzige 'requests' ist für den Upload dazugekommen
RUN pip install --no-cache-dir Pillow==10.3.0 openai==1.30.0 requests

WORKDIR /app

# Wir erstellen nur die Zielordner auf dem Volume-Pfad
RUN mkdir -p /data/logs /data/archive /app/output

# Die Symlinks erstellen wir so, dass sie existieren, 
# aber wir erzwingen keine Neu-Erstellung durch Python im Dockerfile
RUN ln -sfn /data/logs /app/logs && \
    ln -sfn /data/archive /app/archive

RUN chmod -R 777 /data /app/output
COPY src/ /app/src/
RUN fc-cache -f -v

CMD ["python3", "/app/src/scheduler.py"]
