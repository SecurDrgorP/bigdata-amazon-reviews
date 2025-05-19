from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.sql.functions import from_json, col, udf, lit, current_timestamp
from pyspark.sql.types import *
import os

from utils.for_spark_consumer import clean_text, simple_lemmatize, write_to_mongodb


# Créer une session Spark avec support Kafka et MongoDB
spark = SparkSession.builder \
    .appName("KafkaReviewConsumer") \
    .config("spark.jars.packages", 
            "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5,org.mongodb.spark:mongo-spark-connector_2.12:3.0.2") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# Enregistrer les fonctions UDF
clean_text_udf = udf(clean_text, StringType())
lemmatize_udf = udf(simple_lemmatize, StringType())

# Charger le modèle
try:
    model = PipelineModel.load("model/best_model/truly_balanced_sentiment_model")
    print("Modèle chargé avec succès!")
except Exception as e:
    print(f"Erreur lors du chargement du modèle: {e}")
    exit(1)

# Schéma du flux Kafka
schema = StructType() \
    .add("reviewText", StringType()) \
    .add("overall", FloatType()) \
    .add("reviewTime", StringType()) \
    .add("reviewerID", StringType()) \
    .add("asin", StringType())

# Lire les messages Kafka
df_raw = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "reviews") \
    .option("startingOffsets", "latest") \
    .load()

# Convertir le JSON
df_json = df_raw.selectExpr("CAST(value AS STRING) as json") \
    .select(from_json(col("json"), schema).alias("data")) \
    .select("data.*")

# Appliquer le prétraitement pour créer la colonne lemmatized_text
df_preprocessed = df_json \
    .withColumn("lemmatized_text", lemmatize_udf(col("reviewText"))) \
    .withColumn("label", lit(0.0))  # Add dummy label column for the model pipeline

# Afficher le schéma pour vérifier
print("Schéma après prétraitement:")
df_preprocessed.printSchema()

# Préparer les données pour le modèle
df_predicted = model.transform(df_preprocessed)

# Format data for MongoDB
df_to_save = df_predicted.select(
    col("reviewText").alias("text"),
    col("prediction"),
    col("asin"),
    col("reviewTime"),
    col("reviewerID")
)

# Ajouter une colonne horodatée en UTC
df_to_save = df_to_save.withColumn("ingestion_time", current_timestamp())

# Create directory for checkpoint if it doesn't exist
os.makedirs("/tmp/checkpoint", exist_ok=True)

# Affichage des résultats dans la console (pour debug)
console_query = df_predicted.select("prediction", "reviewText", "overall", "lemmatized_text", "probability") \
    .writeStream \
    .outputMode("append") \
    .format("console") \
    .option("truncate", False) \
    .start()

# Use foreachBatch instead of direct MongoDB writer
mongo_query = df_predicted \
    .writeStream \
    .foreachBatch(write_to_mongodb) \
    .outputMode("append") \
    .option("checkpointLocation", "/tmp/checkpoint") \
    .start()

# Wait for both queries to terminate
console_query.awaitTermination()
mongo_query.awaitTermination()
