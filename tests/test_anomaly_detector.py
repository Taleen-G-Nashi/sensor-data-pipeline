from src.anomaly_detector import (
    detect_change_anomalies,
    validate_reading,
)


def test_temperature_change_above_5_flagged_as_anomaly():
    events = detect_change_anomalies(
        temperature=31.0,
        humidity=60.0,
        previous_temperature=24.0,
        previous_humidity=60.0,
    )

    assert any(
        event["sensor_name"] == "temperature"
        and event["alert_type"] == "change_anomaly"
        for event in events
    )


def test_temperature_change_below_5_not_flagged():
    events = detect_change_anomalies(
        temperature=27.0,
        humidity=60.0,
        previous_temperature=24.0,
        previous_humidity=60.0,
    )

    assert not any(
        event["sensor_name"] == "temperature"
        for event in events
    )


def test_humidity_change_above_15_flagged_as_anomaly():
    events = detect_change_anomalies(
        temperature=24.0,
        humidity=80.0,
        previous_temperature=24.0,
        previous_humidity=60.0,
    )

    assert any(
        event["sensor_name"] == "humidity"
        and event["alert_type"] == "change_anomaly"
        for event in events
    )


def test_temperature_out_of_range_rejected_as_invalid():
    reading, error = validate_reading("90.0,60.0")

    assert reading is None
    assert error == "REJECTED: temperature out of range"


def test_humidity_above_100_rejected_as_invalid():
    reading, error = validate_reading("24.0,110.0")

    assert reading is None
    assert error == "REJECTED: humidity out of range"