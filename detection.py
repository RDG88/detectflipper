import bluepy.btle as btle
import logging
import json
import requests
import time
from logging_loki import LokiHandler

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Configurable variables
enable_loki_logging = config.get('enable_loki_logging', False) # enable logging to loki
loki_url = config.get('loki_url', 'http://localhost:3100/loki/api/v1/push') # loki url, for now unauthenticated only
log_other_devices = config.get('log_other_devices', False) # for troubleshooting, this will output all bluetooth devices found
kofferid = config.get('kofferid', 'unknown') # name of the device
lat = config.get('lat', 'unknown') # latitude of the device
lon = config.get('lon', 'unknown') # lonitude of the device
alert = config.get('alert', 'f0') # configures the alert name to be send to loki
cooldown_period = config.get('cooldown_period', 60)  # seconds, default to 60 seconds if not set in config

# Setup logging to console
logger = logging.getLogger("f0_scanner")
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

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