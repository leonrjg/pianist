"""
Generic notification service for desktop notifications.

Uses a custom piano-themed toast widget.
"""

import math

from PyQt6.QtCore import QPoint

from gui.widgets.notification_toast import NotificationToast


class _MagnetDrag:
    """
    A drag offset that magnetically snaps back to its origin (zero offset).

    Two radii govern it:
      * ``break_distance`` — small travel needed to leave the origin. Kept tiny
        so the pile starts following the cursor almost immediately.
      * ``snap_distance`` — larger "catch" radius. While free, the offset is
        pulled back only when dragged *toward* the origin within this radius,
        so the magnet never fights a user who is deliberately dragging away.

    Crucially, when the offset breaks free it is *re-anchored* to the current
    cursor position, so it grows smoothly from zero instead of teleporting by a
    whole radius. The same applies after a snap, so continuing to drag away
    never jumps.
    """

    def __init__(self, snap_distance: int, break_distance: int = 18):
        self.snap_distance = snap_distance
        self.break_distance = break_distance
        self.offset = QPoint(0, 0)
        self._snapped = True            # True while resting at the origin
        self._begin_offset = QPoint(0, 0)
        self._bias = QPoint(0, 0)       # cursor position mapped to zero offset
        self._snap_raw = QPoint(0, 0)   # cursor position where it last pinned home
        self._prev_dist = 0.0

    def begin(self):
        """Capture the starting offset for a new drag gesture."""
        self._begin_offset = QPoint(self.offset)
        self._bias = QPoint(0, 0)
        self._prev_dist = math.hypot(self.offset.x(), self.offset.y())
        if self._snapped:
            self._snap_raw = QPoint(self._begin_offset)

    def update(self, dx: int, dy: int):
        """
        Apply a drag delta (relative to drag start).

        Returns:
            (offset, animate): the new offset and whether the move should be
            animated (True only on the snap-back "pull" to the origin).
        """
        raw = QPoint(self._begin_offset.x() + dx, self._begin_offset.y() + dy)
        animate = False

        if self._snapped:
            # Hold at the origin until the cursor clears the (small) break radius.
            moved = math.hypot(raw.x() - self._snap_raw.x(), raw.y() - self._snap_raw.y())
            if moved > self.break_distance:
                self._snapped = False
                self._bias = QPoint(raw)        # re-anchor: offset restarts at zero
                self.offset = QPoint(0, 0)
                self._prev_dist = 0.0
        else:
            candidate = QPoint(raw.x() - self._bias.x(), raw.y() - self._bias.y())
            dist = math.hypot(candidate.x(), candidate.y())
            moving_toward_origin = dist < self._prev_dist
            if moving_toward_origin and dist <= self.snap_distance:
                # Visibly pull back to the resting slot.
                self._snapped = True
                self._snap_raw = QPoint(raw)
                self.offset = QPoint(0, 0)
                self._prev_dist = 0.0
                animate = True
            else:
                self.offset = candidate
                self._prev_dist = dist

        return QPoint(self.offset), animate

    def settle(self) -> bool:
        """
        Finish a drag: if released within the catch radius, pin exactly home.

        Returns True when it settled home (so the caller can animate the move).
        Anything dropped beyond the catch radius is left where the user put it.
        """
        if self._snapped:
            return False  # already resting exactly at the origin
        dist = math.hypot(self.offset.x(), self.offset.y())
        if dist <= self.snap_distance:
            self._snapped = True
            self._snap_raw = QPoint(0, 0)
            self.offset = QPoint(0, 0)
            return True
        return False


