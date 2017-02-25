import os.path
import asyncio
import zephyr as z

SUBSFILE = os.path.expanduser('~/.zephyr.subs')

async def loadsubs(subsfile=SUBSFILE):
    subs = z.Subscriptions()
    subs.sub_all(subsfile)
    return subs


async def receive(wait=1e-3):
    """Wait for incoming zephyrs.

    Args:
        wait (optional): how long to wait before polling for new zephyrs, in
            seconds

    Returns:
        An incoming zephyr notice
    """
    while True:
        r = z.receive()
        if r is None:
            await asyncio.sleep(wait)
        else:
            return r
