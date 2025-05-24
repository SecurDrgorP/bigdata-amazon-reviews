from flask import Blueprint, render_template, jsonify, request
from app.db import (
    get_sentiment_counts, 
    get_sentiment_by_time, 
    get_recent_reviews,
    get_product_sentiment_distribution,
    get_specific_product_sentiment,
    get_database_stats
)
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Main dashboard page"""
    logger.info("📱 Dashboard page accessed")
    return render_template('index.html')

@main.route('/api/sentiment_counts')
def sentiment_counts():
    """Get counts of positive, neutral, and negative reviews"""
    try:
        counts = get_sentiment_counts()
        logger.info(f"📊 Sentiment counts API called: {counts}")
        
        return jsonify({
            "labels": ["Negative", "Neutral", "Positive"],
            "data": [counts["negative"], counts["neutral"], counts["positive"]],
            "total": sum(counts.values()),
            "status": "success"
        })
    except Exception as e:
        logger.error(f"❌ Error in sentiment_counts API: {e}")
        return jsonify({
            "labels": ["Negative", "Neutral", "Positive"],
            "data": [0, 0, 0],
            "total": 0,
            "status": "error",
            "message": str(e)
        }), 500

@main.route('/api/sentiment_by_time')
def sentiment_by_time():
    """Get sentiment trends over time"""
    try:
        days_back = request.args.get('days', 7, type=int)
        data = get_sentiment_by_time(days_back)
        
        logger.info(f"📈 Sentiment by time API called for {days_back} days")
        
        return jsonify({
            **data,
            "status": "success",
            "days_requested": days_back
        })
    except Exception as e:
        logger.error(f"❌ Error in sentiment_by_time API: {e}")
        return jsonify({
            "days": [],
            "positive": [],
            "neutral": [],
            "negative": [],
            "status": "error",
            "message": str(e)
        }), 500

@main.route('/api/recent_reviews')
def recent_reviews():
    """Get most recent reviews with predictions"""
    try:
        limit = request.args.get('limit', 10, type=int)
        reviews = get_recent_reviews(limit)
        
        logger.info(f"📝 Recent reviews API called, returned {len(reviews)} reviews")
        
        return jsonify({
            "reviews": reviews,
            "count": len(reviews),
            "status": "success"
        })
    except Exception as e:
        logger.error(f"❌ Error in recent_reviews API: {e}")
        return jsonify({
            "reviews": [],
            "count": 0,
            "status": "error",
            "message": str(e)
        }), 500

@main.route('/api/product_sentiment')
def product_sentiment():
    """Get sentiment distribution by product"""
    try:
        limit = request.args.get('limit', 10, type=int)
        results = get_product_sentiment_distribution(limit)
        
        logger.info(f"🏪 Product sentiment API called, returned {len(results)} products")
        
        return jsonify({
            "products": results,
            "count": len(results),
            "status": "success"
        })
    except Exception as e:
        logger.error(f"❌ Error in product_sentiment API: {e}")
        return jsonify({
            "products": [],
            "count": 0,
            "status": "error",
            "message": str(e)
        }), 500

@main.route('/api/specific_product/<asin>')
def specific_product_sentiment(asin):
    """Get sentiment analysis for a specific product"""
    try:
        result = get_specific_product_sentiment(asin)
        
        logger.info(f"🔍 Specific product API called for ASIN: {asin}")
        
        return jsonify({
            "product": result,
            "status": "success"
        })
    except Exception as e:
        logger.error(f"❌ Error in specific_product_sentiment API: {e}")
        return jsonify({
            "product": {"asin": asin, "positive": 0, "neutral": 0, "negative": 0, "total": 0},
            "status": "error",
            "message": str(e)
        }), 500

@main.route('/api/stats')
def database_stats():
    """Get overall database statistics"""
    try:
        stats = get_database_stats()
        
        logger.info(f"📊 Database stats API called: {stats}")
        
        return jsonify({
            "stats": stats,
            "status": "success"
        })
    except Exception as e:
        logger.error(f"❌ Error in database_stats API: {e}")
        return jsonify({
            "stats": {"total_predictions": 0, "connection_status": "error"},
            "status": "error",
            "message": str(e)
        }), 500

@main.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        stats = get_database_stats()
        
        return jsonify({
            "status": "healthy",
            "database": stats.get("connection_status", "unknown"),
            "timestamp": "2024-05-23 21:00:00"  # Current time would be dynamic
        })
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

# Error handlers
@main.errorhandler(404)
def not_found(error):
    return jsonify({
        "status": "error",
        "message": "Endpoint not found",
        "code": 404
    }), 404

@main.errorhandler(500)
def internal_error(error):
    logger.error(f"❌ Internal server error: {error}")
    return jsonify({
        "status": "error",
        "message": "Internal server error",
        "code": 500
    }), 500