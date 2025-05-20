import sys
import os

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, rand
from pyspark.ml.feature import Tokenizer, StopWordsRemover, HashingTF, IDF, StringIndexer, NGram, VectorAssembler, OneHotEncoder
from pyspark.ml.classification import RandomForestClassifier, GBTClassifier, MultilayerPerceptronClassifier
from pyspark.ml import Pipeline
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder

from utils.for_evaluate_model import evaluate_per_class

# Créer une session Spark
spark = SparkSession.builder \
    .appName("BalancedReviewSentimentClassifier") \
    .config("spark.driver.memory", "4g") \
    .config("spark.sql.shuffle.partitions", "20") \
    .config("spark.local.dir", "/tmp/spark-temp") \
    .config("spark.memory.fraction", "0.7") \
    .config("spark.memory.storageFraction", "0.2") \
    .getOrCreate()

# Configurer le niveau de log pour réduire les sorties
spark.sparkContext.setLogLevel("WARN")

# Charger les données (prétraitées en pandas et sauvegardées en CSV)
df = spark.read.csv("data/cleaned_reviews.csv", header=True, inferSchema=True)

# Vérifier le schéma et les données nulles
print("Schema:")
df.printSchema()

# Assurer que label est en format numérique et éliminer toute valeur aberrante
df = df.filter((col("label") == 0) | (col("label") == 1) | (col("label") == 2))
df = df.withColumn("label", col("label").cast("double"))

# Remplacer les valeurs nulles dans la colonne "lemmatized_text" par une chaîne vide
df = df.fillna({'lemmatized_text': ''})

# Afficher des statistiques sur les classes avant équilibrage
print("\nDistribution des classes AVANT équilibrage:")
class_counts_before = df.groupBy("label").count().orderBy("label")
class_counts_before.show()

# ------- RÉÉQUILIBRAGE DES DONNÉES -------

# 1. Séparer les données par classe
df_class_0 = df.filter(col("label") == 0.0)
df_class_1 = df.filter(col("label") == 1.0)
df_class_2 = df.filter(col("label") == 2.0)

# Compter les échantillons par classe
count_class_0 = df_class_0.count()
count_class_1 = df_class_1.count()
count_class_2 = df_class_2.count()

print(f"Classe 0: {count_class_0} échantillons")
print(f"Classe 1: {count_class_1} échantillons")
print(f"Classe 2: {count_class_2} échantillons")

# 2. Sous-échantillonner la classe majoritaire
# Limiter la classe 2 à max 3x la taille de la classe 0
target_count_2 = min(count_class_0 * 3, count_class_2)
sampled_df_class_2 = df_class_2.orderBy(rand()).limit(int(target_count_2))

# 3. Sur-échantillonner les classes minoritaires
# Calculer combien de fois nous devons dupliquer
oversample_ratio_0 = max(1, int(target_count_2 / count_class_0))
oversample_ratio_1 = max(1, int(target_count_2 / count_class_1))

# Suréchantillonnage par réplication
oversampled_df_class_0 = df_class_0
oversampled_df_class_1 = df_class_1

for _ in range(oversample_ratio_0 - 1):
    oversampled_df_class_0 = oversampled_df_class_0.union(df_class_0)

for _ in range(oversample_ratio_1 - 1):
    oversampled_df_class_1 = oversampled_df_class_1.union(df_class_1)

# 4. Combiner les données équilibrées
balanced_df = oversampled_df_class_0.union(oversampled_df_class_1).union(sampled_df_class_2)

# Afficher des statistiques sur les classes après équilibrage
print("\nDistribution des classes APRÈS équilibrage:")
class_counts_after = balanced_df.groupBy("label").count().orderBy("label")
class_counts_after.show()

# 5. Mélanger les données pour éviter les biais d'ordre
balanced_df = balanced_df.orderBy(rand())

# Séparation en ensembles d'entraînement/validation/test en préservant les proportions des classes
train_df, temp_df = balanced_df.randomSplit([0.8, 0.2], seed=42)
validation_df, test_df = temp_df.randomSplit([0.5, 0.5], seed=42)

