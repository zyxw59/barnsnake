import bisect
import event

class View(object):
    """A selection of messages."""
    def __init__(self, messages=None):
        self._messages = []  # [Message]
        self._message_dict = {}  # {message_id: Message}
        self.on_message = event.Event('View.on_message')
        if messages is not None:
            for msg in messages:
                self.add_message(msg)

    def __contains__(self, msg):
        i = bisect.bisect_left(self._messages, msg)
        if i != len(self._messages) and self._messages[i] == msg:
            return True
        return False

    def __iter__(self):
        return iter(self._messages)

    def __len__(self):
        return len(self._messages)

    def add_message(self, msg):
        if msg.uid not in self._message_dict:
            idx = bisect.bisect(self._messages, msg)
            self._messages.insert(idx, msg)
            self._message_dict[msg.uid] = msg
            self.on_message.fire(msg, idx)

    def get_message(self, message_id):
        return self._message_dict[message_id]

    def next_message(self, message_id, prev=False):
        """Return Message following the message with given message_id.

        If prev is True, return the previous message rather than the following
        one.

        Raises KeyError if no such Message is known.

        Return None if there is no following message.
        """
        msg = self._message_dict[message_id]
        if prev:
            i = bisect.bisect_left(self._messages, msg)
            if i > 0:
                return self._messages[i - 1]
            return None
        i = bisect.bisect_right(self._messages, msg)
        if i < len(self._messages):
            return self._messages[i]
        return None

