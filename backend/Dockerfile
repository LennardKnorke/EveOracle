FROM python:3.12-slim


WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

#RUN pip install --no-cache-dir \
#    torch==2.9.1 \
#    --index-url https://download.pytorch.org/whl/cu126


COPY . .

CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]