print(f"\nDonnées d'entraînement: {train_df.count()} lignes")
print(f"Données de validation: {validation_df.count()} lignes")
print(f"Données de test: {test_df.count()} lignes")

# Vérifier l'équilibre dans les ensembles
print("\nDistribution des classes dans l'ensemble d'entraînement:")
train_df.groupBy("label").count().orderBy("label").show()

print("\nDistribution des classes dans l'ensemble de validation:")
validation_df.groupBy("label").count().orderBy("label").show()

print("\nDistribution des classes dans l'ensemble de test:")
test_df.groupBy("label").count().orderBy("label").show()

# Exporter le jeu de test en JSON
test_json_dir = os.path.join("data", "test_data_dir.json")
print(f"\nExportation des données de test vers {test_json_dir}...")
test_df.write.mode("overwrite").json(test_json_dir)

# Exporter un fichier JSON unique
test_single_file_path = os.path.join("data", "test_data.json")
test_pandas_df = test_df.toPandas()
test_pandas_df.to_json(test_single_file_path, orient='records', lines=True)
print(f"Données de test exportées en fichier JSON unique: {test_single_file_path}")

# Exporter en CSV pour une visualisation plus facile si nécessaire
test_csv_path = os.path.join("data", "test_data.csv")
test_pandas_df.to_csv(test_csv_path, index=False)
print(f"Données de test exportées en CSV: {test_csv_path}")

# Tokenisation
tokenizer = Tokenizer(inputCol="lemmatized_text", outputCol="words")
remover = StopWordsRemover(inputCol="words", outputCol="filtered_words")

# Ajouter extraction de bi-grammes et tri-grammes
bigram = NGram(n=2, inputCol="filtered_words", outputCol="bigrams")
trigram = NGram(n=3, inputCol="filtered_words", outputCol="trigrams")

# TF-IDF avec plus de features
# Traiter unigrammes, bigrammes et trigrammes séparément
hashingTF_uni = HashingTF(inputCol="filtered_words", outputCol="tf_uni", numFeatures=1000)  # Reduced from 5000
hashingTF_bi = HashingTF(inputCol="bigrams", outputCol="tf_bi", numFeatures=1000)          # Reduced from 5000
hashingTF_tri = HashingTF(inputCol="trigrams", outputCol="tf_tri", numFeatures=1000)       # Reduced from 5000

idf_uni = IDF(inputCol="tf_uni", outputCol="features_uni")
idf_bi = IDF(inputCol="tf_bi", outputCol="features_bi")
idf_tri = IDF(inputCol="tf_tri", outputCol="features_tri")

# Total size of feature vector (sum of all TF-IDF features)
feature_size = 3000  # 1000 for unigrams + 1000 for bigrams + 1000 for trigrams

# Indexation de la classe avec gestion des valeurs nulles
label_indexer = StringIndexer(
    inputCol="label", 
    outputCol="indexedLabel",
    stringOrderType="alphabetAsc",  # This will keep 0.0, 1.0, 2.0 order
    handleInvalid="keep"
)

# Add this code to verify label mapping
print("\nVérification du mapping des labels:")
label_model = label_indexer.fit(train_df)
print("Label ordering:", label_model.labelsArray[0])

# Encodage One-Hot de la variable cible
encoder = OneHotEncoder(inputCol="indexedLabel", outputCol="labelVec")

# Utiliser RandomForest au lieu de LogisticRegression
rf = RandomForestClassifier(
    featuresCol="features", 
    labelCol="indexedLabel",
    numTrees=20,
    maxDepth=5,
    maxBins=16,
    minInstancesPerNode=10,
    impurity="gini",
    seed=42
)

# Alternative: Try GBTClassifier which often performs better
gbt = GBTClassifier(
    featuresCol="features", 
    labelCol="indexedLabel",
    maxIter=50,
    maxDepth=6,
    stepSize=0.1
)

# Neural network explicitly supporting multi-class
mlp = MultilayerPerceptronClassifier(
    featuresCol="features",
    labelCol="indexedLabel",
    layers=[feature_size, 50, 3],  # 3 output nodes for 3 classes
    seed=42
)

