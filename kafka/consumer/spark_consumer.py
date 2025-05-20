from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.sql.functions import from_json, col, udf, lit, current_timestamp
from pyspark.sql.types import *
import os
import sys

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from utils.for_spark_consumer import clean_text, simple_lemmatize, write_to_mongodb

# Create a Spark session with Kafka and MongoDB support
spark = SparkSession.builder \
    .appName("KafkaReviewConsumer") \
    .config(
        "spark.jars.packages",
        "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5,"
        "org.mongodb.spark:mongo-spark-connector_2.12:3.0.2"
    ) \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# Register UDFs
clean_text_udf = udf(clean_text, StringType())
lemmatize_udf = udf(simple_lemmatize, StringType())

# Load the model
try:
    model = PipelineModel.load("model/best_model/balanced_sentiment_model")
    print("Model loaded successfully!")
except Exception as e:
    print(f"Error loading model: {e}")
    exit(1)

# Define the Kafka message schema
schema = StructType() \
    .add("reviewText", StringType()) \
    .add("overall", FloatType()) \
    .add("reviewTime", StringType()) \
    .add("reviewerID", StringType()) \
    .add("asin", StringType())

broker = os.getenv("KAFKA_BROKER")
topic = os.getenv("KAFKA_TOPIC")

# Read messages from Kafka
df_raw = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", broker) \
    .option("subscribe", topic) \
    .option("startingOffsets", "latest") \
    .load()

# Parse JSON payload
df_json = df_raw.selectExpr("CAST(value AS STRING) as json") \
    .select(from_json(col("json"), schema).alias("data")) \
    .select("data.*")

# Apply preprocessing to add the lemmatized_text column
df_preprocessed = df_json \
    .withColumn("lemmatized_text", lemmatize_udf(col("reviewText"))) \
    .withColumn("label", lit(0.0))  # add dummy label for the pipeline

print("Schema after preprocessing:")
df_preprocessed.printSchema()

# Run the model
df_predicted = model.transform(df_preprocessed)

# Select fields to save to MongoDB
df_to_save = df_predicted.select(
    col("reviewText").alias("text"),
    col("prediction"),
    col("asin"),
    col("reviewTime"),
    col("reviewerID")
)

# Add ingestion timestamp in UTC
df_to_save = df_to_save.withColumn("ingestion_time", current_timestamp())

# Ensure checkpoint directory exists
os.makedirs("/tmp/checkpoint", exist_ok=True)

# Debug: print predictions to console
console_query = df_predicted.select(
    "prediction", "reviewText", "overall", "lemmatized_text", "probability"
).writeStream \
    .outputMode("append") \
    .format("console") \
    .option("truncate", False) \
    .start()

# Write each batch to MongoDB
mongo_query = df_predicted.writeStream \
    .foreachBatch(write_to_mongodb) \
    .outputMode("append") \
    .option("checkpointLocation", "/tmp/checkpoint") \
    .start()

# Await termination of both streams
console_query.awaitTermination()
mongo_query.awaitTermination()
