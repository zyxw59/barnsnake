import collections
import datetime
import socket
import zephyr

class ComparableMixin(object):
    def _compare(self, other, method):
        try:
            return method(self.key, other.key)
        except (AttributeError, TypeError):
            return NotImplemented

    def __lt__(self, other):
        return self._compare(other, lambda s, o: s < o)

    def __le__(self, other):
        return self._compare(other, lambda s, o: s <= o)

    def __eq__(self, other):
        return self._compare(other, lambda s, o: s == o)

    def __ge__(self, other):
        return self._compare(other, lambda s, o: s >= o)

    def __gt__(self, other):
        return self._compare(other, lambda s, o: s > o)

    def __ne__(self, other):
        return self._compare(other, lambda s, o: s != o)


class Message(collections.UserDict, ComparableMixin):
    def __init__(self, time):
        super().__init__()
        try:
            self.time = float(time)
        except TypeError:
            self.time = time.timestamp()
        self.uid = id(self)

    @property
    def key(self):
        return (self.time, self.uid)

    def __eq__(self, other):
        return self.uid == other.uid

    def __hash__(self):
        return hash(self.uid)


class ZephyrMessage(Message):
    def __init__(self, znotice):
        super().__init__(znotice.time)
        self.znotice = znotice
        self.uid = znotice.uid
        self.update(znotice.__dict__)
        self['time'] = datetime.datetime.fromtimestamp(self.time)
        self['zsig'] = znotice.fields[0]
        self['message'] = znotice.fields[1].strip('\n')
        self['host'] = self.uid.address
        try:
            self['pretty_host'] = socket.gethostbyaddr(self['host'])
        except socket.herror:
            self['pretty_host'] = self['host']
