from pyspark.mllib.evaluation import MulticlassMetrics

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