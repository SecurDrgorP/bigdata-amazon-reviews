# MongoDB connection
from pymongo import MongoClient
from datetime import datetime

# Create MongoDB client
client = MongoClient('mongodb://localhost:27017/')
db = client['amazon_reviews']
predictions_collection = db['predictions']

# Helper functions for data retrieval
def get_sentiment_counts():
    """Get counts of positive, neutral, and negative reviews"""
    pipeline = [
        {"$group": {"_id": "$prediction", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    results = list(predictions_collection.aggregate(pipeline))
    
    counts = {"negative": 0, "neutral": 0, "positive": 0}
    for result in results:
        pred = int(result['_id'])
        if pred == 0:
            counts["negative"] = result['count']
        elif pred == 1:
            counts["neutral"] = result['count']
        elif pred == 2:
            counts["positive"] = result['count']
    
    return counts

def get_sentiment_by_time():
    """Get sentiment trends over time"""
    pipeline = [
        {
            "$project": {
                "prediction": 1,
                "day": {"$dateToString": {"format": "%Y-%m-%d", "date": "$ingestion_time"}}
            }
        },
        {
            "$group": {
                "_id": {"day": "$day", "prediction": "$prediction"},
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id.day": 1}}
    ]
    
    results = list(predictions_collection.aggregate(pipeline))
    
    days = sorted(set(r['_id']['day'] for r in results))
    data = {
        "days": days,
        "positive": [],
        "neutral": [],
        "negative": []
    }
    
    for day in days:
        pos_count = next((r['count'] for r in results if r['_id']['day'] == day and r['_id']['prediction'] == 2), 0)
        neu_count = next((r['count'] for r in results if r['_id']['day'] == day and r['_id']['prediction'] == 1), 0)
        neg_count = next((r['count'] for r in results if r['_id']['day'] == day and r['_id']['prediction'] == 0), 0)
        data["positive"].append(pos_count)
        data["neutral"].append(neu_count)
        data["negative"].append(neg_count)
    
    return data

def get_recent_reviews(limit=10):
    """Get most recent reviews with predictions"""
    results = list(predictions_collection.find({}, {
        "_id": 0,
        "text": 1, 
        "prediction": 1, 
        "asin": 1,
        "reviewerID": 1,
        "ingestion_time": 1
    }).sort("ingestion_time", -1).limit(limit))
    
    # Format dates and add sentiment label
    for r in results:
        if "ingestion_time" in r:
            r['ingestion_time'] = r['ingestion_time'].strftime("%Y-%m-%d %H:%M:%S")
        
        pred = r.get('prediction')
        if pred == 0:
            r['sentiment'] = "Negative"
        elif pred == 1:
            r['sentiment'] = "Neutral"
        elif pred == 2:
            r['sentiment'] = "Positive"
    
    return results

def get_product_sentiment_distribution():
    """Get sentiment distribution by product"""
    pipeline = [
        {"$group": {
            "_id": "$asin",
            "positive": {"$sum": {"$cond": [{"$eq": ["$prediction", 2]}, 1, 0]}},
            "neutral": {"$sum": {"$cond": [{"$eq": ["$prediction", 1]}, 1, 0]}},
            "negative": {"$sum": {"$cond": [{"$eq": ["$prediction", 0]}, 1, 0]}}
        }},
        {"$match": {"_id": {"$ne": None}}},
        {"$sort": {"positive": -1}},
        {"$limit": 10}
    ]
    
    results = list(predictions_collection.aggregate(pipeline))
    return results