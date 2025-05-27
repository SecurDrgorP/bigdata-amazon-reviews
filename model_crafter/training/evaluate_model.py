import sys
import os

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, rand
from pyspark.ml.feature import Tokenizer, StopWordsRemover, HashingTF, IDF, StringIndexer, NGram, VectorAssembler
from pyspark.ml.classification import LinearSVC, OneVsRest
from pyspark.ml import Pipeline
from pyspark.ml.evaluation import MulticlassClassificationEvaluator

from utils.for_evaluate_model import evaluate_per_class

# Create a Spark session
spark = SparkSession.builder \
    .appName("BalancedReviewSentimentClassifier") \
    .config("spark.driver.memory", "4g") \
    .config("spark.sql.shuffle.partitions", "20") \
    .config("spark.local.dir", "/tmp/spark-temp") \
    .config("spark.memory.fraction", "0.7") \
    .config("spark.memory.storageFraction", "0.2") \
    .getOrCreate()

# Reduce log verbosity
spark.sparkContext.setLogLevel("WARN")

# Load preprocessed CSV data
df = spark.read.csv("data/cleaned_reviews.csv", header=True, inferSchema=True)

# Check schema and nulls
print("Schema:")
df.printSchema()

# Keep only valid labels and cast to double
df = df.filter((col("label") == 0) | (col("label") == 1) | (col("label") == 2))
df = df.withColumn("label", col("label").cast("double"))

# Replace nulls in 'lemmatized_text' with empty string
df = df.fillna({'lemmatized_text': ''})

# Show class distribution BEFORE balancing
print("\nClass distribution BEFORE balancing:")
class_counts_before = df.groupBy("label").count().orderBy("label")
class_counts_before.show()

# ------- DATA REBALANCING -------

df_class_0 = df.filter(col("label") == 0.0)
df_class_1 = df.filter(col("label") == 1.0)
df_class_2 = df.filter(col("label") == 2.0)

count_class_0 = df_class_0.count()
count_class_1 = df_class_1.count()
count_class_2 = df_class_2.count()

print(f"Class 0: {count_class_0} samples")
print(f"Class 1: {count_class_1} samples")
print(f"Class 2: {count_class_2} samples")

# Subsample majority class 2 to at most 3x class 0
target_count_2 = min(count_class_0 * 3, count_class_2)
sampled_df_class_2 = df_class_2.orderBy(rand()).limit(int(target_count_2))

# Oversample minority classes
oversample_ratio_0 = max(1, int(target_count_2 / count_class_0))
oversample_ratio_1 = max(1, int(target_count_2 / count_class_1))

oversampled_df_class_0 = df_class_0
oversampled_df_class_1 = df_class_1

for _ in range(oversample_ratio_0 - 1):
    oversampled_df_class_0 = oversampled_df_class_0.union(df_class_0)

for _ in range(oversample_ratio_1 - 1):
    oversampled_df_class_1 = oversampled_df_class_1.union(df_class_1)

# Combine balanced data
balanced_df = oversampled_df_class_0.union(oversampled_df_class_1).union(sampled_df_class_2)

# Show class distribution AFTER balancing
print("\nClass distribution AFTER balancing:")
class_counts_after = balanced_df.groupBy("label").count().orderBy("label")
class_counts_after.show()

# Shuffle to remove ordering bias
balanced_df = balanced_df.orderBy(rand())

# Split into train/validation/test
train_df, temp_df = balanced_df.randomSplit([0.8, 0.2], seed=42)
validation_df, test_df = temp_df.randomSplit([0.5, 0.5], seed=42)

print(f"\nTraining set size: {train_df.count()} rows")
print(f"Validation set size: {validation_df.count()} rows")
print(f"Test set size: {test_df.count()} rows")

# Verify class balance in each split
print("\nTraining set class distribution:")
train_df.groupBy("label").count().orderBy("label").show()

print("\nValidation set class distribution:")
validation_df.groupBy("label").count().orderBy("label").show()

print("\nTest set class distribution:")
test_df.groupBy("label").count().orderBy("label").show()

# # Export test set in JSON directory
# test_json_dir = os.path.join("data", "test_data_dir")
# print(f"\nExporting test data to {test_json_dir}...")
# test_df.write.mode("overwrite").json(test_json_dir)

# Export single JSON file
test_single_file_path = os.path.join("data", "test_data.json")
test_pandas_df = test_df.toPandas()
test_pandas_df.to_json(test_single_file_path, orient='records', lines=True)
print(f"Test data exported as single JSON file: {test_single_file_path}")

