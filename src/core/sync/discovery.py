import logging
import socket
import threading
from datetime import datetime

from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser, ServiceStateChange

from core.config import get_device_id
from core.sync.server import APP_VERSION, SYNC_PORT

SERVICE_TYPE = '_pianist._tcp.local.'
logger = logging.getLogger(__name__)


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


class DiscoveryService:
    def __init__(self, client):
        self._client = client
        self._zc: Zeroconf | None = None
        self._info: ServiceInfo | None = None
        self._browser = None
        # Maps mDNS service name -> peer device_id (needed on removal)
        self._name_to_device_id: dict[str, str] = {}

    def start(self) -> None:
        device_id = get_device_id()
        device_name = socket.gethostname()

        self._zc = Zeroconf()
        self._info = ServiceInfo(
            type_=SERVICE_TYPE,
            name=f'pianist-{device_id}.{SERVICE_TYPE}',
            addresses=[socket.inet_aton(_get_local_ip())],
            port=SYNC_PORT,
            properties={
                'device_id': device_id,
                'device_name': device_name,
                'app_version': APP_VERSION,
            },
            server=f'{device_name}.local.',
        )
        self._zc.register_service(self._info)
        self._browser = ServiceBrowser(self._zc, SERVICE_TYPE, handlers=[self._on_state_change])
        logger.info("mDNS discovery started")

    def stop(self) -> None:
        if self._zc:
            if self._info:
                self._zc.unregister_service(self._info)
            self._zc.close()
            self._zc = None
        logger.info("mDNS discovery stopped")

    def _on_state_change(
        self, zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange
    ) -> None:
        if state_change is ServiceStateChange.Added:
            self._on_peer_found(zeroconf, service_type, name)
        elif state_change is ServiceStateChange.Removed:
            self._on_peer_lost(name)

    def _on_peer_found(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
        info = zeroconf.get_service_info(service_type, name)
        if info is None:
            return

        props = {
            (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
            for k, v in info.properties.items()
        }
        peer_device_id = props.get('device_id')
        if not peer_device_id or peer_device_id == get_device_id():
            return  # Skip self

        peer_name = props.get('device_name', name)
        if not info.addresses:
            return
        peer_addr = socket.inet_ntoa(info.addresses[0])
        peer_url = f'http://{peer_addr}:{info.port}'

        self._name_to_device_id[name] = peer_device_id

        from core.sync.models import Device
        now = datetime.now()
        Device.insert(
            id=peer_device_id,
            name=peer_name,
            is_self=False,
            last_seen=now,
            created_at=now,
        ).on_conflict(
            conflict_target=[Device.id],
            update={Device.last_seen: now, Device.name: peer_name},
        ).execute()

        is_new = self._client.register_peer(peer_device_id, peer_url)
        if is_new:
            threading.Thread(
                target=self._client.delta_sync,
                args=(peer_url, peer_device_id),
                daemon=True,
            ).start()
        logger.info("Peer found: %s at %s", peer_device_id, peer_url)

    def _on_peer_lost(self, name: str) -> None:
        peer_device_id = self._name_to_device_id.pop(name, None)
        if not peer_device_id:
            return

        from core.sync.models import Device
        try:
            device = Device.get_by_id(peer_device_id)
            device.last_seen = datetime.now()
            device.save()
        except Device.DoesNotExist:
            pass

        self._client.unregister_peer(peer_device_id)
        logger.info("Peer lost: %s", peer_device_id)
