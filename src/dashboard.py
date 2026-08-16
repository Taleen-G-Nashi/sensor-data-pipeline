import base64
import os
import sqlite3
from datetime import datetime
from io import BytesIO

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from flask import Flask, render_template_string


app = Flask(__name__)

DB_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "sensors.db",
)


def get_recent_readings(limit=50):
    """
    Return the most recent sensor readings from the SQLite database.

    The rows are returned oldest-to-newest so the plot appears in time order.
    """

    conn = sqlite3.connect(DB_PATH)

    rows = conn.execute(
        """
        SELECT
            timestamp,
            temperature,
            humidity,
            temp_alert,
            hum_alert
        FROM sensor_readings
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    conn.close()

    return list(reversed(rows))


def get_summary_stats():
    """
    Return total readings, total alert events, and pipeline uptime.
    """

    conn = sqlite3.connect(DB_PATH)

    total_readings = conn.execute(
        """
        SELECT COUNT(*)
        FROM sensor_readings
        """
    ).fetchone()[0]

    total_alerts = conn.execute(
        """
        SELECT COUNT(*)
        FROM alert_events
        """
    ).fetchone()[0]

    first_timestamp = conn.execute(
        """
        SELECT MIN(timestamp)
        FROM sensor_readings
        """
    ).fetchone()[0]

    last_timestamp = conn.execute(
        """
        SELECT MAX(timestamp)
        FROM sensor_readings
        """
    ).fetchone()[0]

    conn.close()

    if first_timestamp and last_timestamp:
        start = datetime.fromisoformat(first_timestamp)
        end = datetime.fromisoformat(last_timestamp)

        uptime_seconds = int(
            (end - start).total_seconds()
        )

        hours, remainder = divmod(
            uptime_seconds,
            3600,
        )

        minutes, seconds = divmod(
            remainder,
            60,
        )

        uptime = (
            f"{hours}h {minutes}m {seconds}s"
        )
    else:
        uptime = "--"

    return total_readings, total_alerts, uptime

def get_recent_events(limit=10):
    """
    Return the most recent alert/anomaly events.
    """

    conn = sqlite3.connect(DB_PATH)

    rows = conn.execute(
        """
        SELECT
            sensor_name,
            alert_type,
            message,
            created_at
        FROM alert_events
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    conn.close()

    return rows


def create_plot(
    rows,
    value_index,
    title,
    ylabel,
    threshold,
):
    """
    Create one time-series plot and return it as base64.
    """

    timestamps = [
        datetime.fromisoformat(row[0])
        for row in rows
    ]

    values = [
        row[value_index]
        for row in rows
    ]

    fig, ax = plt.subplots(
        figsize=(10, 4)
    )

    ax.plot(
        timestamps,
        values,
        linewidth=1.5,
    )

    ax.axhline(
        y=threshold,
        linestyle="--",
        alpha=0.6,
        label=f"Alert threshold: {threshold}",
    )

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("Time")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    ax.xaxis.set_major_formatter(
        mdates.DateFormatter("%H:%M:%S")
    )

    plt.xticks(rotation=30)
    fig.tight_layout()

    buffer = BytesIO()

    fig.savefig(
        buffer,
        format="png",
        dpi=120,
        bbox_inches="tight",
    )

    plt.close(fig)

    buffer.seek(0)

    return base64.b64encode(
        buffer.read()
    ).decode("utf-8")


HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Sensor Monitoring Dashboard</title>
    <meta http-equiv="refresh" content="10">

    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 24px;
            background: #f4f6f8;
        }

        h1 {
            margin-bottom: 8px;
        }

        .subtitle {
            color: #555;
            margin-bottom: 24px;
        }

        .card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        .stat {
            display: inline-block;
            margin-right: 40px;
            margin-bottom: 10px;
        }

        .value {
            font-size: 2em;
            font-weight: bold;
        }

        .label {
            color: #555;
        }

        .alert {
            font-weight: bold;
            color: #b00020;
        }

        .normal {
            color: #1b5e20;
            font-weight: bold;
        }

        table {
            border-collapse: collapse;
            width: 100%;
            margin-top: 12px;
        }

        th, td {
            padding: 8px 10px;
            border-bottom: 1px solid #ddd;
            text-align: left;
        }

        th {
            background: #e9eef5;
        }

        img {
            width: 100%;
            max-width: 1000px;
        }
    </style>
</head>

