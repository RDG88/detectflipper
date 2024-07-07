# Flipper zero Device Scanner

This script scans for nearby Bluetooth devices and logs their details. It specifically identifies and logs Flipper Zero devices, logging them as warnings, while other devices are logged as informational messages. The script supports logging to both the console and a Loki logging server.

## Features

- Scans for Bluetooth devices using `bluepy.btle`.
- Identifies and logs specific types of devices (e.g., Flipper Zero).
- Logs device details to the console.
- Optionally logs Flipper Zero detections to a Loki server.
- Configurable via a `config.json` file or environment variables.

## Requirements

- Python 3
- bluepy
- requests
- logging_loki

## Installation

1. Install the required Python packages:
    ```sh
    pip install bluepy requests logging_loki
    ```

2. Create a `config.json` file in the same directory as the script (optional).

## Configuration

The script can be configured via a `config.json` file or environment variables. Environment variables take precedence over the configuration file.

### config.json

Example `config.json`:
```json
{
    "enable_loki_logging": true,
    "loki_url": "http://localhost:3100/loki/api/v1/push",
    "log_other_devices": true,
    "kofferid": "your_kofferid_value",
    "lat": "your_latitude_value",
    "lon": "your_longitude_value",
    "alert": "your_alert_value",
    "cooldown_period": 60
}
```

## Environment Variables
- ENABLE_LOKI_LOGGING: Enable or disable logging to Loki (true or false).
- LOKI_URL: The URL of the Loki server.
- LOG_OTHER_DEVICES: Enable or disable logging of other devices (true or false).
- KOFFERID: The ID associated with the scanner.
- LAT: Latitude value.
- LON: Longitude value.
- ALERT: Alert message.
- COOLDOWN_PERIOD: Cooldown period in seconds.



Usage

	1.	Ensure that your Bluetooth adapter is working and accessible.
	2.	Run the script:

    python bluetooth_scanner.py




Script Details

Main Components

	•	Configuration Loading: The script first attempts to load configuration from config.json. If the file is not found, it proceeds with default values or environment variables.
	•	Logging Setup: Configures logging to the console and optionally to a Loki server.
	•	Bluetooth Scanning: Uses bluepy.btle to scan for Bluetooth devices and handles device discovery.
	•	Device Identification: Identifies specific types of devices, such as Flipper Zero, and logs their details.

Script Workflow

	1.	Load configuration.
	2.	Setup logging.
	3.	Initialize Bluetooth scanner with a delegate to handle device discovery.
	4.	Start scanning for devices.
	5.	On discovering a device, log its details based on the device type and configured settings.

Logging

	•	Console Logging: Logs all detected devices to the console.
	•	Loki Logging: Optionally logs Flipper Zero detections to a Loki server as warnings.

Device Discovery

During device discovery, the script captures the following details:

	•	Device name
	•	Manufacturer
	•	UUID
	•	Device type (e.g., White, Black, Transparent)
	•	RSSI (signal strength)
	•	Configured additional fields (kofferid, lat, lon, alert)

Example Output

Example console output:

```
2024-07-07 07:23:55,738 - f0_scanner - INFO - {"timestamp": 1720355035.73851, "type": "Other Device", "address": "80:e1:26:71:74:4a", "name": "A7suroli", "manufacturer": "NOT FOUND", "rssi": -75}
2024-07-07 07:23:55,738 - f0_scanner - WARNING - {"timestamp": 1720355035.73851, "type": "Flipper Zero", "address": "80:e1:26:71:74:4a", "name": "A7suroli", "manufacturer": "NOT FOUND", "uuid": "00003082-0000-1000-8000-00805f9b34fb", "device_type": "White", "rssi": -75, "kofferid": "your_kofferid_value", "lat": "your_latitude_value", "lon": "your_longitude_value", "alert": "your_alert_value"}
```
