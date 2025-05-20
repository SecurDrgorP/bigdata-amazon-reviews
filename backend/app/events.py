import time
from threading import Thread
from flask_socketio import emit
from app.db import (
    get_sentiment_counts, 
    get_sentiment_by_time, 
    get_recent_reviews,
    get_product_sentiment_distribution
)
import datetime

# Store last update timestamp to check for new data
last_update_time = 0
thread = None

def background_thread(socketio):
    """Background thread that sends data updates to clients"""
    global last_update_time
    
    while True:
        # Check for new data every 2 seconds
        time.sleep(2)
        
        # Get latest reviews to check for updates
        reviews = get_recent_reviews(1)
        
        # If we have reviews and the timestamp is newer than our last update
        if reviews and 'ingestion_time' in reviews[0]:
            try:
                # Parse timestamp if it's a string
                if isinstance(reviews[0]['ingestion_time'], str):
                    current_time = datetime.datetime.strptime(
                        reviews[0]['ingestion_time'], "%Y-%m-%d %H:%M:%S"
                    ).timestamp()
                else:
                    # If it's already a datetime
                    current_time = reviews[0]['ingestion_time'].timestamp()
                    
                # If we have new data
                if current_time > last_update_time:
                    last_update_time = current_time
                    
                    # Emit data updates
                    socketio.emit('update_sentiment_counts', get_sentiment_counts())
                    socketio.emit('update_sentiment_trend', get_sentiment_by_time())
                    socketio.emit('update_recent_reviews', get_recent_reviews())
                    socketio.emit('update_product_sentiment', get_product_sentiment_distribution())
                    
                    print(f"Emitted updates at {time.strftime('%H:%M:%S')}")
            except Exception as e:
                print(f"Error in background thread: {e}")

def register_events(socketio):
    @socketio.on('connect')
    def handle_connect():
        global thread
        if thread is None or not thread.is_alive():
            thread = Thread(target=background_thread, args=(socketio,))
            thread.daemon = True
            thread.start()
        
        # Send initial data on connect
        emit('update_sentiment_counts', get_sentiment_counts())
        emit('update_sentiment_trend', get_sentiment_by_time())
        emit('update_recent_reviews', get_recent_reviews())
        emit('update_product_sentiment', get_product_sentiment_distribution())
        
        print("Client connected")
    
    @socketio.on('disconnect')
    def handle_disconnect():
        print("Client disconnected")