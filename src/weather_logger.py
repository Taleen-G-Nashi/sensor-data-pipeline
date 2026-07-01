import requests
import sqlite3
import os
from datetime import datetime


DB_PATH = os.path.join(
    os.path.dirname(__file__),
    '..',
    'data',
    'weather.db'
)


def create_table(conn):
    conn.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            temperature REAL NOT NULL,
            wind_speed REAL NOT NULL,
            location TEXT NOT NULL
        )
    ''')
    conn.commit()


def fetch_geneva_weather():
    url = 'https://api.open-meteo.com/v1/forecast'

    params = {
        'latitude': 46.23,
        'longitude': 6.05,
        'current': 'temperature_2m,wind_speed_10m',
        'timezone': 'Europe/Zurich',
    }

    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()

    data = resp.json()['current']

    return data['temperature_2m'], data['wind_speed_10m']


def store_reading(conn, temp, wind):
    conn.execute(
        'INSERT INTO readings '
        '(timestamp, temperature, wind_speed, location) '
        'VALUES (?, ?, ?, ?)',
        (
            datetime.now().isoformat(),
            temp,
            wind,
            'Geneva-CERN'
        )
    )

    conn.commit()


def main():
    conn = sqlite3.connect(DB_PATH)

    create_table(conn)

    try:
        temp, wind = fetch_geneva_weather()
        store_reading(conn, temp, wind)

        print(
            f'Logged: {temp}°C | '
            f'{wind} km/h | '
            f'{datetime.now().strftime("%H:%M:%S")}'
        )

    except requests.exceptions.RequestException as error:
        print(f'API error: {error}')

    finally:
        conn.close()


if __name__ == '__main__':
    main()