import os
import sqlite3
from datetime import datetime

import serial

try:
    from .anomaly_detector import (
        detect_change_anomalies,
        validate_reading,
    )
except ImportError:
    # Used when running: python3 src/sensor_reader.py
    from anomaly_detector import (
        detect_change_anomalies,
        validate_reading,
    )


# -------------------------------------
# Configuration
# -------------------------------------

PORT = "/dev/ttyUSB0"
BAUD = 9600

DB_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "sensors.db",
)

THRESHOLDS = {
    "temperature": 30.0,
    "humidity": 80.0,
}


# ----------------------------------
# Database setup
# ----------------------------------

def init_db(conn):
    """
    Create database tables and indexes if they do not exist.
    """

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            temperature REAL NOT NULL,
            humidity REAL NOT NULL,
            temp_alert INTEGER NOT NULL DEFAULT 0,
            hum_alert INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS alert_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reading_id INTEGER,
            sensor_name TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (reading_id)
                REFERENCES sensor_readings (id)
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_timestamp
        ON sensor_readings (timestamp)
        """
    )

    conn.commit()

    print(f"Database initialised at {DB_PATH}")


# -----------------------------------
# Serial-data parsing
# -----------------------------------

def parse_line(line):
    """
    Convert a valid Arduino CSV line into temperature
    and humidity values.

    Invalid readings return (None, None).
    """

    reading, _ = validate_reading(line)

    if reading is None:
        return None, None

    return reading


# ---------------------------------------------
# Database insertion and alert calculation
# ---------------------------------------------

def store_reading(conn, temperature, humidity):
    """
    Calculate alert flags and store one sensor reading.
    """

    temp_alert = int(
        temperature > THRESHOLDS["temperature"]
    )

    hum_alert = int(
        humidity > THRESHOLDS["humidity"]
    )

    cursor = conn.execute(
        """
        INSERT INTO sensor_readings (
            timestamp,
            temperature,
            humidity,
            temp_alert,
            hum_alert
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            datetime.now().isoformat(),
            temperature,
            humidity,
            temp_alert,
            hum_alert,
        ),
    )

    conn.commit()

    reading_id = cursor.lastrowid

    return reading_id, temp_alert, hum_alert

#-----------------------
#Storing Alert Events
#-----------------------
def store_alert_event(
    conn,
    reading_id,
    sensor_name,
    alert_type,
    message,
):
    """
    Store one alert or anomaly event.

    reading_id may be None for invalid readings because
    rejected readings are not stored in sensor_readings.
    """

    conn.execute(
        """
        INSERT INTO alert_events (
            reading_id,
            sensor_name,
            alert_type,
            message,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            reading_id,
            sensor_name,
            alert_type,
            message,
            datetime.now().isoformat(),
        ),
    )

    conn.commit()


# ------------------------------------------------------------
# Main program
# ------------------------------------------------------------

def main():
    os.makedirs(
        os.path.dirname(DB_PATH),
        exist_ok=True,
    )

    conn = sqlite3.connect(DB_PATH)

    init_db(conn)

    print(
        f"Opening serial port {PORT} "
        f"at {BAUD} baud..."
    )

    try:
        with serial.Serial(
            PORT,
            BAUD,
            timeout=5,
        ) as ser:

            print(
                "Connected. Reading sensor data. "
                "Press Ctrl+C to stop."
            )

            previous_temperature = None
            previous_humidity = None

            while True:
                raw = ser.readline().decode(
                    "utf-8",
                    errors="ignore",
                )

                current_time = datetime.now().strftime(
                    "%H:%M:%S"
                )

                reading, rejection_reason = validate_reading(
                    raw
                )

                # Invalid readings are rejected and are not
                # written to the database.
                if rejection_reason is not None:
                    raw_display = raw.strip() or "<empty>"

                    # Identify which sensor the rejection refers to when possible.
                    if "temperature" in rejection_reason.lower():
                        sensor_name = "temperature"
                    elif "humidity" in rejection_reason.lower():
                        sensor_name = "humidity"
                    else:
                        sensor_name = "reading"

                    store_alert_event(
                        conn,
                        reading_id=None,
                        sensor_name=sensor_name,
                        alert_type="invalid_reading",
                        message=rejection_reason,
                    )

                    print(
                        f"{current_time} | "
                        f"{rejection_reason} | "
                        f"Raw: {raw_display!r}"
                    )

                    continue

                temperature, humidity = reading

                # Compare this valid reading with the previous
                # valid reading.
                change_events = detect_change_anomalies(
                    temperature=temperature,
                    humidity=humidity,
                    previous_temperature=previous_temperature,
                    previous_humidity=previous_humidity,
                )

                # Store the valid reading and calculate
                # threshold-alert flags.
                reading_id, temp_alert, hum_alert = store_reading(
                    conn,
                    temperature,
                    humidity,
                )

                threshold_messages = []

                if temp_alert:
                    store_alert_event(
                        conn,
                        reading_id=reading_id,
                        sensor_name="temperature",
                        alert_type="threshold_alert",
                        message=(
                            f"Temperature {temperature:.1f}°C "
                            f"exceeded threshold "
                            f"{THRESHOLDS['temperature']:.1f}°C"
                        ),
                    )

                if hum_alert:
                    store_alert_event(
                        conn,
                        reading_id=reading_id,
                        sensor_name="humidity",
                        alert_type="threshold_alert",
                        message=(
                            f"Humidity {humidity:.1f}% "
                            f"exceeded threshold "
                            f"{THRESHOLDS['humidity']:.1f}%"
                        ),
                    )

                if threshold_messages:
                    threshold_status = (
                        "THRESHOLD ALERT: "
                        + "; ".join(threshold_messages)
                    )
                else:
                    threshold_status = "Normal"

                print(
                    f"{current_time} | "
                    f"Temp: {temperature:.1f}°C | "
                    f"Hum: {humidity:.1f}% | "
                    f"{threshold_status}"
                )

                for event in change_events:
                    store_alert_event(
                        conn,
                        reading_id=reading_id,
                        sensor_name=event["sensor_name"],
                        alert_type=event["alert_type"],
                        message=event["message"],
                    )

                    print(
                        f"{current_time} | "
                        f"CHANGE ANOMALY | "
                        f"{event['message']}"
                    )

                # Only valid readings become the previous values.
                previous_temperature = temperature
                previous_humidity = humidity


    except KeyboardInterrupt:
        print("\nStopped by user.")

    except serial.SerialException as error:
        print(f"\nSerial connection error: {error}")

    finally:
        conn.close()
        print("Database connection closed.")


if __name__ == "__main__":
    main()