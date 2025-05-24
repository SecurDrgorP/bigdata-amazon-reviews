import time
from threading import Thread, Event
from flask_socketio import emit
from app.db import (
    get_sentiment_counts, 
    get_sentiment_by_time, 
    get_recent_reviews,
    get_product_sentiment_distribution,
    get_specific_product_sentiment,
    get_latest_prediction_time,
    get_database_stats
)
import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for thread management
last_update_time = 0
thread = None
stop_event = Event()
connected_clients = 0

def background_thread(socketio):
    """Enhanced background thread that sends data updates to clients"""
    global last_update_time
    
    logger.info("🚀 Starting background thread for real-time updates")
    
    while not stop_event.is_set():
        try:
            # Check for new data every 3 seconds
            time.sleep(3)
            
            # Skip if no clients connected
            if connected_clients == 0:
                continue
            
            # Get latest prediction timestamp
            latest_time = get_latest_prediction_time()
            
            if latest_time:
                # Convert to timestamp for comparison
                if isinstance(latest_time, datetime.datetime):
                    current_timestamp = latest_time.timestamp()
                else:
                    try:
                        current_timestamp = datetime.datetime.strptime(
                            str(latest_time), "%Y-%m-%d %H:%M:%S"
                        ).timestamp()
                    except:
                        current_timestamp = time.time()
                
                # Check if we have new data
                if current_timestamp > last_update_time:
                    last_update_time = current_timestamp
                    
                    logger.info(f"📡 Broadcasting updates to {connected_clients} clients")
                    
                    # Emit all data updates
                    socketio.emit('update_sentiment_counts', get_sentiment_counts())
                    socketio.emit('update_sentiment_trend', get_sentiment_by_time())
                    socketio.emit('update_recent_reviews', get_recent_reviews(15))
                    socketio.emit('update_product_sentiment', get_product_sentiment_distribution())
                    socketio.emit('update_specific_product', get_specific_product_sentiment())
                    socketio.emit('update_stats', get_database_stats())
                    
                    # Emit timestamp for debugging
                    socketio.emit('last_update', {
                        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'data_timestamp': latest_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(latest_time, datetime.datetime) else str(latest_time)
                    })
                    
                    logger.info(f"✅ Updates sent at {time.strftime('%H:%M:%S')}")
            else:
                # Send heartbeat even if no new data
                if connected_clients > 0:
                    socketio.emit('heartbeat', {
                        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'status': 'waiting_for_data'
                    })
        
        except Exception as e:
            logger.error(f"❌ Error in background thread: {e}")
            # Continue running even if there's an error
            time.sleep(5)
    
    logger.info("🛑 Background thread stopped")

def register_events(socketio):
    global connected_clients, thread
    
    @socketio.on('connect')
    def handle_connect():
        global connected_clients, thread
        
        connected_clients += 1
        logger.info(f"👤 Client connected. Total clients: {connected_clients}")
        
        # Start background thread if not running
        if thread is None or not thread.is_alive():
            stop_event.clear()
            thread = Thread(target=background_thread, args=(socketio,))
            thread.daemon = True
            thread.start()
            logger.info("🔄 Background thread started")
        
        # Send initial data immediately
        try:
            logger.info("📤 Sending initial data to new client")
            
            emit('update_sentiment_counts', get_sentiment_counts())
            emit('update_sentiment_trend', get_sentiment_by_time())
            emit('update_recent_reviews', get_recent_reviews(15))
            emit('update_product_sentiment', get_product_sentiment_distribution())
            emit('update_specific_product', get_specific_product_sentiment())
            emit('update_stats', get_database_stats())
            
            # Send connection confirmation
            emit('connection_status', {
                'status': 'connected',
                'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'message': 'Real-time updates active'
            })
            
            logger.info("✅ Initial data sent to client")
            
        except Exception as e:
            logger.error(f"❌ Error sending initial data: {e}")
            emit('connection_status', {
                'status': 'error',
                'message': f'Error loading data: {str(e)}'
            })
    
    @socketio.on('disconnect')
    def handle_disconnect():
        global connected_clients
        
        connected_clients = max(0, connected_clients - 1)
        logger.info(f"👋 Client disconnected. Total clients: {connected_clients}")
        
        # Stop background thread if no clients
        if connected_clients == 0:
            stop_event.set()
            logger.info("🛑 No clients connected, background thread will stop")
    
    @socketio.on('request_update')
    def handle_manual_update():
        """Handle manual update requests from clients"""
        logger.info("🔄 Manual update requested by client")
        
        try:
            emit('update_sentiment_counts', get_sentiment_counts())
            emit('update_sentiment_trend', get_sentiment_by_time())
            emit('update_recent_reviews', get_recent_reviews(15))
            emit('update_product_sentiment', get_product_sentiment_distribution())
            emit('update_specific_product', get_specific_product_sentiment())
            emit('update_stats', get_database_stats())
            
            emit('manual_update_response', {
                'status': 'success',
                'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
        except Exception as e:
            logger.error(f"❌ Error in manual update: {e}")
            emit('manual_update_response', {
                'status': 'error',
                'message': str(e)
            })
    
    @socketio.on('get_specific_product')
    def handle_specific_product_request(data):
        """Handle requests for specific product sentiment"""
        asin = data.get('asin', 'B00004Y2UT')
        logger.info(f"🔍 Specific product request for ASIN: {asin}")
        
        try:
            result = get_specific_product_sentiment(asin)
            emit('specific_product_response', {
                'asin': asin,
                'data': result,
                'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        except Exception as e:
            logger.error(f"❌ Error getting specific product data: {e}")
            emit('specific_product_response', {
                'asin': asin,
                'error': str(e)
            })
    
    @socketio.on('ping')
    def handle_ping():
        """Handle ping requests from clients"""
        emit('pong', {
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'server_status': 'healthy'
        })
    
    logger.info("🔗 Socket.IO events registered successfully")