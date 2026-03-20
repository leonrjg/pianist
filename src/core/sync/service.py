from core.sync.client import SyncClient
from core.sync.discovery import DiscoveryService
from core.sync.server import SyncServer


class SyncService:
    _instance: 'SyncService | None' = None

    def __init__(self):
        self._client = SyncClient()
        self._server = SyncServer()
        self._discovery = DiscoveryService(self._client)

    @classmethod
    def get_instance(cls) -> 'SyncService':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start(self) -> None:
        self._server.start()
        self._discovery.start()

    def stop(self) -> None:
        self._discovery.stop()
        self._server.stop()

    @property
    def client(self) -> SyncClient:
        return self._client
