FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    QLEARNING_ENV=production

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY qlearning/ qlearning/
COPY web/ web/
COPY run.py .
COPY assets/ assets/

EXPOSE 8080

CMD ["python", "run.py", "web", "--host", "0.0.0.0", "--no-browser"]
