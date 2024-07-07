import bluepy.btle as btle
import logging
import json
import requests
import time
import os
from logging_loki import LokiHandler

# Load configuration
config = {}
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    print("Config file not found, proceeding with default values or environment variables.")

# Function to get config value with environment variable override and identify source
def get_config_value(key, default_value):
    value = os.getenv(key.upper(), config.get(key, default_value))
    source = "default"
    if os.getenv(key.upper()) is not None:
        source = "environment variable"
    elif key in config:
        source = "config file"
    return value, source

# Configurable variables and their sources
enable_loki_logging, enable_loki_logging_source = get_config_value('enable_loki_logging', True)
loki_url, loki_url_source = get_config_value('loki_url', 'http://localhost:3100/loki/api/v1/push')
log_other_devices, log_other_devices_source = get_config_value('log_other_devices', True)
kofferid, kofferid_source = get_config_value('kofferid', 'unknown')
lat, lat_source = get_config_value('lat', 'unknown')
lon, lon_source = get_config_value('lon', 'unknown')
alert, alert_source = get_config_value('alert', 'unknown')
cooldown_period, cooldown_period_source = get_config_value('cooldown_period', 60)

# Convert enable_loki_logging and log_other_devices to boolean
enable_loki_logging = enable_loki_logging in ['true', 'True', True]
log_other_devices = log_other_devices in ['true', 'True', True]

# Setup logging to console
logger = logging.getLogger("f0_scanner")
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Log configuration
logger.info("Configuration:")
logger.info(f"ENABLE_LOKI_LOGGING: {enable_loki_logging} (source: {enable_loki_logging_source})")
logger.info(f"LOKI_URL: {loki_url} (source: {loki_url_source})")
logger.info(f"LOG_OTHER_DEVICES: {log_other_devices} (source: {log_other_devices_source})")
logger.info(f"KOFFERID: {kofferid} (source: {kofferid_source})")
logger.info(f"LAT: {lat} (source: {lat_source})")
logger.info(f"LON: {lon} (source: {lon_source})")
logger.info(f"ALERT: {alert} (source: {alert_source})")
logger.info(f"COOLDOWN_PERIOD: {cooldown_period} (source: {cooldown_period_source})")

# Function to check if Loki is reachable
def check_loki_reachable(url):
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 405  # 405 Method Not Allowed is expected for GET on Loki push endpoint
    except requests.RequestException as e:
        logger.error(f"Failed to reach Loki: {e}")
        return False

# Custom filter to log only Flipper Zero devices to Loki
class FlipperZeroFilter(logging.Filter):
    def filter(self, record):
        if 'Flipper Zero' in record.getMessage():
            return True
        return False

# Function to setup Loki logging with retry mechanism
def setup_loki_logging():
    while enable_loki_logging:
        if check_loki_reachable(loki_url):
            loki_handler = LokiHandler(
                url=loki_url,
                tags={"application": "f0_scanner"},
                version="1",
            )
            loki_handler.addFilter(FlipperZeroFilter())  # Add filter to Loki handler
            loki_handler.setLevel(logging.WARNING)  # Set the log level for Loki handler to WARNING
            logger.addHandler(loki_handler)
            logger.info("Loki is reachable. Enabled Loki logging.")
            break
        else:
            logger.error("Loki is not reachable. Retrying in 10 seconds...")
            time.sleep(10)

if enable_loki_logging:
    setup_loki_logging()

# Initialize a cache for detected devices with a cooldown period
detected_devices = {}

class ScanDelegate(btle.DefaultDelegate):
    def __init__(self):
        btle.DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        device_name = "NOT FOUND"
        device_manufacturer = "NOT FOUND"
        device_uuid = "NOT FOUND"
        device_type = "NOT FOUND"
        for (adtype, desc, value) in dev.getScanData():
            if desc == "Complete Local Name":
                device_name = value
            elif desc == "Manufacturer":
                device_manufacturer = value
            elif value == "00003082-0000-1000-8000-00805f9b34fb":
                device_uuid = value
                device_type = "White"
            elif value == "00003081-0000-1000-8000-00805f9b34fb":
                device_uuid = value
                device_type = "Black"
            elif value == "00003083-0000-1000-8000-00805f9b34fb":
                device_uuid = value
                device_type = "Transparent"
        current_time = time.time()
        if dev.addr not in detected_devices or (current_time - detected_devices[dev.addr]) > cooldown_period:
            rssi = dev.rssi
            if device_uuid != "NOT FOUND":
                message = {
                    "timestamp": current_time,
                    "type": "Flipper Zero",
                    "address": dev.addr,
                    "name": device_name,
                    "manufacturer": device_manufacturer,
                    "uuid": device_uuid,
                    "device_type": device_type,
                    "rssi": rssi,
                    "kofferid": kofferid,
                    "lat": lat,
                    "lon": lon,
                    "alert": alert
                }
                logger.warning(json.dumps(message))  # Log Flipper Zero detections as WARNING
            elif log_other_devices:
                message = {
                    "timestamp": current_time,
                    "type": "Other Device",
                    "address": dev.addr,
                    "name": device_name,
                    "manufacturer": device_manufacturer,
                    "rssi": rssi
                }
                logger.info(json.dumps(message))
            detected_devices[dev.addr] = current_time  # Update the detection time
        else:
            if device_uuid != "NOT FOUND":
                logger.info(f"Device {dev.addr} detected again within cooldown period; not logging.")

if __name__ == "__main__":
    scanner = btle.Scanner().withDelegate(ScanDelegate())
    logger.info("Starting Bluetooth scanner...")
    while True:
        try:
            logger.info("Scanning for devices...")
            scanner.scan(10.0)
        except Exception as e:
            logger.error(f"Error in scanning: {e}")
        time.sleep(1)  # Short delay before the next scan