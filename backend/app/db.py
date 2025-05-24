# MongoDB connection
from pymongo import MongoClient
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MongoDB client with better error handling
try:
    client = MongoClient("mongodb://mongodb:27017", serverSelectionTimeoutMS=5000)
    # Test connection
    client.admin.command('ping')
    logger.info("✅ Connected to MongoDB successfully")
except Exception as e:
    logger.error(f"❌ Failed to connect to MongoDB: {e}")
    client = None

db = client['reviews'] if client else None
predictions_collection = db['predictions'] if db is not None else None

def ensure_connection():
    """Ensure MongoDB connection is alive"""
    global client, db, predictions_collection
    try:
        if client:
            client.admin.command('ping')
            return True
    except Exception as e:
        logger.warning(f"MongoDB connection lost, reconnecting... {e}")
        try:
            client = MongoClient("mongodb://mongodb:27017", serverSelectionTimeoutMS=5000)
            db = client['reviews']
            predictions_collection = db['predictions']
            logger.info("✅ Reconnected to MongoDB")
            return True
        except Exception as reconnect_error:
            logger.error(f"❌ Failed to reconnect: {reconnect_error}")
            return False
    return False

def get_sentiment_counts():
    """Get counts of positive, neutral, and negative reviews"""
    if not ensure_connection():
        return {"negative": 0, "neutral": 0, "positive": 0}
    
    try:
        pipeline = [
            {"$match": {"predicted_label": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": "$predicted_label", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        results = list(predictions_collection.aggregate(pipeline))

        counts = {"negative": 0, "neutral": 0, "positive": 0}
        for result in results:
            pred = result.get('_id', None)
            if pred is None:
                continue

            try:
                pred = int(pred)
                if pred == 0:
                    counts["negative"] = result['count']
                elif pred == 1:
                    counts["neutral"] = result['count']
                elif pred == 2:
                    counts["positive"] = result['count']
            except (ValueError, TypeError) as e:
                logger.warning(f"⚠️ Skipping invalid prediction label: {pred} → {e}")
                continue

        logger.info(f"📊 Sentiment counts: {counts}")
        return counts
    
    except Exception as e:
        logger.error(f"❌ Error getting sentiment counts: {e}")
        return {"negative": 0, "neutral": 0, "positive": 0}

def get_sentiment_by_time(days_back=7):
    """Get sentiment trends over time for the last N days"""
    if not ensure_connection():
        return {"days": [], "positive": [], "neutral": [], "negative": []}
    
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        pipeline = [
            {
                "$match": {
                    "predicted_label": {"$exists": True, "$ne": None},
                    "ingestion_time": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$project": {
                    "predicted_label": 1,
                    "day": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$ingestion_time",
                            "timezone": "UTC"
                        }
                    }
                }
            },
            {
                "$group": {
                    "_id": {"day": "$day", "predicted_label": "$predicted_label"},
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id.day": 1}}
        ]
        
        results = list(predictions_collection.aggregate(pipeline))
        
        # Generate all days in range
        all_days = []
        current_date = start_date
        while current_date <= end_date:
            all_days.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)
        
        data = {
            "days": all_days,
            "positive": [],
            "neutral": [],
            "negative": []
        }
        
        # Fill data for each day
        for day in all_days:
            pos_count = next(
                (r['count'] for r in results
                if r.get('_id', {}).get('day') == day and r.get('_id', {}).get('predicted_label') == 2),
                0
            )
            neu_count = next(
                (r['count'] for r in results
                if r.get('_id', {}).get('day') == day and r.get('_id', {}).get('predicted_label') == 1),
                0
            )
            neg_count = next(
                (r['count'] for r in results
                if r.get('_id', {}).get('day') == day and r.get('_id', {}).get('predicted_label') == 0),
                0
            )

            data["positive"].append(pos_count)
            data["neutral"].append(neu_count)
            data["negative"].append(neg_count)
        
        logger.info(f"📈 Trend data for {len(all_days)} days")
        return data
    
    except Exception as e:
        logger.error(f"❌ Error getting sentiment by time: {e}")
        return {"days": [], "positive": [], "neutral": [], "negative": []}

def get_recent_reviews(limit=10):
    """Get most recent reviews with predictions"""
    if not ensure_connection():
        return []
    
    try:
        results = list(predictions_collection.find(
            {"predicted_label": {"$exists": True, "$ne": None}},
            {
                "_id": 0,
                "lemmatized_text": 1, 
                "predicted_label": 1,
                "reviewerID": 1,
                "ingestion_time": 1
            }
        ).sort("ingestion_time", -1).limit(limit))
        
        # Format dates and add sentiment labels
        for r in results:
            if "ingestion_time" in r and r["ingestion_time"]:
                if isinstance(r["ingestion_time"], datetime):
                    r['ingestion_time'] = r['ingestion_time'].strftime("%Y-%m-%d %H:%M:%S")
                else:
                    r['ingestion_time'] = str(r["ingestion_time"])
            else:
                r['ingestion_time'] = "Unknown"
            
            pred = r.get('predicted_label')
            if pred == 0:
                r['sentiment'] = "Negative"
            elif pred == 1:
                r['sentiment'] = "Neutral"
            elif pred == 2:
                r['sentiment'] = "Positive"
            else:
                r['sentiment'] = "Unknown"
            
            # Ensure text is not too long
            if r.get('lemmatized_text'):
                if len(r['lemmatized_text']) > 200:
                    r['lemmatized_text'] = r['lemmatized_text'][:200] + "..."
        
        logger.info(f"📝 Retrieved {len(results)} recent reviews")
        return results
    
    except Exception as e:
        logger.error(f"❌ Error getting recent reviews: {e}")
        return []

def get_product_sentiment_distribution(limit=10):
    """Get sentiment distribution by product (top N products)"""
    if not ensure_connection():
        return []
    
    try:
        pipeline = [
            {"$match": {"predicted_label": {"$exists": True, "$ne": None}}},
            {"$group": {
                "_id": "$reviewerID",  # Use reviewerID since asin might not be available
                "positive": {"$sum": {"$cond": [{"$eq": ["$predicted_label", 2]}, 1, 0]}},
                "neutral": {"$sum": {"$cond": [{"$eq": ["$predicted_label", 1]}, 1, 0]}},
                "negative": {"$sum": {"$cond": [{"$eq": ["$predicted_label", 0]}, 1, 0]}},
                "total": {"$sum": 1}
            }},
            {"$match": {"_id": {"$ne": None}, "total": {"$gte": 2}}},  # At least 2 reviews
            {"$sort": {"total": -1}},
            {"$limit": limit}
        ]
        
        results = list(predictions_collection.aggregate(pipeline))
        
        # Add percentage calculations
        for result in results:
            total = result['total']
            if total > 0:
                result['positive_pct'] = round((result['positive'] / total) * 100, 1)
                result['negative_pct'] = round((result['negative'] / total) * 100, 1)
                result['neutral_pct'] = round((result['neutral'] / total) * 100, 1)
            else:
                result['positive_pct'] = result['negative_pct'] = result['neutral_pct'] = 0
        
        logger.info(f"🏪 Retrieved {len(results)} product sentiment distributions")
        return results
    
    except Exception as e:
        logger.error(f"❌ Error getting product sentiment distribution: {e}")
        return []

def get_specific_product_sentiment(asin="B00004Y2UT"):
    """Get sentiment analysis for a specific product by ASIN"""
    if not ensure_connection():
        return {"asin": asin, "positive": 0, "neutral": 0, "negative": 0, "total": 0}
    
    try:
        pipeline = [
            {"$match": {"asin": asin, "predicted_label": {"$exists": True, "$ne": None}}},
            {"$group": {
                "_id": None,
                "positive": {"$sum": {"$cond": [{"$eq": ["$predicted_label", 2]}, 1, 0]}},
                "neutral": {"$sum": {"$cond": [{"$eq": ["$predicted_label", 1]}, 1, 0]}},
                "negative": {"$sum": {"$cond": [{"$eq": ["$predicted_label", 0]}, 1, 0]}},
                "total": {"$sum": 1}
            }}
        ]
        
        results = list(predictions_collection.aggregate(pipeline))
        
        if results:
            result = results[0]
            result['asin'] = asin
            total = result['total']
            if total > 0:
                result['positive_pct'] = round((result['positive'] / total) * 100, 1)
                result['negative_pct'] = round((result['negative'] / total) * 100, 1)
                result['neutral_pct'] = round((result['neutral'] / total) * 100, 1)
            return result
        else:
            return {"asin": asin, "positive": 0, "neutral": 0, "negative": 0, "total": 0}
    
    except Exception as e:
        logger.error(f"❌ Error getting specific product sentiment: {e}")
        return {"asin": asin, "positive": 0, "neutral": 0, "negative": 0, "total": 0}

def get_latest_prediction_time():
    """Get the timestamp of the most recent prediction"""
    if not ensure_connection():
        return None
    
    try:
        result = predictions_collection.find_one(
            {"ingestion_time": {"$exists": True}},
            {"ingestion_time": 1},
            sort=[("ingestion_time", -1)]
        )
        
        if result and 'ingestion_time' in result:
            return result['ingestion_time']
        return None
    
    except Exception as e:
        logger.error(f"❌ Error getting latest prediction time: {e}")
        return None

def get_database_stats():
    """Get overall database statistics"""
    if not ensure_connection():
        return {"total_predictions": 0, "connection_status": "disconnected"}
    
    try:
        total_count = predictions_collection.count_documents({})
        predictions_with_labels = predictions_collection.count_documents(
            {"predicted_label": {"$exists": True, "$ne": None}}
        )
        
        latest_time = get_latest_prediction_time()
        
        return {
            "total_predictions": total_count,
            "valid_predictions": predictions_with_labels,
            "latest_prediction": latest_time.strftime("%Y-%m-%d %H:%M:%S") if latest_time else "None",
            "connection_status": "connected"
        }
    
    except Exception as e:
        logger.error(f"❌ Error getting database stats: {e}")
        return {"total_predictions": 0, "connection_status": "error"}