import bluepy.btle as btle
import logging
import json
import time
import requests
from logging_loki import LokiHandler

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Setup logging to console
logger = logging.getLogger("device_detection")
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Variable to control logging to Loki
enable_loki_logging = config.get('enable_loki_logging', True)

# Function to check if Loki is reachable
def check_loki_reachable(url):
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException as e:
        logger.error(f"Failed to reach Loki: {e}")
        return False

# Setup Loki logging if enabled and Loki is reachable
if enable_loki_logging:
    loki_url = config['loki_url']
    if check_loki_reachable(loki_url):
        loki_handler = LokiHandler(
            url=loki_url,
            tags={"application": "bluetooth_scanner"},
            version="1",
        )
        logger.addHandler(loki_handler)
    else:
        logger.error("Loki is not reachable. Disabling Loki logging.")
        enable_loki_logging = False

# Initialize a cache for detected devices with a cooldown period (e.g., 60 seconds)
detected_devices = {}
cooldown_period = 60  # seconds

# Variable to control logging of other devices
log_other_devices = config.get('log_other_devices', True)  # Set to False to disable logging of other devices

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
                    "rssi": rssi
                }
                logger.info(json.dumps(message))
                if enable_loki_logging:
                    logger.info(message)  # This will send the message to Loki as well
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
                if enable_loki_logging:
                    logger.info(message)  # This will send the message to Loki as well
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
