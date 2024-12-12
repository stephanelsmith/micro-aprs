# app.py

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import logging
import threading
import time
import queue
import json

from backend import Backend  # Adjust the import path as necessary

# Initialize Flask and Flask-SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a secure key in production
socketio = SocketIO(app, async_mode='eventlet')

# Configure logging
logging.basicConfig(
    filename='radio_transmission_app.log',
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)

# Initialize a queue to receive APRS messages from the backend
aprs_queue = queue.Queue()

# Initialize Backend
backend = Backend("config.json", socketio)
backend.set_aprs_queue(aprs_queue)

# Start the backend in a separate thread
def run_backend():
    try:
        backend.run()
    except Exception as e:
        logger.error(f"Backend encountered an error: {e}")
        socketio.emit('system_error', {'message': str(e)})

backend_thread = threading.Thread(target=run_backend, daemon=True)
backend_thread.start()

# Route for the main page
@app.route('/')
def index():
    return render_template('index.html')

# API endpoint to get current configuration
@app.route('/api/config', methods=['GET'])
def get_config():
    config = backend.config_manager.config
    return jsonify(config), 200

# API endpoint to update configuration
@app.route('/api/config', methods=['POST'])
def update_config():
    new_config = request.json
    try:
        # Validate and update the configuration
        mandatory_fields = ['callsign_source', 'callsign_dest', 'send_ip']
        for field in mandatory_fields:
            if field not in new_config or not new_config[field]:
                return jsonify({"status": "error", "message": f"Missing mandatory field: {field}"}), 400

        # Update configuration in the backend
        for key, value in new_config.items():
            backend.config_manager.set(key, value)

        # Save the updated config to file
        backend.config_manager.save_config()
        logger.info("Configuration updated successfully.")

        # Restart the backend to apply new configuration
        restart_backend()

        return jsonify({"status": "success", "message": "Configuration updated and backend restarted."}), 200
    except ValueError as ve:
        logger.error(f"Invalid input when saving configuration: {ve}")
        return jsonify({"status": "error", "message": f"Invalid input: {ve}"}), 400
    except Exception as e:
        logger.error(f"Error updating configuration: {e}")
        return jsonify({"status": "error", "message": f"Error updating configuration: {e}"}), 500

# API endpoint to restart reception
@app.route('/api/restart_reception', methods=['POST'])
def restart_reception():
    try:
        backend.start_reception()
        logger.info("Reception restarted successfully.")
        return jsonify({"status": "success", "message": "Reception restarted successfully."}), 200
    except Exception as e:
        logger.error(f"Error restarting reception: {e}")
        return jsonify({"status": "error", "message": f"Error restarting reception: {e}"}), 500

def restart_backend():
    try:
        backend.shutdown()
        logger.info("Backend shutdown initiated.")
        time.sleep(2)  # Wait for shutdown to complete

        # Reinitialize Backend
        backend = Backend("config.json", socketio)
        backend.set_aprs_queue(aprs_queue)

        # Restart Backend thread
        backend_thread = threading.Thread(target=run_backend, daemon=True)
        backend_thread.start()

        logger.info("Backend restarted successfully.")
        socketio.emit('backend_restarted', {'message': 'Backend restarted successfully.'})
    except Exception as e:
        logger.error(f"Error restarting backend: {e}")
        socketio.emit('system_error', {'message': f"Error restarting backend: {e}"})

# WebSocket event for client connection
@socketio.on('connect')
def handle_connect():
    logger.info("Client connected.")
    emit('system_status', {'status': 'connected'})
    # Optionally send initial data
    emit('system_status', {'status': 'running'})

# WebSocket event for client disconnection
@socketio.on('disconnect')
def handle_disconnect():
    logger.info("Client disconnected.")

# Function to handle APRS messages from the queue
def handle_aprs_messages():
    while True:
        try:
            message = aprs_queue.get(timeout=1)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            formatted_message = f"[{timestamp}] {message}"
            socketio.emit('aprs_message', {'message': formatted_message})
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Error handling APRS message: {e}")
            socketio.emit('system_error', {'message': f"Error handling APRS message: {e}"})

# Start APRS message handler in a background thread
aprs_thread = threading.Thread(target=handle_aprs_messages, daemon=True)
aprs_thread.start()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
