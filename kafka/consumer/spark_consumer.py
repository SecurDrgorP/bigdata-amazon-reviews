from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StringType, FloatType, ArrayType, LongType

# Créer une session Spark avec support Kafka
spark = SparkSession.builder \
    .appName("KafkaReviewConsumer") \
    .master("local[*]") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# Définir le schéma des messages JSON
schema = StructType() \
    .add("reviewerID", StringType()) \
    .add("asin", StringType()) \
    .add("reviewerName", StringType()) \
    .add("helpful", ArrayType(FloatType())) \
    .add("reviewText", StringType()) \
    .add("overall", FloatType()) \
    .add("summary", StringType()) \
    .add("unixReviewTime", LongType()) \
    .add("reviewTime", StringType())

# Lire depuis le topic Kafka
df_raw = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "reviews") \
    .option("startingOffsets", "latest") \
    .load()

# Extraire le contenu JSON
df_reviews = df_raw.selectExpr("CAST(value AS STRING) as json") \
    .select(from_json(col("json"), schema).alias("data")) \
    .select("data.*")

# Affichage dans la console (en continu)
query = df_reviews.writeStream \
    .outputMode("append") \
    .format("console") \
    .option("truncate", False) \
    .start()

query.awaitTermination()
