import bluepy.btle as btle
import logging
import json
import time

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

# Initialize a cache for detected devices with a cooldown period (e.g., 60 seconds)
detected_devices = {}
cooldown_period = 60  # seconds

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
                logger.info(f"Detected Flipper Zero: {dev.addr}, Name: {device_name}, Manufacturer: {device_manufacturer}, UUID: {device_uuid}, Type: {device_type}, RSSI: {rssi}")
            else:
                logger.info(f"Detected Device: {dev.addr}, Name: {device_name}, Manufacturer: {device_manufacturer}, RSSI: {rssi}")
            detected_devices[dev.addr] = current_time  # Update the detection time
        else:
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

