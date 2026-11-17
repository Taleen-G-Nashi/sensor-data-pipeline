# Real-Time Sensor Data Pipeline

An end-to-end environmental monitoring system that acquires temperature and humidity data from an Arduino-connected DHT11 sensor, validates incoming measurements, detects threshold and rate-of-change anomalies, stores readings and events in SQLite, and visualizes the system through a live Flask dashboard.

## Overview

This project demonstrates a small real-time data acquisition and monitoring pipeline.

The system reads temperature and humidity measurements from a DHT11 sensor through Arduino serial communication. A Python ingestion layer validates each reading before storage, detects abnormal conditions, and records alert events separately from the underlying time-series data.

A Flask dashboard provides live monitoring of sensor values, historical plots, system statistics, and recent alert events.

The project also includes automated unit tests, GitHub Actions continuous integration, and Docker support for reproducible execution of the dashboard application.

## Architecture

```text
DHT11 Sensor
     ↓
Arduino
     ↓
Serial Communication
     ↓
sensor_reader.py
     ↓
Data Validation
     ↓
anomaly_detector.py
     ↓
┌──────────────────────────────┐
│            SQLite            │
│                              │
│  sensor_readings             │
│  alert_events                │
└──────────────┬───────────────┘
               ↓
         dashboard.py
               ↓
             Flask
               ↓
            Browser
```

A more detailed architecture description is available in [`docs/architecture.md`](docs/architecture.md).

## Features

### Real-Time Sensor Acquisition

The Arduino reads DHT11 temperature and humidity values and transmits them over serial in CSV format:

```text
24.3,60.0
```

`sensor_reader.py` reads the serial stream using PySerial and timestamps each accepted measurement.

### Data Validation

Incoming data is validated before being written to the database.

The pipeline rejects readings when:

- the message does not contain exactly two comma-separated values
- temperature or humidity cannot be converted to numeric values
- either value is empty
- either value is `NaN` or non-finite
- temperature is outside the configured valid range
- humidity is outside 0–100%

Rejected measurements are not inserted into the main readings table.

### Threshold Detection

Valid readings are checked against configured monitoring thresholds:

- Temperature > 30°C
- Humidity > 80%

Threshold violations remain valid measurements but generate a `threshold_alert` event.

### Rate-of-Change Anomaly Detection

The system compares each valid measurement with the previous valid measurement.

A `change_anomaly` event is generated when:

- temperature changes by more than 5°C between consecutive readings
- humidity changes by more than 15 percentage points between consecutive readings

This provides a simple rule-based mechanism for identifying sudden sensor changes.

### Alert History

The system distinguishes three event types:

| Event type | Meaning |
| --- | --- |
| `threshold_alert` | A valid measurement exceeded a configured threshold |
| `change_anomaly` | A valid measurement changed unusually quickly |
| `invalid_reading` | Incoming sensor data failed validation |

Invalid measurements are deliberately excluded from `sensor_readings`, while the rejection itself can still be recorded in `alert_events`.

## Database

The project uses SQLite with two main tables.

### `sensor_readings`

| Column | Description |
| --- | --- |
| `id` | Primary key |
| `timestamp` | Time the reading was stored |
| `temperature` | Temperature in °C |
| `humidity` | Relative humidity in % |
| `temp_alert` | Temperature threshold flag |
| `hum_alert` | Humidity threshold flag |

### `alert_events`

| Column | Description |
| --- | --- |
| `id` | Primary key |
| `reading_id` | Related `sensor_readings.id`, nullable for rejected readings |
| `sensor_name` | Sensor associated with the event |
| `alert_type` | `threshold_alert`, `change_anomaly`, or `invalid_reading` |
| `message` | Human-readable event description |
| `created_at` | Event timestamp |

For valid measurements, `alert_events.reading_id` references the corresponding row in `sensor_readings`.

## Dashboard

The Flask monitoring dashboard displays:

- latest temperature and humidity
- independent `Normal` / `ALERT` status indicators
- total number of stored readings
- total number of alert events
- recorded data span
- temperature plot for the latest 50 readings
- humidity plot for the latest 50 readings
- latest 10 alert/anomaly events
- recent sensor readings

The page automatically refreshes every 10 seconds.

