#!/bin/bash

# ML Pipeline Runner Script
set -e

echo "🎯 Amazon Reviews ML Pipeline Runner"
echo "===================================="

# Simple colored output functions
print_info() { echo -e "\033[34m[INFO]\033[0m $1"; }
print_success() { echo -e "\033[32m[SUCCESS]\033[0m $1"; }
print_error() { echo -e "\033[31m[ERROR]\033[0m $1"; }

# Check if data exists
if [ ! -f "data/reviews.json" ]; then
    print_error "data/reviews.json not found!"
    exit 1
fi

# Check Docker is available
if ! command -v docker compose &> /dev/null; then
    print_error "Docker Compose not found"
    exit 1
fi

# Run pipeline
print_info "Starting ML pipeline..."
if docker compose --profile ml-training up --build ml-pipeline; then
    print_success "Pipeline completed!"
else
    print_error "Pipeline failed"
    exit 1
fi

# Check outputs
echo ""
echo "📊 Results:"
echo "==========="

check_file() {
    if [ -f "$1" ]; then
        echo "✅ $1"
    else
        echo "❌ $1 (missing)"
    fi
}

check_file "data/cleaned_reviews.csv"
check_file "data/test_data.csv" 
check_file "data/test_data.json"

if [ -d "best_model" ] && [ "$(ls -A best_model)" ]; then
    echo "✅ best_model/ ($(ls best_model | wc -l) files)"
else
    echo "❌ best_model/ (empty or missing)"
fi

print_success "Done! 🎉"
