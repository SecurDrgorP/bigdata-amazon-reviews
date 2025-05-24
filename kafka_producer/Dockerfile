FROM python:3.9-slim

WORKDIR /app

COPY kafka_producer.py ./

# Data is mounted via volume, no need to copy it here
RUN pip install kafka-python

CMD ["python", "kafka_producer.py"]