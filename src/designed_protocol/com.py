import time

class Packet():
    def __init__(self, data, is_bytes=False):
        if is_bytes:
            data = self.unformat(data)
        self.id    = data[0][0]
        self.total = data[0][1]
        self.data  = data[1]
        self._time = time.time()
    def __repr__(self):
        return f'Packet<{self.id}/{self.total}>'
    def __lt__(self, other):
        return self.id < other.id
    def unformat(self, data):
        data = data.split(b'|', maxsplit=1)
        data[0] = list(map(int, (data[0]
                    .decode()
                    .replace(' ', '')
                    .replace('(', '')
                    .replace(')', '')
                    .split(',')
                    )))
        return data
    def format(self):
        header = (str((self.id,self.total)) + '|').encode()
        return header + self.data
    def get_age(self):
        return time.time() - self._time
    def reset_age(self):
        self._time = time.time()
