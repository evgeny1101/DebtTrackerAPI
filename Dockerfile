FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

RUN mkdir -p /data && \
    useradd --uid 1001 --create-home appuser && \
    chown -R appuser:appuser /app /data

USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
