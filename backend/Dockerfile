FROM python:3.12-slim

# 영상 렌더(ffmpeg) + 한글 자막 폰트(fonts-noto-cjk) — root 단계에서 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH

WORKDIR /app
COPY --chown=user requirements-deploy.txt .
RUN pip install --user --no-cache-dir -r requirements-deploy.txt

COPY --chown=user app ./app
COPY --chown=user assets ./assets

EXPOSE 7860
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "7860"]
