FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY docs ./docs
COPY data/eval_questions.json ./data/eval_questions.json
COPY scripts ./scripts

# The search index is written here; mount a volume on it to keep it between runs.
RUN useradd --create-home appuser \
    && mkdir -p /app/data/index \
    && chown -R appuser /app/data /app/docs
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
