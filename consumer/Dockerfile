FROM bitnami/spark:3.3

USER root
WORKDIR /app

# Create necessary directories
RUN mkdir -p ./utils

COPY consumer/spark_consumer.py ./
COPY utils/for_spark_consumer.py ./utils/

# Install Python packages in the system Python that Spark uses
RUN pip install --upgrade pip && \
    pip install pymongo numpy

# Set PYTHONPATH to ensure Spark can find installed packages
ENV PYTHONPATH="${PYTHONPATH}:/opt/bitnami/python/lib/python3.9/site-packages"

# Updated command with local mode to avoid master connection issues
CMD ["spark-submit", "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0,org.mongodb.spark:mongo-spark-connector_2.12:3.0.2", "--conf", "spark.pyspark.python=/opt/bitnami/python/bin/python", "--conf", "spark.pyspark.driver.python=/opt/bitnami/python/bin/python", "spark_consumer.py"]