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
    Create the sensor_readings table and timestamp index
    if they do not already exist.
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

    conn.execute(
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

    return temp_alert, hum_alert


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
                temp_alert, hum_alert = store_reading(
                    conn,
                    temperature,
                    humidity,
                )

                threshold_messages = []

                if temp_alert:
                    threshold_messages.append(
                        "temperature above 30°C"
                    )

                if hum_alert:
                    threshold_messages.append(
                        "humidity above 80%"
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