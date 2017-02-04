"""Simple event observer system supporting asyncio.

Observers must be removed to avoid memory leaks.
"""

class Event(object):
    """Event that tracks a list of observer callbacks to notify when fired."""
    def __init__(self, name):
        """Create a new Event with a name."""
        self._name = str(name)
        self._observers = []

    def add_observer(self, callback):
        """Add an event observer callback.

        Args:
            callback: a function.

        Raises ValueError if the callback has already been added.
        """
        if callback in self._observers:
            raise ValueError('{} is already an observer of {}'
                             .format(callback, self))
        self._observers.append(callback)

    def remove_observer(self, callback):
        """Remove an event observer callback.

        Raises ValueError if the callback is not an event observer.
        """
        if callback not in self._observers:
            raise ValueError('{} is not an observer of {}'
                             .format(callback, self))
        self._observers.remove(callback)

    def fire(self, *args, **kwargs):
        """Call all observer callbacks with the same arguments."""
        for observer in self._observers:
            observer(*args, **kwargs)

    def __repr__(self):
        return 'Event(\'{}\')'.format(self._name)

