#!/bin/bash

# ML Pipeline Runner Script
# This script runs the ML pipeline using Docker Compose

set -e  # Exit on any error

echo "🎯 Amazon Reviews ML Pipeline Runner"
echo "===================================="

# Function to print colored output
print_status() {
    echo -e "\033[1;34m[INFO]\033[0m $1"
}

print_success() {
    echo -e "\033[1;32m[SUCCESS]\033[0m $1"
}

print_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

print_warning() {
    echo -e "\033[1;33m[WARNING]\033[0m $1"
}

# Check if data file exists
if [ ! -f "data/reviews.json" ]; then
    print_error "data/reviews.json not found!"
    print_warning "Please ensure your review data is available at data/reviews.json"
    exit 1
fi

print_status "Found input data at data/reviews.json"

# Create necessary directories
mkdir -p data model best_model

print_status "Created necessary directories"

# Run the ML pipeline using Docker Compose
print_status "Starting ML pipeline execution..."
if docker-compose --profile ml-training up --build ml-pipeline; then
    print_success "ML pipeline completed successfully!"
else
    print_error "ML pipeline failed"
    exit 1
fi

# Check if model was created
if [ -d "best_model" ] && [ "$(ls -A best_model)" ]; then
    print_success "Model artifacts found in best_model/"
    ls -la best_model/
else
    print_warning "No model artifacts found in best_model/"
fi

# Check for generated files
echo ""
echo "📊 Pipeline Summary:"
echo "==================="
if [ -f "data/cleaned_reviews.csv" ]; then
    echo "✅ data/cleaned_reviews.csv (processed training data)"
else
    echo "❌ data/cleaned_reviews.csv (missing)"
fi

if [ -f "data/test_data.csv" ]; then
    echo "✅ data/test_data.csv (test dataset)"
else
    echo "❌ data/test_data.csv (missing)"
fi

if [ -f "data/test_data.json" ]; then
    echo "✅ data/test_data.json (test dataset in JSON)"
else
    echo "❌ data/test_data.json (missing)"
fi

echo ""
print_success "ML Pipeline execution completed! 🎉"
