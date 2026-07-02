import os
import random
import sqlite3
from datetime import datetime, timedelta


DB_PATH = os.path.join(
    os.path.dirname(__file__),
    '..',
    'data',
    'sensors.db',
)


SCHEMA = '''
CREATE TABLE IF NOT EXISTS sensor_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_name TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    alert INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sensor_timestamp
ON sensor_readings (sensor_name, timestamp);
'''


ALERT_THRESHOLDS = {
    'temperature': 30.0,
    'humidity': 80.0,
    'light': 900.0,
}


def seed_data(conn, n=50):
    rows = []

    base = datetime.now() - timedelta(hours=n)

    for i in range(n):
        timestamp = (base + timedelta(hours=i)).isoformat()

        temperature = round(
            22 + random.uniform(-3, 12),
            2,
        )

        humidity = round(
            55 + random.uniform(-10, 30),
            2,
        )

        rows += [
            (
                'temperature',
                temperature,
                'celsius',
                timestamp,
                int(
                    temperature
                    > ALERT_THRESHOLDS['temperature']
                ),
            ),
            (
                'humidity',
                humidity,
                'percent',
                timestamp,
                int(
                    humidity
                    > ALERT_THRESHOLDS['humidity']
                ),
            ),
        ]

    conn.executemany(
        '''
        INSERT INTO sensor_readings
        (sensor_name, value, unit, timestamp, alert)
        VALUES (?, ?, ?, ?, ?)
        ''',
        rows,
    )

    conn.commit()

    print(f'Inserted {len(rows)} readings.')


def run_queries(conn):
    print('\n-- All alert events --')

    for row in conn.execute(
        '''
        SELECT sensor_name, value, unit, timestamp
        FROM sensor_readings
        WHERE alert = 1
        ORDER BY timestamp DESC
        LIMIT 10
        '''
    ):
        print(row)

    print('\n-- Average value per sensor --')

    for row in conn.execute(
        '''
        SELECT
            sensor_name,
            ROUND(AVG(value), 2),
            MAX(value),
            MIN(value)
        FROM sensor_readings
        GROUP BY sensor_name
        '''
    ):
        print(row)

    print('\n-- Alert count per sensor --')

    for row in conn.execute(
        '''
        SELECT
            sensor_name,
            COUNT(*) AS alerts
        FROM sensor_readings
        WHERE alert = 1
        GROUP BY sensor_name
        '''
    ):
        print(row)


def main():
    conn = sqlite3.connect(DB_PATH)

    conn.executescript(SCHEMA)

    seed_data(conn)
    run_queries(conn)

    conn.close()


if __name__ == '__main__':
    main()