"""
Sound Manager - Handles all sound effects for the piano interface.

This manager handles:
- Loading sound files
- Playing session start/end sounds
- Managing sound players
- Future sounds can be added here

Benefits:
- Centralized sound management
- Easy to add new sounds
- Handles missing sound files gracefully
"""
import os

from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QSoundEffect, QMediaDevices

from ..constants import Audio


class SoundManager:
    """Manages all sound effects for the piano application"""

    def __init__(self):
        self.players: dict[str, QSoundEffect | None] = {}

        def initialize_players():
            """Initialize sound players for all sound effects"""
            for name in Audio.SOUND_FILES.keys():
                if name in self.players:
                    del self.players[name]
                self.players[name] = self._create_sound_player(name)

        initialize_players()
        self.devices = QMediaDevices()
        self.devices.audioOutputsChanged.connect(initialize_players)


    def _create_sound_player(self, sound_key: str) -> QSoundEffect | None:
        """Create a sound player for the given sound key"""
        file_path = Audio.SOUND_FILES.get(sound_key)
        if not os.path.exists(file_path):
            print(f"Warning: Sound file not found: {file_path}")
            return None

        effect = QSoundEffect()
        effect.setSource(QUrl.fromLocalFile(file_path))
        return effect

    def play_sound(self, name: str):
        """Play the session start sound effect"""
        try:
            if name in self.players:
                self.players[name].play()
        except Exception as e:
            print(f"Error playing start sound: {e}")

    def set_volume(self, volume: float):
        """Set volume for all sound effects (0.0 to 1.0)"""
        for player in self.players.values():
            if player:
                player.setVolume(volume)

    def mute(self):
        """Mute all sound effects"""
        self.set_volume(0.0)

    def unmute(self):
        """Unmute all sound effects (set to full volume)"""
        self.set_volume(1.0)
