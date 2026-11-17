# System Architecture

The sensor data pipeline collects environmental measurements from a DHT11 sensor and processes them through a small real-time monitoring stack.

## Data Flow

```text
DHT11 Sensor
     ↓
Arduino
     ↓
Serial Communication
     ↓
sensor_reader.py
     ↓
anomaly_detector.py
     ↓
SQLite
 ┌───────────────┬──────────────┐
 │               │              │
sensor_readings  alert_events
 │               │
 └───────┬───────┘
         ↓
   dashboard.py
         ↓
      Flask
         ↓
      Browser
    