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


def _should_start_mqtt(debug_mode: bool) -> bool:
    """Avoid duplicate MQTT workers when Flask reloader is enabled."""
    if not debug_mode:
        return True
    return os.getenv("WERKZEUG_RUN_MAIN") == "true"


if __name__ == '__main__':
    debug_mode = os.getenv("PRISM_DEBUG", "true").lower() == "true"
    start_mqtt = _should_start_mqtt(debug_mode)

    if start_mqtt:
        mqtt_service.start()

    try:
        # Run Flask development server
        app.run(
            host='0.0.0.0',
            port=int(os.getenv('PORT', 5000)),
            debug=debug_mode,
            use_reloader=debug_mode,
        )
    finally:
        if start_mqtt:
            mqtt_service.stop()
