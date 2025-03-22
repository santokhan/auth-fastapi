FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN python -m venv venv

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0"]