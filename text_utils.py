import datetime
import re
import socket
import zephyr

var_matcher = lambda s: r'(?<!\$)((?:\$\$)*)\$(' + s + ')'
var_match = re.compile(var_matcher(r'\w+'))

class MessageFormatter(object):
    def __init__(self, fmt_str, **fmt_args):
        self.fmt_str = fmt_str
        self.fmt_args = fmt_args

    def __call__(self, msg):
        """Formats a message."""
        return var_match.sub(self.subfn(msg), self.fmt_str)

    def subfn(self, msg):
        def outfn(match):
            field = match.group(2)
            if field not in msg:
                return ''
            if field in self.fmt_args:
                if isinstance(self.fmt_args[field], str):
                    return match.group(1) + self.fmt_args[field].format(msg[field])
                try:
                    return match.group(1) + self.fmt_args[field](msg)
                except TypeError:
                    return match.group(1) + self.fmt_args[field][msg[field]].format(msg[field])
            return r'{}{}'.format(match.group(1), msg[field])
        return outfn


zephyr_format = MessageFormatter(
    '$cls / $instance / $sender$auth $recipient $time $zsig\n$message',
    sender=lambda msg: ('@b({})' if msg['auth'] else '{}').format(pretty_zsender(msg['sender'])),
    auth={True: '', False: '@b(!)'},
    recipient=lambda msg: pretty_zrecipient(msg['recipient']),
    zsig='({})',
    time=lambda msg: msg['time'].isoformat())


def pretty_host(host):
    try:
        return socket.gethostbyaddr(host)[0]
    except socket.herror:
        return host


def pretty_zsender(sender):
    if '@' in sender:
        user, host = sender.rsplit('@', 1)
        if host.lower() == zephyr.realm().lower():
            return user
    return sender


def pretty_zrecipient(recipient):
    if recipient.startswith('@'):
        if recipient[1:].lower() == zephyr.realm.lower():
            return ''
        return recipient[1:]
    return recipient.rsplit('@', 1)[0]
