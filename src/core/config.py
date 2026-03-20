import uuid
from pathlib import Path

_DEVICE_ID_PATH = Path.home() / ".pianist" / "device_id"


def get_device_id() -> str:
    if _DEVICE_ID_PATH.exists():
        return _DEVICE_ID_PATH.read_text().strip().replace('-', '')
    _DEVICE_ID_PATH.parent.mkdir(parents=True, exist_ok=True)
    device_id = uuid.uuid4().hex  # no dashes, matches Peewee UUIDField storage format
    _DEVICE_ID_PATH.write_text(device_id)
    return device_id