<body>
    <h1>Sensor Monitoring Dashboard</h1>
    <div class="subtitle">
        Arduino DHT readings stored in SQLite and displayed through Flask.
        Page refreshes every 10 seconds.
    </div>

    <div class="card">
        <h2>Current Reading</h2>

        <div class="stat">
    <div class="value">{{ latest_temp }}°C</div>
    <div class="label">
        Temperature —
        {% if latest_temp_alert %}
            <span class="alert">ALERT</span>
        {% else %}
            <span class="normal">Normal</span>
        {% endif %}
    </div>
</div>

<div class="stat">
    <div class="value">{{ latest_humidity }}%</div>
    <div class="label">
        Humidity —
        {% if latest_hum_alert %}
            <span class="alert">ALERT</span>
        {% else %}
            <span class="normal">Normal</span>
        {% endif %}
    </div>
</div>

        <div class="stat">
            <div class="value">{{ total_readings }}</div>
            <div class="label">Total Readings</div>
        </div>

        <div class="stat">
    <div class="value">{{ total_alerts }}</div>
    <div class="label">Alert Events</div>
</div>

<div class="stat">
    <div class="value">{{ uptime }}</div>
    <div class="label">Data Span</div>
</div>

        
    </div>

    <div class="card">
    <h2>Temperature — Last 50 Readings</h2>

    {% if temperature_plot %}
        <img src="data:image/png;base64,{{ temperature_plot }}">
    {% else %}
        <p>No temperature data available yet.</p>
    {% endif %}
</div>

<div class="card">
    <h2>Humidity — Last 50 Readings</h2>

    {% if humidity_plot %}
        <img src="data:image/png;base64,{{ humidity_plot }}">
    {% else %}
        <p>No humidity data available yet.</p>
    {% endif %}
</div>

<div class="card">
    <h2>Recent Events</h2>

    {% if recent_events %}
    <table>
        <tr>
            <th>Sensor</th>
            <th>Type</th>
            <th>Message</th>
            <th>Timestamp</th>
        </tr>

        {% for event in recent_events %}
        <tr>
            <td>{{ event[0] }}</td>
            <td>{{ event[1] }}</td>
            <td>{{ event[2] }}</td>
            <td>{{ event[3][:19] }}</td>
        </tr>
        {% endfor %}
    </table>

    {% else %}
        <p>No alert events recorded yet.</p>
    {% endif %}
</div>

    <div class="card">
        <h2>Recent Readings</h2>

        <table>
            <tr>
                <th>Timestamp</th>
                <th>Temperature (°C)</th>
                <th>Humidity (%)</th>
                <th>Status</th>
            </tr>

            {% for row in recent_rows %}
            <tr>
                <td>{{ row[0][:19] }}</td>
                <td>{{ row[1] }}</td>
                <td>{{ row[2] }}</td>
                <td>
                    {% if row[3] or row[4] %}
                        <span class="alert">ALERT</span>
                    {% else %}
                        <span class="normal">Normal</span>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""


@app.route("/")
def index():
    rows = get_recent_readings(limit=50)

    total_readings, total_alerts, uptime = (
        get_summary_stats()
    )

    recent_events = get_recent_events(
        limit=10
    )

    if not rows:
        return render_template_string(
            HTML,
            latest_temp="--",
            latest_humidity="--",
            latest_temp_alert=0,
            latest_hum_alert=0,
            total_readings=total_readings,
            total_alerts=total_alerts,
            uptime=uptime,
            recent_rows=[],
            recent_events=recent_events,
            temperature_plot="",
            humidity_plot="",
        )

    latest = rows[-1]

    temperature_plot = create_plot(
        rows,
        value_index=1,
        title="Temperature Over Time",
        ylabel="Temperature (°C)",
        threshold=30.0,
    )

    humidity_plot = create_plot(
        rows,
        value_index=2,
        title="Humidity Over Time",
        ylabel="Humidity (%)",
        threshold=80.0,
    )

    return render_template_string(
        HTML,
        latest_temp=latest[1],
        latest_humidity=latest[2],
        latest_temp_alert=latest[3],
        latest_hum_alert=latest[4],
        total_readings=total_readings,
        total_alerts=total_alerts,
        uptime=uptime,
        recent_rows=list(
            reversed(rows[-20:])
        ),
        recent_events=recent_events,
        temperature_plot=temperature_plot,
        humidity_plot=humidity_plot,
    )


if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000,
    )