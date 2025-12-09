import json
from typing import Any, Dict, Callable, Optional
from paho.mqtt import client as mqtt
import logging
log = logging.getLogger(__name__)

class Mqtt:
    def __init__(self, cfg):
        self.cfg = cfg
        self.cli = mqtt.Client(client_id=cfg.client_id, clean_session=True)
        if cfg.username:
            self.cli.username_pw_set(cfg.username, cfg.password or "")
        self.cli.connect_async(cfg.host, cfg.port, keepalive=30)
        self.cli.loop_start()

    def pub(self, topic: str, payload: Dict[str, Any], retain: bool = False):
        try:
            # Ensure payload is JSON-serializable
            # Convert any non-serializable values to strings
            serializable_payload = self._make_json_serializable(payload)
            p = json.dumps(serializable_payload, separators=(",", ":"))
            log.debug("MQTT PUB %s %s", topic, p)
            self.cli.publish(topic, p, qos=0, retain=retain)
        except Exception as e:
            log.error(f"Failed to publish MQTT message to {topic}: {e}", exc_info=True)
            raise
    
    def _make_json_serializable(self, obj: Any, visited: Optional[set] = None) -> Any:
        """
        Recursively convert object to JSON-serializable format.
        Handles circular references and non-serializable types.
        
        Args:
            obj: Object to make JSON-serializable
            visited: Set of object IDs already visited (to detect circular references)
        """
        if visited is None:
            visited = set()
        
        # Handle circular references by tracking visited objects
        # Use object ID for mutable types (dict, list), value for immutable types
        if isinstance(obj, (dict, list)):
            obj_id = id(obj)
            if obj_id in visited:
                return "<circular reference>"
            visited.add(obj_id)
        
        try:
            if isinstance(obj, dict):
                result = {}
                for k, v in obj.items():
                    # Ensure key is string
                    key = str(k) if not isinstance(k, str) else k
                    result[key] = self._make_json_serializable(v, visited.copy())
                return result
            elif isinstance(obj, (list, tuple)):
                return [self._make_json_serializable(item, visited.copy()) for item in obj]
            elif isinstance(obj, (str, int, float, bool, type(None))):
                return obj
            else:
                # Try to serialize, fallback to string representation
                try:
                    json.dumps(obj)
                    return obj
                except (TypeError, ValueError):
                    # Non-serializable type - convert to string
                    return str(obj)
        finally:
            # Clean up visited set for mutable types
            if isinstance(obj, (dict, list)):
                visited.discard(id(obj))

    def sub(self, topic: str, handler: Callable[[str, Dict[str, Any]], None]):
        def on_message(_cli, _ud, msg):
            try:
                data = json.loads(msg.payload.decode())
            except Exception:
                handler(msg.topic, msg.payload.decode())
                return
            handler(msg.topic, data)
        self.cli.subscribe(topic, qos=0)
        self.cli.message_callback_add(topic, on_message)
