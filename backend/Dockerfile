FROM python:3.12-slim

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH

WORKDIR /app
COPY --chown=user requirements-deploy.txt .
RUN pip install --user --no-cache-dir -r requirements-deploy.txt

COPY --chown=user app ./app

EXPOSE 7860
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "7860"]
