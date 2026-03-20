import socket
import threading
from datetime import datetime

from flask import Flask, request, jsonify

from core.config import get_device_id
from core.sync.merge import get_model_registry, serialize_row, merge_record

APP_VERSION = '1.0.0'
SYNC_PORT = 47832

app = Flask(__name__)


@app.route('/sync/info')
def sync_info():
    return jsonify({
        'device_id': get_device_id(),
        'device_name': socket.gethostname(),
        'app_version': APP_VERSION,
    })


@app.route('/sync/delta')
def sync_delta():
    since_str = request.args.get('since', '1970-01-01T00:00:00')
    try:
        since_dt = datetime.fromisoformat(since_str)
    except ValueError:
        since_dt = datetime(1970, 1, 1)

    records = []
    for table_name, model in get_model_registry().items():
        for row in model.select().where(model.updated_at > since_dt):
            records.append(serialize_row(row, table_name))

    return jsonify({
        'device_id': get_device_id(),
        'generated_at': datetime.now().isoformat(),
        'records': records,
    })


@app.route('/sync/push', methods=['POST'])
def sync_push():
    payload = request.get_json(force=True)
    for item in payload.get('records', []):
        merge_record(item['table'], item['data'])
    return jsonify({'status': 'ok'})


class SyncServer:
    def __init__(self):
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(
            target=lambda: app.run(
                host='0.0.0.0', port=SYNC_PORT, threaded=True, use_reloader=False
            ),
            daemon=True,
            name='sync-server',
        )
        self._thread.start()

    def stop(self) -> None:
        # Daemon thread exits with the process; no explicit shutdown needed for dev server
        pass
