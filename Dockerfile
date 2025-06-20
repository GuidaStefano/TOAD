FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install Flask

EXPOSE 5000

CMD ["python", "server.py"]
