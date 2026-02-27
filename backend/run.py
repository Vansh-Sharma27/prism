"""
Run the PRISM Flask application.
"""
import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.services.mqtt_service import MQTTService

app = create_app()
mqtt_service = MQTTService(app)

if __name__ == '__main__':
    # Start MQTT subscriber in background
    mqtt_service.start()
    
    try:
        # Run Flask development server
        app.run(
            host='0.0.0.0',
            port=int(os.getenv('PORT', 5000)),
            debug=True
        )
    finally:
        mqtt_service.stop()
