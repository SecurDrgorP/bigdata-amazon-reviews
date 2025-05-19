import re

from pyspark.sql.functions import col, current_timestamp

# Fonction de nettoyage du texte
def clean_text(text):
    if text is None:
        return ""
    # Convert to lowercase
    text = text.lower()
    # Remove punctuation and numbers
    text = re.sub(r'[^a-z\s]', '', text)
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# Version simplifiée de lemmatization (sans spaCy pour le streaming)
def simple_lemmatize(text):
    # This is a simplified version - in production you might want to use a proper lemmatizer
    if text is None:
        return ""
    return clean_text(text)


# Define function to write each batch to MongoDB
def write_to_mongodb(batch_df, batch_id):
    if not batch_df.isEmpty():
        # Format data for MongoDB
        batch_to_save = batch_df.select(
            col("reviewText").alias("text"),
            col("prediction"),
            col("asin"),
            col("reviewTime"),
            col("reviewerID")
        )
        
        # Add timestamp
        batch_to_save = batch_to_save.withColumn("ingestion_time", current_timestamp())
        
        # Save to MongoDB (using standard batch writes, not streaming)
        batch_to_save.write \
            .format("mongo") \
            .option("uri", "mongodb://localhost:27017/amazon_reviews.predictions") \
            .mode("append") \
            .save()
        
        print(f"Batch {batch_id}: Written {batch_df.count()} records to MongoDB")
