FROM bitnami/spark:3.3

USER root
WORKDIR /app

COPY spark_consumer.py ./

# Create directories that will be populated by volume mounts
RUN mkdir -p utils model

# Install Python packages in the system Python that Spark uses
RUN pip install --upgrade pip && \
    pip install pymongo numpy pyspark

# Set PYTHONPATH to ensure Spark can find installed packages
ENV PYTHONPATH="${PYTHONPATH}:/opt/bitnami/python/lib/python3.9/site-packages"

CMD ["spark-submit", "--master", "spark://spark-master:7077", "--conf", "spark.pyspark.python=/opt/bitnami/python/bin/python", "--conf", "spark.pyspark.driver.python=/opt/bitnami/python/bin/python", "spark_consumer.py"]