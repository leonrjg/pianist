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
from PyQt6.QtMultimedia import QSoundEffect

from ..constants import Audio


class SoundManager:
    """Manages all sound effects for the piano application"""

    def __init__(self):
        self.start_player = self._create_sound_player('start')
        self.end_player = self._create_sound_player('end')

        # Warn if sound files are missing
        if not self.start_player and not self.end_player:
            print(f"Warning: No sound files found ({', '.join(Audio.SOUND_FILES.values())})")

    def _create_sound_player(self, sound_key: str) -> QSoundEffect | None:
        """Create a sound player for the given sound key"""
        if sound_key not in Audio.SOUND_FILES:
            print(f"Warning: Unknown sound key '{sound_key}'")
            return None

        file_path = Audio.SOUND_FILES[sound_key]
        if os.path.exists(file_path):
            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(file_path))
            return effect
        else:
            print(f"Warning: Sound file not found: {file_path}")
            return None

    def play_start_sound(self):
        """Play the session start sound effect"""
        try:
            if self.start_player:
                self.start_player.play()
        except Exception as e:
            print(f"Error playing start sound: {e}")

    def play_end_sound(self):
        """Play the session end sound effect"""
        try:
            if self.end_player:
                self.end_player.play()
        except Exception as e:
            print(f"Error playing end sound: {e}")

    def set_volume(self, volume: float):
        """Set volume for all sound effects (0.0 to 1.0)"""
        if self.start_player:
            self.start_player.setVolume(volume)
        if self.end_player:
            self.end_player.setVolume(volume)

    def mute(self):
        """Mute all sound effects"""
        self.set_volume(0.0)

    def unmute(self):
        """Unmute all sound effects (set to full volume)"""
        self.set_volume(1.0)
