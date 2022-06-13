import logging

import aiohttp
import aiohttp_jinja2
from aiohttp import web
from faker import Faker
from aiohttp.web_runner import GracefulExit
import hashlib

log = logging.getLogger(__name__)
HASHED_VALUE = hashlib.md5(b'true')


def get_random_name():
    fake = Faker()
    return fake.name()


async def stopChat(request):
    res = await request.text()
    if hashlib.md5((res.split('=')[1]).encode(
            "utf-8")).hexdigest() == HASHED_VALUE.hexdigest():
        log.info('Server has been stoped!')
        raise GracefulExit()
    else:
        return web.Response(status=200)


async def index(request):
    ws_current = web.WebSocketResponse()
    ws_ready = ws_current.can_prepare(request)
    if not ws_ready.ok:
        return aiohttp_jinja2.render_template('index.html', request, {})

    await ws_current.prepare(request)

    name = get_random_name()
    log.info('%s joined.', name)

    await ws_current.send_json({'action': 'connect', 'name': name})

    for ws in request.app['websockets'].values():
        await ws.send_json({'action': 'join', 'name': name})
    request.app['websockets'][name] = ws_current

    while True:
        msg = await ws_current.receive()

        if msg.type == aiohttp.WSMsgType.text:
            for ws in request.app['websockets'].values():
                if ws is not ws_current:
                    await ws.send_json(
                        {'action': 'sent', 'name': name, 'text': msg.data})
        else:
            break

    del request.app['websockets'][name]
    log.info('%s disconnected.', name)
    for ws in request.app['websockets'].values():
        await ws.send_json({'action': 'disconnect', 'name': name})

    return ws_current
