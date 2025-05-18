from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, when, isnan, lit, rand
from pyspark.ml.feature import Tokenizer, StopWordsRemover, HashingTF, IDF, StringIndexer, NGram, VectorAssembler
from pyspark.ml.classification import RandomForestClassifier, GBTClassifier  # Changed from LogisticRegression
from pyspark.ml import Pipeline
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder
from pyspark.mllib.evaluation import MulticlassMetrics
import pandas as pd
import matplotlib.pyplot as plt

# Créer une session Spark
spark = SparkSession.builder \
    .appName("BalancedReviewSentimentClassifier") \
    .config("spark.driver.memory", "4g") \
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

# Tokenisation
tokenizer = Tokenizer(inputCol="lemmatized_text", outputCol="words")
remover = StopWordsRemover(inputCol="words", outputCol="filtered_words")

# Ajouter extraction de bi-grammes et tri-grammes
bigram = NGram(n=2, inputCol="filtered_words", outputCol="bigrams")
trigram = NGram(n=3, inputCol="filtered_words", outputCol="trigrams")

# TF-IDF avec plus de features
# Traiter unigrammes, bigrammes et trigrammes séparément
hashingTF_uni = HashingTF(inputCol="filtered_words", outputCol="tf_uni", numFeatures=5000)
hashingTF_bi = HashingTF(inputCol="bigrams", outputCol="tf_bi", numFeatures=5000)
hashingTF_tri = HashingTF(inputCol="trigrams", outputCol="tf_tri", numFeatures=5000)

idf_uni = IDF(inputCol="tf_uni", outputCol="features_uni")
idf_bi = IDF(inputCol="tf_bi", outputCol="features_bi")
idf_tri = IDF(inputCol="tf_tri", outputCol="features_tri")

# Indexation de la classe avec gestion des valeurs nulles
label_indexer = StringIndexer(
    inputCol="label", 
    outputCol="indexedLabel", 
    handleInvalid="skip"
)

# Utiliser RandomForest au lieu de LogisticRegression
rf = RandomForestClassifier(
    featuresCol="features",  # Updated to use combined features
    labelCol="indexedLabel",
    numTrees=200,            # More trees for better ensemble effect
    maxDepth=8,              # Slightly reduced to prevent overfitting
    maxBins=32,              # Increase bins for better splits
    minInstancesPerNode=5,   # Require more samples per node
    impurity="entropy",      # Try entropy instead of gini
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

# Create parameter grid
paramGrid = ParamGridBuilder() \
    .addGrid(rf.maxDepth, [6, 8, 10]) \
    .addGrid(rf.numTrees, [100, 200]) \
    .addGrid(rf.impurity, ["gini", "entropy"]) \
    .build()

# Create cross-validator
crossval = CrossValidator(
    estimator=rf,
    estimatorParamMaps=paramGrid,
    evaluator=MulticlassClassificationEvaluator(labelCol="indexedLabel", predictionCol="prediction", metricName="f1"),
    numFolds=3  # Use 3 folds for faster training
)

# Pipeline complète
pipeline = Pipeline(stages=[
    tokenizer, remover, bigram, trigram,
    hashingTF_uni, idf_uni, hashingTF_bi, idf_bi, hashingTF_tri, idf_tri,
    VectorAssembler(inputCols=["features_uni", "features_bi", "features_tri"], outputCol="features"),
    label_indexer,
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
    model_path = "model/truly_balanced_sentiment_model"
    model.write().overwrite().save(model_path)
    print(f"\nModèle sauvegardé avec succès à: {model_path}")
    
    # Add per-class metrics evaluation
    def evaluate_per_class(predictions, label_col="indexedLabel", pred_col="prediction"):
        # Get predictions and labels
        predictionAndLabels = predictions.select(pred_col, label_col).rdd
        metrics = MulticlassMetrics(predictionAndLabels)
        
        # Overall metrics
        print(f"Overall Accuracy: {metrics.accuracy}")
        print(f"Weighted Precision: {metrics.weightedPrecision}")
        print(f"Weighted Recall: {metrics.weightedRecall}")
        print(f"Weighted F1 Score: {metrics.weightedFMeasure()}")
        
        # Per-class metrics
        print("\nPer-Class Metrics:")
        labels = predictions.select(label_col).distinct().rdd.map(lambda x: x[0]).collect()
        for label in sorted(labels):
            print(f"\nClass {label}:")
            print(f"Precision: {metrics.precision(label):.4f}")
            print(f"Recall: {metrics.recall(label):.4f}")
            print(f"F1 Score: {metrics.fMeasure(label):.4f}")
        
        # Return metrics for further analysis
        return metrics

    # Call this function after model evaluation
    metrics = evaluate_per_class(test_predictions)
    
except Exception as e:
    print(f"\nErreur pendant l'entraînement: {e}")
    import traceback
    traceback.print_exc()
finally:
    spark.stop()