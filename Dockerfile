FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    espeak-ng \
    libasound2-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

COPY src/ ./src/
COPY tests/ ./tests/

EXPOSE 8765

CMD ["voiceforge", "serve", "--host", "0.0.0.0", "--port", "8765"]
