FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies and Java in one layer
RUN apt-get update && apt-get install -y \
    build-essential \
    openjdk-17-jdk-headless \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set JAVA_HOME
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH=$PATH:$JAVA_HOME/bin

# Install Spark
ENV SPARK_VERSION=3.4.1
ENV HADOOP_VERSION=3
ENV SPARK_HOME=/opt/spark
ENV PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
ENV PYSPARK_PYTHON=python3
ENV PYSPARK_DRIVER_PYTHON=python3

RUN wget -q https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz \
    && tar -xzf spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz \
    && mv spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION} /opt/spark \
    && rm spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz

# Copy requirements first for better caching
COPY requirements.txt /app/

# Install Python dependencies in one layer
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir \
    pyspark==3.4.1 \
    scikit-learn==1.3.0 \
    pandas==2.0.3 \
    numpy==1.24.3 \
    spacy==3.6.1 \
    joblib==1.3.2 && \
    python -m spacy download en_core_web_sm

# Copy only necessary project files
COPY model_crafter/preprocessing/ /app/preprocessing/
COPY model_crafter/training/ /app/training/
COPY utils/for_evaluate_model.py /app/utils/

# Create necessary directories
RUN mkdir -p /app/data /app/best_model /app/utils

# Make scripts executable
RUN chmod +x /app/preprocessing/clean_data.py

# Set proper Python path
ENV PYTHONPATH=/app

# Run the preprocessing and evaluation scripts sequentially
CMD ["sh", "-c", "echo 'Starting data preprocessing...' && python /app/preprocessing/clean_data.py && echo 'Starting model training...' && python /app/training/evaluate_model.py && echo 'Pipeline completed successfully!'"]
