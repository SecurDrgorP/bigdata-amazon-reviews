# Makefile for easy project management

.PHONY: help build up down logs clean test lint format

# Default target
help:
	@echo "Available commands:"
	@echo "  build     - Build all Docker images"
	@echo "  up        - Start all services"
	@echo "  down      - Stop all services"
	@echo "  logs      - Show logs from all services"
	@echo "  clean     - Clean up Docker resources"
	@echo "  test      - Run tests"
	@echo "  dev       - Start development environment"
	@echo "  prod      - Start production environment"

# Build all images
build:
	sudo docker compose build --no-cache

# Start all services
up:
	sudo docker compose up -d

# Start development environment
dev:
	sudo docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Start production environment
prod:
	sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Stop all services
down:
	sudo docker compose down

# Show logs
logs:
	sudo docker compose logs -f

# Show logs for specific service
logs-service:
	@read -p "Enter service name: " service; \
	sudo docker compose logs -f $$service

# Clean up Docker resources
clean:
	sudo docker compose down -v --remove-orphans
	sudo docker system prune -f
	sudo docker volume prune -f

# Run tests
test:
	sudo docker compose exec backend python -m pytest tests/
	sudo docker compose exec spark-consumer python -m pytest tests/

# Check service health
health:
	@echo "Checking service health..."
	@sudo docker compose ps
	@echo "\nKafka topics:"
	@sudo docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list
	@echo "\nMongoDB status:"
	@sudo docker compose exec mongodb mongosh --eval "db.adminCommand('ping')"

# Scale services
scale-spark:
	@read -p "Enter number of Spark workers: " workers; \
	sudo docker compose up -d --scale spark-worker=$$workers

# View service URLs
urls:
	@echo "Service URLs:"
	@echo "  Spark Master UI: http://localhost:8080"
	@echo "  Backend API: http://localhost:5000"
	@echo "  MongoDB: mongodb://localhost:27017"
	@echo "  Kafka: localhost:9092"

# Backup data
backup:
	@echo "Creating backup..."
	sudo docker compose exec mongodb mongodump --out /data/backup/$(shell date +%Y%m%d_%H%M%S)
	sudo docker cp mongodb:/data/backup ./backups/

# Restore data
restore:
	@read -p "Enter backup directory name: " backup; \
	sudo docker cp ./backups/$$backup mongodb:/data/restore/; \
	sudo docker compose exec mongodb mongorestore /data/restore/$$backup

# Monitor resources
monitor:
	@echo "Resource usage:"
	sudo docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

# Development setup
setup-dev:
	@echo "Setting up development environment..."
	cp .env.example .env
	@echo "Please edit .env file with your configuration"
	make build
	make up
	@echo "Development environment ready!"

# Production deployment
deploy-prod:
	@echo "Deploying to production..."
	git pull origin main
	make build
	make prod
	@echo "Production deployment complete!"
