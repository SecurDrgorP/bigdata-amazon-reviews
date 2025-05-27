import os
import re

from pyspark.sql.functions import col, current_timestamp

# Text cleaning function
def clean_text(text):
    if text is None:
        return ""
    # Convert to lowercase
    text = text.lower()
    # Remove punctuation and numbers
    text = re.sub(r'[^a-z\s]', '', text)
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# Simplified lemmatization (no spaCy for streaming)
def simple_lemmatize(text):
    if text is None:
        return ""
    return clean_text(text)


# Define function to write each micro-batch to MongoDB
def write_to_mongodb(batch_df, batch_id):
    """
    Write the batch DataFrame to MongoDB.
    """
    if not batch_df.isEmpty():
        # Select and rename columns for MongoDB
        batch_to_save = batch_df.select(
            col("reviewText").alias("text"),
            col("prediction"),
            col("asin"),
            col("reviewTime"),
            col("reviewerID"),
            current_timestamp().alias("ingestion_time")
        )
        
        # Write to MongoDB
        batch_to_save.write \
            .format("mongo") \
            .option("uri", "mongodb://mongodb:27017") \
            .option("database", "amazon_reviews") \
            .option("collection", "predictions") \
            .mode("append") \
            .save()
        
        print(f"Batch {batch_id} successfully written to MongoDB")