# Create parameter grid
paramGrid = ParamGridBuilder() \
    .addGrid(rf.maxDepth, [5]) \
    .addGrid(rf.numTrees, [20]) \
    .build()

# Create cross-validator
crossval = CrossValidator(
    estimator=rf,
    estimatorParamMaps=paramGrid,
    evaluator=MulticlassClassificationEvaluator(labelCol="indexedLabel", predictionCol="prediction", metricName="f1"),
    numFolds=2  # Reduced from 3
)

# Pipeline complète
pipeline = Pipeline(stages=[
    tokenizer, remover, bigram, trigram,
    hashingTF_uni, idf_uni, hashingTF_bi, idf_bi, hashingTF_tri, idf_tri,
    VectorAssembler(inputCols=["features_uni", "features_bi", "features_tri"], outputCol="features"),
    label_indexer, encoder,
    crossval  # Use the cross-validator instead of direct classifier
])

try:
    # Entraîner le modèle sur les données d'entraînement
    print("\nEntraînement du modèle en cours...")
    model = pipeline.fit(train_df)
    
    # Évaluer sur les données de validation
    print("Évaluation du modèle sur l'ensemble de validation...")
    val_predictions = model.transform(validation_df)
    
    # Calculer les métriques d'évaluation sur la validation
    evaluator = MulticlassClassificationEvaluator(
        labelCol="indexedLabel", 
        predictionCol="prediction", 
        metricName="f1"
    )
    val_f1 = evaluator.evaluate(val_predictions)
    
    evaluator.setMetricName("accuracy")
    val_accuracy = evaluator.evaluate(val_predictions)
    
    print(f"\nRésultats de validation:")
    print(f"F1-score (validation): {val_f1:.4f}")
    print(f"Précision (validation): {val_accuracy:.4f}")
    
    # Matrice de confusion sur la validation
    print("\nMatrice de confusion (validation):")
    val_predictions.groupBy("label", "prediction").count().orderBy("label", "prediction").show()
    
    # Évaluation finale sur l'ensemble de test
    print("\nÉvaluation finale sur l'ensemble de test...")
    test_predictions = model.transform(test_df)
    
    # Afficher quelques prédictions
    print("\nExemples de prédictions (test):")
    test_predictions.select("lemmatized_text", "label", "prediction", "probability").show(5, truncate=30)
    
    # Afficher la distribution des prédictions sur l'ensemble de test
    print("\nDistribution des prédictions (test):")
    test_predictions.groupBy("prediction").count().orderBy("prediction").show()
    
    # Matrice de confusion simplifiée sur le test
    print("\nMatrice de confusion (test):")
    test_predictions.groupBy("label", "prediction").count().orderBy("label", "prediction").show()
    
    # Calculer les métriques finales sur l'ensemble de test
    test_f1 = evaluator.setMetricName("f1").evaluate(test_predictions)
    test_accuracy = evaluator.setMetricName("accuracy").evaluate(test_predictions)
    test_recall = evaluator.setMetricName("weightedRecall").evaluate(test_predictions)
    
    print(f"\nRésultats d'évaluation finaux (test):")
    print(f"F1-score: {test_f1:.4f}")
    print(f"Précision: {test_accuracy:.4f}")
    print(f"Recall pondéré: {test_recall:.4f}")
    
    # Sauvegarder le modèle
    model_path = "model/best_model/balanced_sentiment_model"
    model.write().overwrite().save(model_path)
    print(f"\nModèle sauvegardé avec succès à: {model_path}")


    # Call this function after model evaluation
    metrics = evaluate_per_class(test_predictions)
    
    # After applying StringIndexer, check distribution
    indexed_df = label_indexer.fit(train_df).transform(train_df)
    indexed_df.groupBy("indexedLabel").count().show()
    
except Exception as e:
    print(f"\nErreur pendant l'entraînement: {e}")
    import traceback
    traceback.print_exc()
finally:
    spark.stop()