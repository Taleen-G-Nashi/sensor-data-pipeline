# DHT11 Sensor Notes and Data Quality

## Sensor Purpose

The DHT11 is a low-cost digital sensor used to measure:

- temperature
- relative humidity

It is appropriate for demonstrating a real-time environmental monitoring pipeline, but it is not a precision scientific instrument.

## Expected Readings

Typical indoor readings are approximately:

- Temperature: 15–35°C
- Humidity: 20–80%

Actual values depend on the environment.

## Validation Rules

The pipeline rejects readings when:

- the serial message does not contain exactly two comma-separated values
- either value cannot be converted to a number
- either value is empty
- either value is NaN
- temperature is outside the configured valid range
- humidity is outside 0–100%

Rejected readings are not inserted into the `sensor_readings` table.

## Threshold Alerts

Configured monitoring thresholds:

- Temperature > 30°C
- Humidity > 80%

A reading exceeding either threshold is still a valid measurement, but an associated `threshold_alert` event is created.

## Change Anomalies

The system also checks the change from the previous valid reading.

An anomaly is generated when:

- temperature changes by more than 5°C between consecutive readings
- humidity changes by more than 15 percentage points between consecutive readings

These are simple rule-based anomaly checks designed to detect sudden sensor changes or potentially unreliable measurements.

## Limitations

The DHT11:

- has relatively low measurement precision
- has a slow sampling rate compared with higher-end sensors
- may occasionally produce invalid or unstable measurements
- should not be treated as laboratory-grade instrumentation

The pipeline therefore separates sensor acquisition from validation and event detection rather than trusting every incoming measurement automatically.