# Export CSV if needed
test_csv_path = os.path.join("data", "test_data.csv")
test_pandas_df.to_csv(test_csv_path, index=False)
print(f"Test data exported as CSV: {test_csv_path}")

# Tokenization and n-grams
tokenizer = Tokenizer(inputCol="lemmatized_text", outputCol="words")
remover = StopWordsRemover(inputCol="words", outputCol="filtered_words")
bigram = NGram(n=2, inputCol="filtered_words", outputCol="bigrams")
trigram = NGram(n=3, inputCol="filtered_words", outputCol="trigrams")

# TF-IDF
hashingTF_uni = HashingTF(inputCol="filtered_words", outputCol="tf_uni", numFeatures=1000)
hashingTF_bi = HashingTF(inputCol="bigrams", outputCol="tf_bi", numFeatures=1000)
hashingTF_tri = HashingTF(inputCol="trigrams", outputCol="tf_tri", numFeatures=1000)
idf_uni = IDF(inputCol="tf_uni", outputCol="features_uni")
idf_bi = IDF(inputCol="tf_bi", outputCol="features_bi")
idf_tri = IDF(inputCol="tf_tri", outputCol="features_tri")

# Label indexing
label_indexer = StringIndexer(
    inputCol="label", 
    outputCol="indexedLabel",
    stringOrderType="alphabetAsc",
    handleInvalid="keep"
)

print("\nVerifying label mapping:")
label_model = label_indexer.fit(train_df)
print("Label ordering:", label_model.labelsArray[0])

# One-vs-Rest with LinearSVC
lsvc = LinearSVC(featuresCol="features", labelCol="indexedLabel", maxIter=50, regParam=0.1)
ovr = OneVsRest(classifier=lsvc, labelCol="indexedLabel", featuresCol="features")

pipeline = Pipeline(stages=[
    tokenizer, remover, bigram, trigram,
    hashingTF_uni, idf_uni, hashingTF_bi, idf_bi, hashingTF_tri, idf_tri,
    VectorAssembler(inputCols=["features_uni", "features_bi", "features_tri"], outputCol="features"),
    label_indexer,
    ovr
])

try:
    print("\nStarting model training...")
    model = pipeline.fit(train_df)
    
    print("Evaluating model on validation set...")
    val_predictions = model.transform(validation_df)
    
    evaluator = MulticlassClassificationEvaluator(
        labelCol="indexedLabel", 
        predictionCol="prediction", 
        metricName="f1"
    )
    val_f1 = evaluator.evaluate(val_predictions)
    
    evaluator.setMetricName("accuracy")
    val_accuracy = evaluator.evaluate(val_predictions)
    
    print(f"\nValidation results:")
    print(f"F1-score: {val_f1:.4f}")
    print(f"Accuracy: {val_accuracy:.4f}")
    
    print("\nValidation confusion matrix:")
    val_predictions.groupBy("label", "prediction").count().orderBy("label", "prediction").show()
    
    print("\nFinal evaluation on test set...")
    test_predictions = model.transform(test_df)
    
    print("\nSample test predictions:")
    test_predictions.select("lemmatized_text", "label", "prediction", "rawPrediction")\
        .show(5, truncate=30)
    
    print("\nTest prediction distribution:")
    test_predictions.groupBy("prediction").count().orderBy("prediction").show()
    
    print("\nTest confusion matrix:")
    test_predictions.groupBy("label", "prediction").count().orderBy("label", "prediction").show()
    
    test_f1 = evaluator.setMetricName("f1").evaluate(test_predictions)
    test_accuracy = evaluator.setMetricName("accuracy").evaluate(test_predictions)
    test_recall = evaluator.setMetricName("weightedRecall").evaluate(test_predictions)
    
    print(f"\nFinal test metrics:")
    print(f"F1-score: {test_f1:.4f}")
    print(f"Accuracy: {test_accuracy:.4f}")
    print(f"Weighted Recall: {test_recall:.4f}")
    
    model_path = "best_model/SVC_Model_2"
    model.write().overwrite().save(model_path)
    print(f"\nModel successfully saved at: {model_path}")

    metrics = evaluate_per_class(test_predictions)
    
    indexed_df = label_indexer.fit(train_df).transform(train_df)
    indexed_df.groupBy("indexedLabel").count().show()
    
except Exception as e:
    print(f"\nError during training: {e}")
    import traceback
    traceback.print_exc()
finally:
    spark.stop()
