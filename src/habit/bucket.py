from datetime import datetime


class Bucket:
    def __init__(self, start: datetime, end: datetime, net_duration: int = 0, sessions: int = 0):
        self.start = start
        self.end = end
        self.net_duration = net_duration
        self.sessions = sessions

    def __repr__(self):
        return f"Bucket(start={self.start}, end={self.end}, net_duration={self.net_duration}, sessions={self.sessions})"
