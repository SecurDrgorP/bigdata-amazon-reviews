#!/usr/bin/env python3
"""
Data preprocessing script for Amazon reviews sentiment analysis.
This script cleans and prepares the raw review data for machine learning.
"""

import pandas as pd
import numpy as np
import spacy
import re
import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split

def create_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs("data", exist_ok=True)
    print("Created data directory.")

def load_data():
    """Load raw review data from JSON file."""
    print("Loading data...")
    try:
        data = pd.read_json("data/reviews.json", lines=True)
        print(f"Loaded data: {data.shape[0]} reviews")
        return data
    except FileNotFoundError:
        print("Error: data/reviews.json not found!")
        raise

def explore_data(data):
    """Display basic information about the dataset."""
    print("\nData preview:")
    print(data.head(2))
    
    print("\nColumn types:")
    print(data.dtypes)
    
    print("\nStatistics on ratings (overall):")
    print(data['overall'].describe())
    print("\nDistribution of ratings:")
    print(data['overall'].value_counts().sort_index())
    
    print("\nChecking for null values:")
    print(data.isnull().sum())

def clean_text_data(data):
    """Clean and preprocess text data."""
    print("\nCleaning text...")
    
    def clean_text(text):
        """Clean individual text entries."""
        # Convert to string in case we have non-string inputs
        text = str(text)
        # Remove non-alphabetic characters (except spaces)
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        # Convert to lowercase
        text = text.lower()
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    data['cleaned_text'] = data['reviewText'].apply(clean_text)
    
    # Check for empty text after cleaning
    empty_text_count = (data['cleaned_text'] == '').sum()
    print(f"Empty texts after cleaning: {empty_text_count}")
    if empty_text_count > 0:
        # Replace empty text with a placeholder
        data['cleaned_text'] = data['cleaned_text'].replace('', 'no text available')
    
    return data

def setup_spacy():
    """Setup spaCy model for lemmatization."""
    print("\nLoading spaCy model...")
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        print("Downloading spaCy model...")
        import subprocess
        subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
        nlp = spacy.load("en_core_web_sm")
    return nlp

def lemmatize_text(data, nlp):
    """Apply lemmatization to cleaned text."""
    print("Lemmatizing texts...")
    
    def lemmatize(text):
        """Lemmatize individual text."""
        # Limit text length for processing efficiency
        text = text[:100000]  # Limit to first 100K chars to avoid memory issues
        doc = nlp(text)
        # Get lemmas for tokens that aren't stop words
        lemmas = [token.lemma_ for token in doc if not token.is_stop]
        if not lemmas:  # If all tokens were stop words
            return text  # Return original cleaned text
        return ' '.join(lemmas)
    
    # Apply lemmatization with error handling
    print("Applying lemmatization...")
    lemmatized_texts = []
    for i, text in enumerate(data['cleaned_text']):
        try:
            lemmatized = lemmatize(text)
            lemmatized_texts.append(lemmatized)
            if i % 1000 == 0:
                print(f"Processing: {i}/{len(data)}")
        except Exception as e:
            print(f"Error during lemmatization at index {i}: {e}")
            lemmatized_texts.append(text)  # Use cleaned text as fallback
    
    data['lemmatized_text'] = lemmatized_texts
    return data

def create_labels(data):
    """Create sentiment labels based on ratings."""
    print("\nDefining sentiment classes...")
    
    def label(overall):
        """Convert rating to sentiment label."""
        # Ensure overall is a number
        try:
            overall = float(overall)
        except (ValueError, TypeError):
            return None  # Return None for invalid values
            
        if overall < 3:
            return 0  # negative
        elif overall == 3:
            return 1  # neutral
        else:
            return 2  # positive
    
    data['label'] = data['overall'].apply(label)
    
    # Verify there are no None values in label
    null_labels = data['label'].isnull().sum()
    if null_labels > 0:
        print(f"WARNING: {null_labels} null labels found!")
        print("Removing rows with null labels...")
        data = data.dropna(subset=['label'])
    
    # Ensure label is integer type
    data['label'] = data['label'].astype(int)
    
    print("\nDistribution of sentiment classes:")
    print(data['label'].value_counts().sort_index())
    
    return data

def vectorize_text(data):
    """Create TF-IDF vectors from lemmatized text."""
    print("\nTF-IDF Vectorization...")
    vectorizer = TfidfVectorizer(max_features=5000)
    X = vectorizer.fit_transform(data['lemmatized_text'])
    
    print(f"Shape of the vectorized corpus: {X.shape}")
    return X, vectorizer

def split_data(X, data):
    """Split data into train/validation/test sets."""
    print("\nSplitting data into train/val/test...")
    y = data['label']
    
    # Split 80/20 first, then split the 20% into validation and test
    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.2, random_state=42)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5)
    
    print(f"Training set: {X_train.shape[0]} samples")
    print(f"Validation set: {X_val.shape[0]} samples")
    print(f"Test set: {X_test.shape[0]} samples")
    
    return X_train, X_val, X_test, y_train, y_val, y_test

def save_processed_data(data, vectorizer, nlp, X_train, X_val, X_test, y_train, y_val, y_test):
    """Save all processed data and models."""
    print("\nSaving processed data...")
    
    # Saving for PySpark/ML
    print("Saving as CSV (for Spark)...")
    # Select columns needed for Spark ML
    columns_for_spark = ['reviewerID', 'overall', 'lemmatized_text', 'label']
    data_for_spark = data[columns_for_spark].copy()
    
    # Final verification before saving
    print("\nFinal verification before saving:")
    print("Column types:")
    print(data_for_spark.dtypes)
    print("\nPreview of data to be saved:")
    print(data_for_spark.head())
    
    # Save to CSV
    data_for_spark.to_csv("data/cleaned_reviews.csv", index=False)

def main():
    """Main preprocessing pipeline."""
    try:
        # Create directories
        create_directories()
        
        # Load and explore data
        data = load_data()
        explore_data(data)
        
        # Clean text data
        data = clean_text_data(data)
        
        # Setup spaCy and lemmatize
        nlp = setup_spacy()
        data = lemmatize_text(data, nlp)
        
        # Create sentiment labels
        data = create_labels(data)
        
        # Vectorize text
        X, vectorizer = vectorize_text(data)
        
        # Split data
        X_train, X_val, X_test, y_train, y_val, y_test = split_data(X, data)
        
        # Save processed data
        save_processed_data(data, vectorizer, nlp, X_train, X_val, X_test, y_train, y_val, y_test)
        
        print("\n✅ Data preprocessing completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during preprocessing: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()