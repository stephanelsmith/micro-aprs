# webui.py

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import threading
import logging
import sys
import json

from backend.backend import Backend  # Ensure this import path is correct

# Configure logging
logging.basicConfig(
    filename='radio_transmission_app.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)



# Initialize Flask and SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Replace with your secret key
socketio = SocketIO(app, cors_allowed_origins="*")  # Adjust CORS as necessary

# Initialize Backend
backend = Backend(config_file='config.json', socketio=socketio)

@socketio.on('connect')
def handle_connect():
    print("Client connected")
    logger.info("A client has connected to the server.")
    # Optionally, emit initial system status or data to the client
    socketio.emit('system_status', {'status': 'running'})
    # You can also send other statuses if needed
    socketio.emit('reception_status', {'status': 'idle'})

@socketio.on('aprs_message')
def handle_aprs():
    print("allo2")



# Define routes
@app.route('/')
def index():
    return render_template('index.html')

# API endpoint to get current configuration
@app.route('/api/config', methods=['GET'])
def get_config():
    try:
        config = backend.config_manager.config
        return jsonify({'status': 'success', 'config': config})
    except Exception as e:
        logger.exception("Failed to get configuration: %s", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

# API endpoint to update configuration
@app.route('/api/config', methods=['POST'])
def update_config():
    try:
        new_config = request.get_json()
        if not new_config:
            return jsonify({'status': 'error', 'message': 'No configuration data provided.'}), 400

        # Apply new configuration
        backend.apply_new_config(new_config)

        # Emit configuration update event
        socketio.emit('config_updated', {'status': 'success'})

        logger.info("Configuration updated successfully.")
        return jsonify({'status': 'success', 'message': 'Configuration updated successfully.'})
    except Exception as e:
        logger.exception("Failed to update configuration: %s", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

# API endpoint to restart reception
@app.route('/api/restart_reception', methods=['POST'])
def restart_reception():
    try:
        backend.message_processor.restart_receiver()
        logger.info("Reception restarted successfully.")
        return jsonify({'status': 'success', 'message': 'Reception restarted successfully.'})
    except Exception as e:
        logger.exception("Failed to restart reception: %s", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Function to run the backend in a separate thread
def run_backend():
    backend.run()

# Start the backend in a background thread before starting the SocketIO server
backend_thread = threading.Thread(target=run_backend, daemon=True)
backend_thread.start()
logger.info("Backend thread started.")

# Run the Flask app with SocketIO
if __name__ == '__main__':
    try:
        socketio.run(app, host='0.0.0.0', port=5000)
    except Exception as e:
        logger.exception("Failed to start the Flask-SocketIO server: %s", e)
        sys.exit(1)
