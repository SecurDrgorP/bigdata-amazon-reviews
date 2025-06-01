# Amazon Reviews Sentiment Analysis - Big Data Project

## Overview

This project implements an end-to-end big data pipeline for analyzing Amazon product reviews. It uses a combination of data preprocessing, machine learning for sentiment analysis, and real-time streaming technologies to process reviews and visualize insights through an interactive dashboard.

## Architecture

The system architecture consists of the following components:

- **Data Preprocessing**: Cleans and transforms raw Amazon review data
- **Machine Learning**: Trains and deploys a sentiment analysis model
- **Streaming Pipeline**: Processes reviews in real-time using Kafka and Spark
- **Storage Layer**: Stores processed data and results in MongoDB
- **Web Dashboard**: Visualizes insights through a Flask web application

## Technologies

- **Apache Kafka**: Message streaming platform
- **Apache Spark**: Distributed data processing
- **MongoDB**: NoSQL database for storing reviews and results
- **Flask**: Web framework for the dashboard
- **Docker**: Containerization for easy deployment
- **Python**: Primary programming language
- **SpaCy**: NLP library for text processing

## Installation & Setup

### Prerequisites
- Docker and Docker Compose
- Python 3.7+

### Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/bigdata-amazon-reviews.git
   cd bigdata-amazon-reviews
   ```

2. Create and activate a virtual environment:
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate virtual environment
   # On Linux/macOS
   source venv/bin/activate
   # On Windows
   venv\Scripts\activate
   ```

3. Create and configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with appropriate values
   ```

4. Install Python dependencies and the spaCy language model:
   ```bash
   pip install -r requirements.txt

   python -m spacy download en_core_web_sm
   ```

5. Start Docker containers:
   ```bash
   docker-compose up -d
   ```

## Usage

1. Run the Spark consumer to process the data:
   ```bash
   ./run_consumer.sh
   ```

2. Start the Kafka producer to ingest review data:
   ```bash
   ./run_producer.sh
   ```

3. Access the dashboard at http://localhost:5000

## Data Pipeline

1. **Data Preparation**: Raw Amazon review data is cleaned and preprocessed
2. **Producer**: Kafka producer streams review data into the pipeline
3. **Consumer**: Spark processes the streams and performs sentiment analysis
4. **Storage**: Results are stored in MongoDB
5. **Visualization**: Flask application renders insights through a web dashboard

## Dataset

Source: [Amazon Review Sentiment Analysis Dataset on Kaggle](https://www.kaggle.com/code/soniaahlawat/sentiment-analysis-amazon-review/input)

| Field Name       | Description                                       |
|------------------|-------------------------------------------------|
| `reviewerID`     | Reviewer’s unique ID                             |
| `asin`           | Product ID                                       |
| `reviewerName`   | Reviewer’s name                                  |
| `helpful`        | Helpfulness rating, e.g. `[2, 3]` means 2 out of 3 found the review helpful |
| `reviewText`     | Text content of the review                       |
| `overall`        | Product rating (out of 5)                        |
| `summary`        | Summary of the review                            |
| `unixReviewTime` | Review time (Unix timestamp)                     |
| `reviewTime`     | Review time (human-readable)                     |

## Model Training

The sentiment analysis model can be retrained using:
```bash
cd model
python evaluate_model.py
```

Alternatively, examine the training process:
```bash
jupyter notebook model/train_model.ipynb
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Acknowledgments

- Amazon review dataset providers
- The open source community for the amazing tools used in this project
