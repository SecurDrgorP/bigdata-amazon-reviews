#!/bin/bash

# Quick Start Script for Big Data Amazon Reviews Project
# This script helps you run the project step by step

echo "🚀 Big Data Amazon Reviews - Quick Start Guide"
echo "================================================"
echo

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "📝 Setting up environment configuration..."
    cp .env.template .env
    echo "✅ Created .env file from template"
    echo "💡 You can edit .env file to customize your configuration"
    echo
fi

# Function to check if Docker is running
check_docker() {
    if sudo docker info > /dev/null 2>&1; then
        echo "✅ Docker is running"
        return 0
    else
        echo "❌ Docker is not running or not accessible"
        echo "💡 Please start Docker service: sudo systemctl start docker"
        return 1
    fi
}

# Function to show available options
show_options() {
    echo "Choose an option:"
    echo "  1) Start all services (recommended for first run)"
    echo "  2) Build and start services"
    echo "  3) Stop all services"
    echo "  4) View service logs"
    echo "  5) Check service health"
    echo "  6) View service URLs"
    echo "  7) Clean up resources"
    echo "  8) Exit"
    echo
    read -p "Enter your choice (1-8): " choice
}

# Function to start services
start_services() {
    echo "🏗️  Building and starting services..."
    echo "This may take a few minutes on first run..."
    
    # Build images first
    echo "📦 Building Docker images..."
    sudo docker compose build
    
    if [ $? -eq 0 ]; then
        echo "✅ Build completed successfully"
        echo "🚀 Starting services..."
        sudo docker compose up -d
        
        if [ $? -eq 0 ]; then
            echo "✅ All services started successfully!"
            echo
            echo "📊 Service Status:"
            sudo docker compose ps
            echo
            echo "🌐 Access your services:"
            echo "  • Web Dashboard: http://localhost:5000"
            echo "  • Spark UI: http://localhost:8080"
            echo "  • MongoDB: mongodb://localhost:27017"
            echo
            echo "⏳ Wait a few moments for all services to fully initialize..."
        else
            echo "❌ Failed to start services"
        fi
    else
        echo "❌ Build failed"
    fi
}

# Function to stop services
stop_services() {
    echo "🛑 Stopping all services..."
    sudo docker compose down
    echo "✅ All services stopped"
}

# Function to show logs
show_logs() {
    echo "📋 Available services:"
    sudo docker compose ps --format "table {{.Name}}\t{{.Status}}"
    echo
    read -p "Enter service name (or press Enter for all): " service
    
    if [ -z "$service" ]; then
        echo "📜 Showing logs for all services (Ctrl+C to exit):"
        sudo docker compose logs -f
    else
        echo "📜 Showing logs for $service (Ctrl+C to exit):"
        sudo docker compose logs -f "$service"
    fi
}

# Function to check health
check_health() {
    echo "🏥 Checking service health..."
    echo
    echo "📊 Service Status:"
    sudo docker compose ps
    echo
    
    echo "🔍 Detailed Health Check:"
    
    # Check Kafka
    echo "📡 Kafka Topics:"
    sudo docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list 2>/dev/null || echo "  ❌ Kafka not responding"
    
    # Check MongoDB
    echo "🍃 MongoDB Status:"
    sudo docker compose exec mongodb mongosh --eval "db.adminCommand('ping')" --quiet 2>/dev/null || echo "  ❌ MongoDB not responding"
    
    # Check Backend
    echo "🌐 Backend API:"
    curl -s http://localhost:5000 > /dev/null && echo "  ✅ Backend responding" || echo "  ❌ Backend not responding"
}

# Function to show URLs
show_urls() {
    echo "🌐 Service URLs:"
    echo "  📊 Web Dashboard: http://localhost:5000"
    echo "  ⚡ Spark Master UI: http://localhost:8080"
    echo "  🗄️  MongoDB: mongodb://localhost:27017"
    echo "  📡 Kafka: localhost:9092"
    echo
    echo "💡 Tip: Open these URLs in your browser to access the services"
}

# Function to clean up
cleanup() {
    echo "🧹 Cleaning up Docker resources..."
    sudo docker compose down -v --remove-orphans
    sudo docker system prune -f
    echo "✅ Cleanup completed"
}

# Main script
echo "🔍 Checking Docker status..."
if ! check_docker; then
    exit 1
fi
echo

# Main loop
while true; do
    show_options
    
    case $choice in
        1)
            start_services
            ;;
        2)
            echo "🏗️  Force rebuilding all images..."
            sudo docker compose build --no-cache
            start_services
            ;;
        3)
            stop_services
            ;;
        4)
            show_logs
            ;;
        5)
            check_health
            ;;
        6)
            show_urls
            ;;
        7)
            cleanup
            ;;
        8)
            echo "👋 Goodbye!"
            exit 0
            ;;
        *)
            echo "❌ Invalid choice. Please try again."
            ;;
    esac
    
    echo
    echo "Press Enter to continue..."
    read
    clear
done
