from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    # Use socketio.run instead of app.run
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)