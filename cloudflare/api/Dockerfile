# Librarian backend for Cloudflare Containers: the same Python pipeline as on a laptop (demo/server.py + model server).
# Build context: cloudflare/api (run tools/build_backend_bundle.py first to fill ./bundle).
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HF_HOME=/models TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir sentence-transformers==6.2.0 transformers==5.22.1 bm25s==0.3.16 PyStemmer==3.1.0 \
    numpy==2.5.4 scipy==1.18.1 "websockets>=14" huggingface_hub
RUN python -c "from huggingface_hub import snapshot_download as d; d('BAAI/bge-small-en-v1.5'); d('cross-encoder/ms-marco-MiniLM-L-6-v2')"
ENV HF_HUB_OFFLINE=1
# organisers' kit (no LICENSE upstream: fetched at build time, never copied into our repo)
RUN git clone -q https://github.com/RxAI-dev/memory-challenge.git /app/memory-challenge \
    && git -C /app/memory-challenge checkout -q f0a317d
# the team's archive importer (demo/ingest.py, /api/upload)
RUN pip install --no-cache-dir python-dateutil
COPY bundle/ /app/
COPY reactor.sh start.sh /app/
RUN chmod +x /app/reactor.sh /app/start.sh && touch /app/reactor.env
WORKDIR /app/librarian
EXPOSE 8800
CMD ["/app/start.sh"]