## Tech Stack

| Area | Technology |
| --- | --- |
| Hardware | Arduino, DHT11 |
| Embedded communication | Serial / USB |
| Language | Python 3.14 |
| Serial ingestion | PySerial |
| Database | SQLite |
| Visualization | Matplotlib |
| Web dashboard | Flask |
| Testing | pytest |
| Continuous integration | GitHub Actions |
| Containerization | Docker |
| Development environment | Linux / WSL2, Git, GitHub |

## Repository Structure

```text
sensor-data-pipeline/
├── .github/
│   └── workflows/
│       └── tests.yml
│
├── data/
│   └── .gitkeep
│
├── docs/
│   ├── architecture.md
│   └── calibration.md
│
├── src/
│   ├── anomaly_detector.py
│   ├── csv_processor.py
│   ├── dashboard.py
│   ├── db_schema.py
│   ├── sensor_reader.py
│   └── weather_logger.py
│
├── tests/
│   ├── test_anomaly_detector.py
│   └── test_sensor_reader.py
│
├── .dockerignore
├── .gitignore
├── Dockerfile
├── README.md
└── requirements.txt
```

The CSV processor and weather logger were developed as supporting data-pipeline exercises and are retained in the repository alongside the primary sensor-monitoring application.

## Running Locally

### 1. Clone the repository

```bash
git clone <repository-url>
cd sensor-data-pipeline
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Connect the Arduino

Ensure the Arduino serial device is available to Linux/WSL.

The project currently expects:

```text
/dev/ttyUSB0
```

The Arduino serial monitor must be closed before Python connects to the serial port.

### 5. Start sensor ingestion

```bash
python3 src/sensor_reader.py
```

Example output:

```text
03:04:29 | Temp: 29.2°C | Hum: 72.4% | Normal
03:04:31 | Temp: 29.2°C | Hum: 72.3% | Normal
```

Valid readings are stored in:

```text
data/sensors.db
```

### 6. Start the dashboard

In a second terminal:

```bash
source venv/bin/activate
python3 src/dashboard.py
```

Open:

```text
http://localhost:5000
```

## Tests

The project contains unit tests covering parsing, validation, threshold detection, and rate-of-change anomaly detection.

Run:

```bash
python3 -m pytest tests/ -v
```

Current test suite:

```text
10 passed
```

The tests use controlled inputs and in-memory SQLite databases, so an Arduino is not required to run them.

## Continuous Integration

GitHub Actions automatically runs the pytest suite on pushes and pull requests to `main`.

The CI workflow:

1. checks out the repository
2. configures Python 3.14
3. installs project dependencies
4. executes the complete pytest suite

This verifies that the core pipeline logic works in a clean environment rather than only in the local development environment.

## Docker

The Flask dashboard can also run inside a Docker container.

### Build the image

```bash
docker build -t sensor-pipeline .
```

### Run the container

```bash
docker run --rm -p 5000:5000 sensor-pipeline
```

Then open:

```text
http://localhost:5000
```

The Docker image intentionally excludes local `.db` files. When started in a fresh container, the dashboard initializes an empty SQLite schema automatically.

The current Docker configuration containerizes the dashboard application and its Python environment. Live Arduino serial ingestion is run separately on the host rather than exposing the USB serial device directly to the container.

## Data Quality and Sensor Limitations

The DHT11 is a low-cost environmental sensor and should not be treated as laboratory-grade instrumentation.

The pipeline therefore does not automatically trust every incoming measurement. Validation and event detection are applied between acquisition and persistence.

Additional notes are available in [`docs/calibration.md`](docs/calibration.md).

## Development Practices Demonstrated

This project combines several software and data-engineering concepts in one end-to-end system:

- serial hardware integration
- streaming data ingestion
- input validation
- time-series persistence
- relational database design
- foreign-key relationships
- SQL joins and aggregation
- rule-based anomaly detection
- web monitoring
- automated unit testing
- continuous integration
- containerization
- technical documentation

## CV Description

> Built an Arduino-to-Python time-series sensor pipeline with SQLite logging, data validation, threshold and rate-of-change anomaly detection, SQL alert tracking, automated tests, and a Flask monitoring dashboard.