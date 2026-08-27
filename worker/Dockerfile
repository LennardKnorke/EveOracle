FROM python:3.12

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY worker ./worker
COPY shared ./shared

CMD ["python", "-m", "worker.main"]