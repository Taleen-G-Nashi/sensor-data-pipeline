import sqlite3

from src.sensor_reader import (
    init_db,
    parse_line,
    store_reading,
)


def test_valid_csv_line_parses_correctly():
    temperature, humidity = parse_line("24.3,60.0")

    assert temperature == 24.3
    assert humidity == 60.0


def test_empty_line_returns_none():
    temperature, humidity = parse_line("")

    assert temperature is None
    assert humidity is None


def test_malformed_line_returns_none():
    temperature, humidity = parse_line("24.3")

    assert temperature is None
    assert humidity is None


def test_temperature_above_threshold_triggers_alert():
    conn = sqlite3.connect(":memory:")

    init_db(conn)

    _, temp_alert, _ = store_reading(
        conn,
        temperature=31.0,
        humidity=60.0,
    )

    conn.close()

    assert temp_alert == 1


def test_temperature_below_threshold_does_not_trigger_alert():
    conn = sqlite3.connect(":memory:")

    init_db(conn)

    _, temp_alert, _ = store_reading(
        conn,
        temperature=25.0,
        humidity=60.0,
    )

    conn.close()

    assert temp_alert == 0