#!/bin/bash

echo "🚀 Starting Enhanced Real-time Sentiment Dashboard"
echo "================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📋 Checking Docker services...${NC}"

# Check if docker-compose is available
if ! command -v sudo docker compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose not found. Please install docker-compose.${NC}"
    exit 1
fi

# Stop any existing containers
echo -e "${YELLOW}🛑 Stopping existing containers...${NC}"
sudo docker compose down

# Build and start services
echo -e "${BLUE}🔨 Building and starting services...${NC}"
sudo docker compose up --build -d

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
sleep 30

# Check service status
echo -e "${BLUE}📊 Service Status:${NC}"
echo "================================="

services=("zookeeper" "kafka" "mongodb" "spark-master" "flask-backend")

for service in "${services[@]}"; do
    if sudo docker compose ps $service | grep "Up" &> /dev/null; then
        echo -e "${GREEN}✅ $service: Running${NC}"
    else
        echo -e "${RED}❌ $service: Not running${NC}"
    fi
done

echo ""
echo -e "${GREEN}🎉 Enhanced Dashboard Features:${NC}"
echo "=================================="
echo "📊 Real-time sentiment charts"
echo "📈 24-hour hourly trend analysis"
echo "📋 Live metrics dashboard"
echo "🔔 Real-time review notifications"
echo "📱 Responsive design with animations"
echo "🔄 Auto-refresh and manual refresh"
echo "💬 WebSocket real-time updates"
echo ""

echo -e "${BLUE}🌐 Access URLs:${NC}"
echo "=================================="
echo "📊 Dashboard: http://localhost:5000"
echo "🔧 Spark UI: http://localhost:8080"
echo "📊 API Health: http://localhost:5000/api/health"
echo ""

echo -e "${YELLOW}📝 To view logs:${NC}"
echo "Backend: sudo docker compose logs -f backend"
echo "Kafka: sudo docker compose logs -f kafka"
echo "Spark: sudo docker compose logs -f spark-master"
echo ""

echo -e "${GREEN}✅ Enhanced real-time dashboard is ready!${NC}"
echo -e "${BLUE}🚀 Open http://localhost:5000 to see the real-time visualization${NC}"
