FROM python:3.11-slim

RUN groupadd --gid 1001 appuser \
 && useradd --uid 1001 --gid appuser --no-create-home appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY templates ./templates/

RUN mkdir -p /app/log_files && chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

CMD ["python", "app.py"]
