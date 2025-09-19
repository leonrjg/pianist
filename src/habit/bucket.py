from datetime import datetime


class Bucket:
    def __init__(self, start: datetime, end: datetime, net_duration: int = 0, sessions: int = 0):
        """Initialize a time bucket for tracking habit activity."""
        self.start = start
        self.end = end
        self.net_duration = net_duration or 0
        self.sessions = sessions

    def __repr__(self):
        """Return string representation of the bucket."""
        return f"Bucket(start={self.start}, end={self.end}, net_duration={self.net_duration}, sessions={self.sessions})"
