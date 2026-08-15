"""
Validation and anomaly-detection functions for DHT11 readings.
"""
import math

# -------------------------------------
# Validation limits
# -------------------------------------

TEMPERATURE_MIN = -40.0
TEMPERATURE_MAX = 80.0

HUMIDITY_MIN = 0.0
HUMIDITY_MAX = 100.0

TEMPERATURE_CHANGE_LIMIT = 5.0
HUMIDITY_CHANGE_LIMIT = 15.0


# -------------------------------------
# Reading validation
# -------------------------------------

def validate_reading(line):
    """
    Validate one Arduino reading.

    Expected format:

        24.3,60.0

    Returns:
        ((temperature, humidity), None) when valid.

        (None, rejection_message) when invalid.
    
    """

    if line is None or not line.strip():
        return None, "REJECTED: empty reading"

    parts = line.strip().split(",")

    if len(parts) != 2:
        return (
            None,
            "REJECTED: expected exactly two comma-separated values",
        )

    temperature_text = parts[0].strip()
    humidity_text = parts[1].strip()

    if not temperature_text:
        return None, "REJECTED: empty temperature value"

    if not humidity_text:
        return None, "REJECTED: empty humidity value"

    try:
        temperature = float(temperature_text)
        humidity = float(humidity_text)

    except ValueError:
        return None, "REJECTED: values must be numbers"

    if math.isnan(temperature) or math.isnan(humidity):
        return None, "REJECTED: NaN reading"

    if not math.isfinite(temperature) or not math.isfinite(humidity):
        return None, "REJECTED: infinite reading"

    if not TEMPERATURE_MIN <= temperature <= TEMPERATURE_MAX:
        return None, "REJECTED: temperature out of range"

    if not HUMIDITY_MIN <= humidity <= HUMIDITY_MAX:
        return None, "REJECTED: humidity out of range"

    return (temperature, humidity), None

# -------------------------------------
# Change-anomaly detection
# -------------------------------------

def detect_change_anomalies(temperature, humidity, previous_temperature=None, previous_humidity=None,):
     """
    Detect suspicious changes from the previous valid reading.

    A temperature change greater than 5°C is anomalous.
    A humidity change greater than 15% is anomalous.

    Returns a list of anomaly-event dictionaries.
    """

     events = []
     if previous_temperature is not None:
        temperature_change = abs(
            temperature - previous_temperature
        )

        if temperature_change > TEMPERATURE_CHANGE_LIMIT:
            events.append(
                {
                    "sensor_name": "temperature",
                    "alert_type": "change_anomaly",
                    "message": (
                        "Temperature changed by "
                        f"{temperature_change:.1f}°C "
                        "since the previous reading"
                    ),
                }
            )

     if previous_humidity is not None:
        humidity_change = abs(
            humidity - previous_humidity
        )

        if humidity_change > HUMIDITY_CHANGE_LIMIT:
            events.append(
                {
                    "sensor_name": "humidity",
                    "alert_type": "change_anomaly",
                    "message": (
                        "Humidity changed by "
                        f"{humidity_change:.1f}% "
                        "since the previous reading"
                    ),
                }
            )

     return events