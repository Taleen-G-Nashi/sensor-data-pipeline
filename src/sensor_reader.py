import os
import sqlite3
from datetime import datetime

import serial


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
    Convert a line such as:

        24.50,63.00

    into two floating-point values:

        temperature = 24.5
        humidity = 63.0

    Invalid lines return (None, None).
    """

    parts = line.strip().split(",")

    if len(parts) != 2:
        return None, None

    try:
        temperature = float(parts[0])
        humidity = float(parts[1])

        return temperature, humidity

    except ValueError:
        return None, None


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

            while True:
                raw = ser.readline().decode(
                    "utf-8",
                    errors="ignore",
                )

                temperature, humidity = parse_line(raw)

                if temperature is None:
                    continue

                temp_alert, hum_alert = store_reading(
                    conn,
                    temperature,
                    humidity,
                )

                alert_message = (
                    " ALERT!"
                    if temp_alert or hum_alert
                    else ""
                )

                current_time = datetime.now().strftime(
                    "%H:%M:%S"
                )

                print(
                    f"{current_time} | "
                    f"Temp: {temperature}°C | "
                    f"Hum: {humidity}%"
                    f"{alert_message}"
                )

    except KeyboardInterrupt:
        print("\nStopped by user.")

    except serial.SerialException as error:
        print(f"\nSerial connection error: {error}")

    finally:
        conn.close()
        print("Database connection closed.")


if __name__ == "__main__":
    main()