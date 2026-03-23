"""
Settings Page - User-configurable preferences for the app.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSpinBox, QCheckBox, QSlider
from PyQt6.QtCore import Qt

from .base_page import SheetPage
from ..themed_form_widgets import ThemedButton
from ..themed_dropdown import ThemedDropdown

from core.settings.service import SettingsService


class SettingsPage(SheetPage):
    """App settings page."""

    def get_page_title(self) -> str:
        return "Settings"

    def get_page_type(self) -> str:
        return "settings"

    def build_content(self):
        layout = self.layout()
        layout.addWidget(self._create_section_header("Settings"))

        # --- Appearance ---
        layout.addSpacing(12)
        layout.addWidget(self._create_section_header("Appearance"))
        self._build_theme_row(layout)
        self._build_opacity_row(layout)
        layout.addWidget(self._create_separator())

        # --- Index Page ---
        layout.addSpacing(12)
        layout.addWidget(self._create_section_header("Index Page"))
        self._build_spinbox_row(
            layout,
            label="Show past days",
            key='index.past_days',
            min_val=0, max_val=90,
        )
        self._build_spinbox_row(
            layout,
            label="Show future days",
            key='index.future_days',
            min_val=1, max_val=365,
        )
        layout.addWidget(self._create_separator())

        # --- Sounds ---
        layout.addSpacing(12)
        layout.addWidget(self._create_section_header("Sounds"))
        self._build_toggle_row(layout, label="Enable sound effects", key='sounds.enabled')
        layout.addWidget(self._create_separator())

        # --- Reminders ---
        layout.addSpacing(12)
        layout.addWidget(self._create_section_header("Reminders"))
        self._build_toggle_row(layout, label="Enable reminders", key='reminders.enabled')
        layout.addWidget(self._create_separator())

        # --- Calendar ---
        layout.addSpacing(12)
        layout.addWidget(self._create_section_header("Calendar"))
        self._build_toggle_row(layout, label="Show ICAL events on calendar", key='calendar.ical_sources_visible')
        self._build_ical_section(layout)
        layout.addWidget(self._create_separator())

        # --- Export ---
        layout.addSpacing(12)
        layout.addWidget(self._create_section_header("Export"))
        csv = self._create_link_label('Export CSV', lambda: self.navigate_to.emit('export', None))
        layout.addWidget(csv)

        layout.addStretch()

    # --- Row builders ---

    def _build_theme_row(self, layout):
        row, h = self._make_row()
        h.addWidget(self._row_label("Theme"))

        themes = ['wood', 'sakura', 'midori']
        current = SettingsService.get('theme.active', 'wood')
        dropdown = ThemedDropdown(themes, default_item=current if current in themes else themes[0])

        def on_theme_changed(name):
            SettingsService.set('theme.active', name)
            self._apply_theme(name)

        dropdown.selection_changed.connect(on_theme_changed)
        h.addWidget(dropdown)
        layout.addWidget(row)

    def _build_opacity_row(self, layout):
        from gui.themes.manager import ThemeManager
        t = ThemeManager.get_instance().current
        row, h = self._make_row()
        h.addWidget(self._row_label("Window opacity"))

        current = int(SettingsService.get('window.opacity', 1.0) * 100)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(30, 100)
        slider.setValue(current)
        slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {t.border};
                height: 4px; border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {t.accent};
                width: 12px; height: 12px;
                margin: -4px 0; border-radius: 6px;
            }}
        """)

        value_lbl = QLabel(f"{current}%")
        value_lbl.setStyleSheet(f"color: {t.ink_secondary}; background: transparent; min-width: 32px;")

        def on_opacity_changed(val):
            SettingsService.set('window.opacity', val / 100.0)
            value_lbl.setText(f"{val}%")
            win = self.window()
            if win:
                win.setWindowOpacity(val / 100.0)

        slider.valueChanged.connect(on_opacity_changed)
        h.addWidget(slider)
        h.addWidget(value_lbl)
        layout.addWidget(row)

    def _build_spinbox_row(self, layout, label: str, key: str, min_val: int, max_val: int):
        row, h = self._make_row()
        h.addWidget(self._row_label(label))

        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(SettingsService.get(key, 0))
        from gui.themes.manager import ThemeManager
        t = ThemeManager.get_instance().current
        spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: {t.input_bg};
                border: 1px solid {t.border};
                border-radius: 2px;
                padding: 2px 4px;
                color: {t.ink_primary};
                max-width: 60px;
            }}
        """)

        def on_changed(val, k=key):
            SettingsService.set(k, val)

        spin.valueChanged.connect(on_changed)
        h.addWidget(spin)
        h.addStretch()
        layout.addWidget(row)

    def _build_toggle_row(self, layout, label: str, key: str):
        row, h = self._make_row()
        h.addWidget(self._row_label(label))

        cb = QCheckBox()
        cb.setChecked(bool(SettingsService.get(key, True)))

        def on_changed(state, k=key):
            SettingsService.set(k, bool(state))

        cb.stateChanged.connect(on_changed)
        h.addWidget(cb)
        h.addStretch()
        layout.addWidget(row)

    def _build_ical_section(self, layout):
        from core.ical.service import ICalService
        sources = ICalService.get_sources()
        for source in sources:
            row, h = self._make_row()
            h.addWidget(self._row_label(source.name))
            path_lbl = QLabel(source.path)
            from gui.themes.manager import ThemeManager
            t = ThemeManager.get_instance().current
            path_lbl.setStyleSheet(f"color: {t.ink_secondary}; font-size: 10px; background: transparent;")
            h.addWidget(path_lbl, 1)
            remove_btn = ThemedButton("Remove")
            remove_btn.clicked.connect(lambda checked, s=source: self._remove_ical_source(s))
            h.addWidget(remove_btn)
            layout.addWidget(row)

        add_btn = ThemedButton("Add ICAL File...")
        add_btn.clicked.connect(self._add_ical_source)
        layout.addWidget(add_btn)

    def _add_ical_source(self):
        from PyQt6.QtWidgets import QFileDialog, QInputDialog
        path, _ = QFileDialog.getOpenFileName(self, "Select .ics file", "", "iCalendar files (*.ics)")
        if not path:
            return
        name, ok = QInputDialog.getText(self, "Source name", "Display name for this calendar:")
        if not ok or not name.strip():
            return
        from core.ical.service import ICalService
        ICalService.add_source(name.strip(), path)
        self.refresh()

    def _remove_ical_source(self, source):
        from core.ical.service import ICalService
        ICalService.remove_source(source)
        self.refresh()

    def _make_row(self):
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 2, 0, 2)
        h.setSpacing(8)
        return row, h

    def _row_label(self, text: str) -> QLabel:
        from gui.themes.manager import ThemeManager
        t = ThemeManager.get_instance().current
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {t.ink_primary}; background: transparent; min-width: 140px;")
        return lbl

    def _apply_theme(self, theme_name: str):
        try:
            from gui.themes.manager import ThemeManager
            from PyQt6.QtWidgets import QApplication
            ThemeManager.get_instance().apply(QApplication.instance())
        except Exception:
            pass
