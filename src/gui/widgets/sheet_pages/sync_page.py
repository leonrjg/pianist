"""
Sync Page - Shows sync status, known devices, and network permission state.
"""

import platform
import threading
from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices

from .base_page import SheetPage


def _friendly_dt(dt: Optional[datetime]) -> str:
    if dt is None:
        return "Never"
    now = datetime.now()
    delta = now - dt
    secs = int(delta.total_seconds())
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{secs // 60}m ago"
    if secs < 86400:
        return f"{secs // 3600}h ago"
    return dt.strftime("%b %d")


def _network_permission_status() -> tuple[str, Optional[str]]:
    """Return (status_text, settings_url_or_None)."""
    if platform.system() == 'Darwin':
        try:
            from core.sync.service import SyncService
            discovery = SyncService.get_instance()._discovery
            running = discovery._zc is not None
        except Exception:
            running = False

        if running:
            return "Local network access active — mDNS discovery is running", None
        return (
            "Local network access may be restricted",
            "x-apple.systempreferences:com.apple.preference.security?Privacy_LocalNetwork",
        )
    return "Local network access is not restricted on this platform", None


class SyncPage(SheetPage):
    """Sync status page showing devices and network permission."""

    def get_page_title(self) -> str:
        return "Sync"

    def get_page_type(self) -> str:
        return "sync"

    def build_content(self):
        layout = self.layout()
        layout.addWidget(self._create_section_header("Sync"))

        # --- Network access ---
        layout.addWidget(self._create_section_header("Network Access"))
        self._build_permissions_section(layout)
        layout.addWidget(self._create_separator())

        # --- Devices ---
        layout.addWidget(self._create_section_header("Known Devices"))
        self._build_devices_section(layout)

        layout.addStretch()

    def _build_permissions_section(self, layout):
        status_text, settings_url = _network_permission_status()
        layout.addWidget(self._create_text_label(status_text))

        if settings_url:
            link = self._create_link_label(
                "Open Privacy & Security Settings",
                lambda url=settings_url: QDesktopServices.openUrl(QUrl(url)),
            )
            layout.addWidget(link)

    def _build_devices_section(self, layout):
        from core.sync.models import Device, SyncState
        from core.sync.service import SyncService

        devices = list(Device.select().where(Device.is_self == False))

        if not devices:
            layout.addWidget(self._create_text_label(
                "No devices discovered yet — devices appear when found on the local network.",
                secondary=True,
            ))
            self._build_sync_button(layout, active_peers={})
            return

        try:
            client = SyncService.get_instance().client
            with client._lock:
                active_peers = dict(client._active_peers)
        except Exception:
            active_peers = {}

        # Header row
        layout.addWidget(self._create_device_header())

        for device in devices:
            try:
                last_sync = SyncState.get_by_id(device.id).last_sync_at
            except SyncState.DoesNotExist:
                last_sync = None

            is_active = str(device.id).replace('-', '') in active_peers
            layout.addWidget(self._create_device_row(device, last_sync, is_active))

        layout.addWidget(self._create_separator())
        self._build_sync_button(layout, active_peers)

    def _create_device_header(self) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 4, 0, 2)
        h.setSpacing(8)

        def _header_label(text, stretch):
            lbl = QLabel(text)
            lbl.setStyleSheet("color: rgb(110, 90, 70); font-style: italic; background: transparent;")
            font = lbl.font()
            font.setPointSize(font.pointSize() - 1)
            lbl.setFont(font)
            h.addWidget(lbl, stretch)

        _header_label("Device", 3)
        _header_label("Status", 2)
        _header_label("Last seen", 2)
        _header_label("Last synced", 2)
        return row

    def _create_device_row(self, device, last_sync: Optional[datetime], is_active: bool) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 4, 0, 4)
        h.setSpacing(8)

        # Name
        name_lbl = QLabel(device.name)
        name_lbl.setStyleSheet("color: rgb(70, 50, 35); background: transparent;")
        font = name_lbl.font()
        font.setBold(True)
        name_lbl.setFont(font)
        h.addWidget(name_lbl, 3)

        # Status dot
        if is_active:
            status_lbl = QLabel("● In range")
            status_lbl.setStyleSheet("color: rgb(60, 140, 60); background: transparent;")
        else:
            status_lbl = QLabel("○ Offline")
            status_lbl.setStyleSheet("color: rgb(140, 120, 95); background: transparent;")
        h.addWidget(status_lbl, 2)

        # Last seen
        last_seen_lbl = QLabel(_friendly_dt(device.last_seen))
        last_seen_lbl.setStyleSheet("color: rgb(110, 90, 70); background: transparent;")
        h.addWidget(last_seen_lbl, 2)

        # Last synced
        last_sync_lbl = QLabel(_friendly_dt(last_sync))
        last_sync_lbl.setStyleSheet("color: rgb(110, 90, 70); background: transparent;")
        h.addWidget(last_sync_lbl, 2)

        return row

    def _build_sync_button(self, layout, active_peers: dict):
        from .vintage_form_widgets import VintageButton

        btn = VintageButton("Sync Now")
        btn.setEnabled(len(active_peers) > 0)
        btn.setToolTip("Trigger a delta sync with all reachable devices")

        def _on_sync_now():
            btn.setEnabled(False)
            btn.setText("Syncing…")

            def _do_sync():
                try:
                    from core.sync.service import SyncService
                    client = SyncService.get_instance().client
                    with client._lock:
                        peers = dict(client._active_peers)
                    for device_id, url in peers.items():
                        client.delta_sync(url, device_id)
                finally:
                    # Re-enable on the GUI thread
                    QTimer.singleShot(0, lambda: (btn.setEnabled(True), btn.setText("Sync Now")))

            threading.Thread(target=_do_sync, daemon=True).start()

        btn.clicked.connect(_on_sync_now)
        layout.addWidget(btn)