class NotificationService:
    """
    Singleton notification service for displaying toast notifications.

    Also coordinates the on-screen pile of toasts:
      * Successive toasts are indented to the left so each one peeks out.
      * Dragging any toast moves the whole pile at once, snapping back to the
        resting slot via a magnet.
      * Clicking a toast brings it to the top of the pile and keeps it there.
    """

    _instance = None

    # Drag/snap tuning (pixels).
    GROUP_SNAP_DISTANCE = 80   # generous catch when restoring the whole pile
    STACK_MARGIN = 22          # left indent per successive toast in the pile

    @classmethod
    def get_instance(cls) -> 'NotificationService':
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._sound_manager = None
        self._active_toasts = []  # oldest first, newest ("front") last

        self._group = _MagnetDrag(self.GROUP_SNAP_DISTANCE)
        self._top_toast = None  # toast explicitly raised to the top of the pile

    def set_parent(self, widget):
        """
        Set parent widget for notifications.

        Args:
            widget: Parent QWidget (unused, kept for API compatibility)
        """
        self._sound_manager = getattr(widget, "sound_manager", None)

    def is_showing_task(self, dedup_key) -> bool:
        """Return whether a toast for ``dedup_key`` is currently on screen."""
        if dedup_key is None:
            return False
        return any(getattr(t, "dedup_key", None) == dedup_key for t in self._active_toasts)

    def show_toast(self, title: str, message: str, duration: int = 5000, urgency: str = 'normal', buttons: list = None, dedup_key=None):
        """
        Show a generic toast notification.

        Args:
            title: Notification title
            message: Notification message
            duration: Display duration in milliseconds
            urgency: Urgency level ('low', 'normal', 'high')
            buttons: Optional list of button configs (see NotificationToast.show_notification)
            dedup_key: Optional identity. If a toast with the same key is already
                visible, no new toast is created and that toast is returned.

        Returns:
            NotificationToast instance (for chaining updates)
        """
        try:
            existing = next(
                (t for t in self._active_toasts if dedup_key is not None and getattr(t, "dedup_key", None) == dedup_key),
                None
            )
            if existing is not None:
                return existing

            toast = NotificationToast()
            toast.dedup_key = dedup_key

            # Keep reference to prevent garbage collection
            self._active_toasts.append(toast)

            # Auto-cleanup when toast is destroyed
            toast.destroyed.connect(lambda: self._cleanup_toast(toast))

            # Per-toast layout state owned by this coordinator.
            toast.pile_offset = QPoint(0, 0)          # cascade indent in the pile
            toast.set_drag_coordinator(self)

            # A freshly shown toast becomes the top of the pile.
            self._top_toast = toast

            # Indent the pile before showing so the new toast slides straight to
            # its slot and the existing toasts glide aside to make room.
            self._recompute_pile()
            toast.show_notification(title, message, duration, urgency, buttons)
            self._reposition_all(animate=True, skip=toast)
            self._restack()

            if self._sound_manager:
                self._sound_manager.play_sound("notification")
            return toast
        except Exception as e:
            print(f"Failed to show notification: {e}")
            return None

    def _cleanup_toast(self, toast):
        """Remove toast from active list when destroyed and reflow the pile."""
        try:
            self._active_toasts.remove(toast)
        except (ValueError, AttributeError):
            return  # Already removed or list doesn't exist

        if self._top_toast is toast:
            self._top_toast = None  # fall back to newest-on-top
        self._recompute_pile()
        self._reposition_all(animate=True)
        self._restack()

    def show_reminder_notification(self, reminder_name: str, message: str, urgency: str = 'normal', dedup_key=None):
        """
        Show a reminder-specific notification.

        Args:
            reminder_name: Name of the reminder
            message: Message to display
            urgency: Urgency level ('low', 'normal', 'high')
            dedup_key: Optional identity to suppress duplicate visible toasts.
        """
        if urgency == 'high':
            duration = 15000
        elif urgency == 'low':
            duration = 5000
        else:
            duration = 12000

        self.show_toast(reminder_name, message, duration, urgency, dedup_key=dedup_key)

    # ------------------------------------------------------------------
    # Pile layout
    # ------------------------------------------------------------------
    def _recompute_pile(self):
        """
        Indent each toast left of the newest so it peeks out and is grabbable.

        The newest toast (front) sits at the base position; every older toast
        is shifted one STACK_MARGIN further left, exposing a grab strip.
        """
        n = len(self._active_toasts)
        for i, toast in enumerate(self._active_toasts):
            indent = -(n - 1 - i) * self.STACK_MARGIN
            toast.pile_offset = QPoint(indent, 0)

    def offset_for(self, toast) -> QPoint:
        """Total offset from the toast's home position (pile indent + group)."""
        return toast.pile_offset + self._group.offset

    def _reposition(self, toast, animate: bool):
        toast.apply_offset(self.offset_for(toast), animate)

    def _reposition_all(self, animate: bool, skip=None):
        for toast in self._active_toasts:
            if toast is not skip:
                self._reposition(toast, animate)

    def _restack(self):
        """
        Raise toasts oldest-to-newest so the newest sits on top, then lift the
        explicitly-clicked toast above all of it so it stays put.
        """
        for toast in self._active_toasts:
            toast.raise_()
        if self._top_toast is not None and self._top_toast in self._active_toasts:
            self._top_toast.raise_()

    # ------------------------------------------------------------------
    # Drag coordination
    # ------------------------------------------------------------------
    def begin_drag(self, toast):
        """Bring the pressed toast to the top, then start a whole-pile drag."""
        self._top_toast = toast
        self._restack()
        self._group.begin()

    def update_drag(self, toast, dx: int, dy: int):
        """Apply a drag delta to the whole pile."""
        _, animate = self._group.update(dx, dy)
        self._reposition_all(animate)

    def end_drag(self, toast):
        """On release, settle the pile home if dropped within the catch radius."""
        if self._group.settle():
            self._reposition_all(animate=True)
