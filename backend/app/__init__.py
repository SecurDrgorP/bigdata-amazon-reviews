from flask import Flask
from flask_socketio import SocketIO

# Create SocketIO instance
socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    
    # Initialize SocketIO with the app
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Register blueprints
    from app.routes import main
    app.register_blueprint(main)
    
    # Import and register socket events
    from app.events import register_events
    register_events(socketio)
    
    return app