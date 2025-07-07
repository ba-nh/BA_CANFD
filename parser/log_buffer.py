# log_buffer.py
from collections import deque

class LogBuffer:
    def __init__(self, maxlen=1000):
        self.buffer = deque(maxlen=maxlen)

    def append(self, row):
        self.buffer.append(row)
    
    def add(self, row):
        self.buffer.append(row)

    def get_latest(self):
        return self.buffer[-1] if self.buffer else None
    
    def get_all_data(self):
        """버퍼의 모든 데이터를 반환하고 버퍼를 비움"""
        data = list(self.buffer)
        self.buffer.clear()
        return data

    def clear(self):
        self.buffer.clear()
