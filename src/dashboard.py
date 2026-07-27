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


def get_summary_counts():
    """
    Return total number of readings and total number of alert readings.
    """

    conn = sqlite3.connect(DB_PATH)

    total_readings = conn.execute(
        """
        SELECT COUNT(*)
        FROM sensor_readings
        """
    ).fetchone()[0]

    alert_readings = conn.execute(
        """
        SELECT COUNT(*)
        FROM sensor_readings
        WHERE temp_alert = 1 OR hum_alert = 1
        """
    ).fetchone()[0]

    conn.close()

    return total_readings, alert_readings


def create_time_series_plot(rows):
    """
    Create a temperature and humidity time-series plot.

    The plot is returned as a base64 string so it can be embedded directly
    inside the Flask HTML page.
    """

    timestamps = [
        datetime.fromisoformat(row[0])
        for row in rows
    ]

    temperatures = [
        row[1]
        for row in rows
    ]

    humidities = [
        row[2]
        for row in rows
    ]

    fig, (ax1, ax2) = plt.subplots(
        2,
        1,
        figsize=(10, 6),
        sharex=True,
    )

    fig.suptitle(
        "Real-Time Sensor Monitoring Dashboard",
        fontsize=14,
        fontweight="bold",
    )

    ax1.plot(
        timestamps,
        temperatures,
        linewidth=1.5,
        label="Temperature",
    )

    ax1.axhline(
        y=30.0,
        linestyle="--",
        alpha=0.6,
        label="Temperature alert threshold",
    )

    ax1.set_ylabel("Temperature (°C)")
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    ax2.plot(
        timestamps,
        humidities,
        linewidth=1.5,
        label="Humidity",
    )

    ax2.axhline(
        y=80.0,
        linestyle="--",
        alpha=0.6,
        label="Humidity alert threshold",
    )

    ax2.set_ylabel("Humidity (%)")
    ax2.set_xlabel("Time")
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)

    ax2.xaxis.set_major_formatter(
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
            <div class="label">Temperature</div>
        </div>

        <div class="stat">
            <div class="value">{{ latest_humidity }}%</div>
            <div class="label">Humidity</div>
        </div>

        <div class="stat">
            <div class="value">{{ total_readings }}</div>
            <div class="label">Total Readings</div>
        </div>

        <div class="stat">
            <div class="value">{{ alert_readings }}</div>
            <div class="label">Alert Readings</div>
        </div>

        <p>
            Current status:
            {% if latest_temp_alert or latest_hum_alert %}
                <span class="alert">ALERT</span>
            {% else %}
                <span class="normal">Normal</span>
            {% endif %}
        </p>
    </div>

    <div class="card">
        <h2>Recent Time-Series Plot</h2>
        {% if plot_image %}
            <img src="data:image/png;base64,{{ plot_image }}">
        {% else %}
            <p>No plot available yet.</p>
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

    if not rows:
        return render_template_string(
            HTML,
            latest_temp="--",
            latest_humidity="--",
            latest_temp_alert=0,
            latest_hum_alert=0,
            total_readings=0,
            alert_readings=0,
            recent_rows=[],
            plot_image="",
        )

    total_readings, alert_readings = get_summary_counts()
    latest = rows[-1]
    plot_image = create_time_series_plot(rows)

    return render_template_string(
        HTML,
        latest_temp=latest[1],
        latest_humidity=latest[2],
        latest_temp_alert=latest[3],
        latest_hum_alert=latest[4],
        total_readings=total_readings,
        alert_readings=alert_readings,
        recent_rows=list(reversed(rows[-20:])),
        plot_image=plot_image,
    )


if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000,
    )