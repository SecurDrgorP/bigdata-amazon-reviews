from flask import Blueprint, render_template, jsonify
from app.db import (
    get_sentiment_counts, 
    get_sentiment_by_time, 
    get_recent_reviews,
    get_product_sentiment_distribution
)

# Create blueprint
main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@main.route('/api/sentiment_counts')
def sentiment_counts():
    """Get counts of positive, neutral, and negative reviews"""
    counts = get_sentiment_counts()
    return jsonify({
        "labels": ["Negative", "Neutral", "Positive"],
        "data": [counts["negative"], counts["neutral"], counts["positive"]]
    })

@main.route('/api/sentiment_by_time')
def sentiment_by_time():
    """Get sentiment trends over time"""
    return jsonify(get_sentiment_by_time())

@main.route('/api/recent_reviews')
def recent_reviews():
    """Get most recent reviews with predictions"""
    return jsonify(get_recent_reviews())

@main.route('/api/product_sentiment')
def product_sentiment():
    """Get sentiment distribution by product"""
    results = get_product_sentiment_distribution()
    return jsonify(results)