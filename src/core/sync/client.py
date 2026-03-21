import logging
import threading
from datetime import datetime

import requests

from core.sync.merge import get_model_registry, serialize_row, merge_record

logger = logging.getLogger(__name__)

TIMEOUT = 10
EPOCH = datetime(1970, 1, 1)


def _build_delta(since: datetime) -> list:
    from core.db import db
    records = []
    with db.atomic():
        for table_name, model in get_model_registry().items():
            for row in model.select().where(model.updated_at > since):
                records.append(serialize_row(row, table_name))
    return records


class SyncClient:
    def __init__(self):
        self._active_peers: dict[str, str] = {}  # device_id -> url
        self._lock = threading.Lock()
        self._sync_count: int = 0  # number of delta_syncs currently in-flight
        self.on_sync_complete = None  # optional callback fired after each successful sync

    def register_peer(self, device_id: str, url: str) -> bool:
        """Register a peer. Returns True if the peer is newly added, False if already known."""
        with self._lock:
            is_new = device_id not in self._active_peers
            self._active_peers[device_id] = url
            return is_new

    def unregister_peer(self, device_id: str) -> None:
        with self._lock:
            self._active_peers.pop(device_id, None)

    @property
    def peer_count(self) -> int:
        with self._lock:
            return len(self._active_peers)

    @property
    def is_syncing(self) -> bool:
        with self._lock:
            return self._sync_count > 0

    def delta_sync(self, peer_url: str, peer_device_id: str) -> None:
        """Full bidirectional delta sync with a peer."""
        with self._lock:
            self._sync_count += 1
        try:
            info = requests.get(f'{peer_url}/sync/info', timeout=TIMEOUT).json()
            if info.get('device_id') != peer_device_id:
                return

            from core.sync.models import SyncState
            try:
                since = SyncState.get_by_id(peer_device_id).last_sync_at
            except SyncState.DoesNotExist:
                since = EPOCH

            resp = requests.get(
                f'{peer_url}/sync/delta',
                params={'since': since.isoformat()},
                timeout=TIMEOUT,
            )
            for item in resp.json().get('records', []):
                try:
                    merge_record(item['table'], item['data'])
                except Exception:
                    logger.exception("Failed to merge record: %s", item.get('table'))

            our_delta = _build_delta(since)
            requests.post(f'{peer_url}/sync/push', json={'records': our_delta}, timeout=TIMEOUT)

            now = datetime.now()
            SyncState.insert(device_id=peer_device_id, last_sync_at=now).on_conflict(
                conflict_target=[SyncState.device_id],
                update={SyncState.last_sync_at: now},
            ).execute()

            if self.on_sync_complete:
                self.on_sync_complete()
        except Exception:
            pass  # Will retry on next reconnect
        finally:
            with self._lock:
                self._sync_count -= 1

    def live_push(self, record: dict) -> None:
        """Fire-and-forget push of a single record to all active peers."""
        with self._lock:
            peers = dict(self._active_peers)
        for url in peers.values():
            threading.Thread(
                target=self._push_to_peer,
                args=(url, record),
                daemon=True,
            ).start()

    def _push_to_peer(self, url: str, record: dict) -> None:
        try:
            requests.post(f'{url}/sync/push', json={'records': [record]}, timeout=TIMEOUT)
        except Exception:
            pass
