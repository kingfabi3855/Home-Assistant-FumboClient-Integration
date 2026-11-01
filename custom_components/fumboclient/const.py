"""Constants shared by the native FumboClient platforms."""

DOMAIN = "fumboclient"
DEFAULT_PORT = 25809
DEFAULT_INTERVAL = 5
CONF_TOKEN = "token"
CONF_INTERVAL = "scan_interval"
PLATFORMS = ["sensor", "binary_sensor", "switch", "button", "select", "text", "event"]
EVENT_TYPES = [
    "joined", "left", "afk_on", "afk_off", "damage", "death",
    "low_health", "low_hunger", "tool_low", "inventory_full", "fire",
]
ENTITY_PLATFORMS = {
    "connected": "binary_sensor", "afk": "binary_sensor",
    "idle_seconds": "sensor", "session_seconds": "sensor",
    "health": "sensor", "max_health": "sensor", "hunger": "sensor",
    "armor": "sensor", "air": "sensor", "alive": "binary_sensor",
    "on_fire": "binary_sensor", "low_health": "binary_sensor",
    "low_hunger": "binary_sensor", "xp_level": "sensor", "xp_progress": "sensor",
    "fps": "sensor", "ping": "sensor", "empty_slots": "sensor",
    "tool_durability": "sensor", "inventory_full": "binary_sensor",
    "dimension": "sensor", "x": "sensor", "y": "sensor", "z": "sensor", "server": "sensor",
    "cosmetics": "switch", "auto_eat": "switch", "auto_sell": "switch",
    "auto_fish": "switch", "auto_break": "switch", "auto_replant": "switch",
    "tool_warning": "switch", "mob_warning": "switch", "msg_notifications": "switch",
    "stop_helpers": "button", "disconnect": "button", "afk_mode": "select",
    "notify": "text", "events": "event",
}
