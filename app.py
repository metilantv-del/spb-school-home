import os
from flask import Flask, jsonify, send_from_directory
import urllib.request
from google.transit import gtfs_realtime_pb2  # ✅ ПРАВИЛЬНЫЙ ИМПОРТ
from datetime import datetime
import pytz

STOPS_CONFIG = [
    {"name": "Лужская улица", "stop_id": "11426", "route_id": "51", "vehicle": "Трамвай", "direction": "school"},
    {"name": "проспект Мечникова", "stop_id": "11429", "route_id": "51", "vehicle": "Трамвай", "direction": "home"},
    {"name": "метро Гражданский проспект", "stop_id": "18868", "route_id": "295", "vehicle": "Автобус", "direction": "school"},
    {"name": "Замшина улица", "stop_id": "18872", "route_id": "295", "vehicle": "Автобус", "direction": "home"},
]

GTFS_RT_URL = "https://spb-transport.xyz/gtfs-rt"
TIMEZONE = pytz.timezone("Europe/Moscow")

app = Flask(__name__, static_folder='.')

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/api/all')
def get_all_arrivals():
    feed = gtfs_realtime_pb2.FeedMessage()
    try:
        response = urllib.request.urlopen(GTFS_RT_URL, timeout=10)
        feed.ParseFromString(response.read())
    except Exception as e:
        return jsonify({"error": "Ошибка подключения к данным СПб", "details": str(e)}), 500

    stop_data = {item["stop_id"]: [] for item in STOPS_CONFIG}

    for entity in feed.entity:
        if not entity.HasField('trip_update'):
            continue
        trip = entity.trip_update
        route_id = trip.trip.route_id

        for stu in trip.stop_time_update:
            if not stu.HasField('arrival') or not stu.arrival.time:
                continue

            stop_id = stu.stop_id
            if stop_id in stop_data:
                config = next((c for c in STOPS_CONFIG if c["stop_id"] == stop_id), None)
                if config and config["route_id"] == route_id:
                    arrival_time = datetime.fromtimestamp(stu.arrival.time, tz=TIMEZONE)
                    now = datetime.now(TIMEZONE)
                    if arrival_time > now:
                        delta_min = int((arrival_time - now).total_seconds() // 60)
                        stop_data[stop_id].append({
                            "arrival_time": arrival_time.strftime("%H:%M"),
                            "minutes": delta_min
                        })

    result = []
    for config in STOPS_CONFIG:
        arrivals = stop_data[config["stop_id"]]
        arrivals.sort(key=lambda x: x["minutes"])
        next_bus = arrivals[0] if arrivals else None
        result.append({
            "id": config["stop_id"],
            "vehicle": config["vehicle"],
            "route": config["route_id"],
            "stop_name": config["name"],
            "direction": config["direction"],
            "next": next_bus
        })

    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
