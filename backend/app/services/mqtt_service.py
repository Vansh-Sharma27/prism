"""
MQTT Service for receiving sensor data from ESP32 devices.
"""
import json
import os
import logging
from datetime import datetime
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

# MQTT Configuration
MQTT_BROKER = os.getenv('MQTT_BROKER_HOST', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_BROKER_PORT', 1883))
MQTT_TOPIC_PATTERN = 'prism/+/slot/+'  # prism/{lot_id}/slot/{slot_id}

# Sensor threshold (cm) - below this = occupied
OCCUPANCY_THRESHOLD = 15


class MQTTService:
    """Handles MQTT connection and message processing."""
    
    def __init__(self, app=None):
        self.app = app
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
    def _on_connect(self, client, userdata, flags, reason_code, properties):
        """Called when connected to MQTT broker."""
        logger.info(f"Connected to MQTT broker with result: {reason_code}")
        client.subscribe(MQTT_TOPIC_PATTERN)
        client.subscribe('prism/+/heartbeat')
        logger.info(f"Subscribed to: {MQTT_TOPIC_PATTERN}")
        
    def _on_message(self, client, userdata, msg):
        """Process incoming MQTT messages."""
        try:
            topic_parts = msg.topic.split('/')
            payload = json.loads(msg.payload.decode())
            
            if 'heartbeat' in msg.topic:
                self._handle_heartbeat(topic_parts[1], payload)
            else:
                # Format: prism/{lot_id}/slot/{slot_id}
                lot_id = topic_parts[1]
                slot_id = topic_parts[3]
                self._handle_slot_update(lot_id, slot_id, payload)
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        """Called when disconnected from MQTT broker."""
        logger.warning(f"Disconnected from MQTT broker: {reason_code}")
    
    def _handle_slot_update(self, lot_id, slot_id, payload):
        """Process slot status update from sensor."""
        distance = payload.get('distance_cm', 999)
        is_occupied = distance < OCCUPANCY_THRESHOLD
        
        logger.info(f"Slot {slot_id}: distance={distance}cm, occupied={is_occupied}")
        
        # Update database
        if self.app:
            with self.app.app_context():
                from app.models.parking import OccupancyLog, ParkingSlot, SensorReading
                from app import db
                
                slot = ParkingSlot.query.get(f"{lot_id}-{slot_id}")
                if slot:
                    old_status = slot.is_occupied
                    slot.is_occupied = is_occupied
                    
                    if old_status != is_occupied:
                        slot.last_status_change = datetime.utcnow()
                        from app.models.parking import ParkingEvent
                        event = ParkingEvent(
                            slot_id=slot.id,
                            event_type='entry' if is_occupied else 'exit',
                            sensor_distance_cm=distance
                        )
                        db.session.add(event)
                    
                    # Store reading for ML
                    reading = SensorReading(
                        slot_id=slot.id,
                        distance_cm=distance,
                        is_occupied=is_occupied
                    )
                    occupancy_log = OccupancyLog(
                        slot_id=slot.id,
                        status='occupied' if is_occupied else 'vacant',
                        distance_cm=distance
                    )
                    db.session.add(reading)
                    db.session.add(occupancy_log)
                    db.session.commit()
    
    def _handle_heartbeat(self, device_id, payload):
        """Process device heartbeat."""
        logger.debug(f"Heartbeat from {device_id}: {payload}")
    
    def start(self):
        """Connect to broker and start processing."""
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            logger.info(f"MQTT service started, connecting to {MQTT_BROKER}:{MQTT_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
    
    def stop(self):
        """Stop MQTT processing."""
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT service stopped")
