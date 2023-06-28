import datetime
import weakref
import aiohttp
import aiohttp_jinja2
import asyncio
import jinja2
import redis

from aiohttp import web, WSCloseCode
from aiohttp_session import get_session, setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet


async def init_redis(app):
    # initializing the redis instances
    redis_pool = redis.ConnectionPool(host="127.0.0.1", port=6379)
    redis_conn = redis.Redis(connection_pool=redis_pool)
    redis_pubsub = redis_conn.pubsub()
    redis_pubsub.subscribe("lablup")

    # test redis connection
    try:
        response = redis_conn.ping()
        if response:
            print("Redis Connection is active.")
        else:
            print("Redis Connection is not active.")
    except redis.ConnectionError:
        print("Redis Connection error occurred.")

    app["redis_pool"] = redis_pool
    app["redis_conn"] = redis_conn
    app["redis_pubsub"] = redis_pubsub


async def init_session(app):
    key = fernet.Fernet.generate_key()
    encoded_key = key.decode("utf-8")
    setup(
        app,
        EncryptedCookieStorage(encoded_key, httponly=True),  # max_age=60*60 1 hour
    )


@aiohttp_jinja2.template("index.html")
class HomeHandler(web.View):
    async def get(self):
        return

    async def post(self):
        data = await self.request.post()
        nickname = data.get("nickname")

        is_nickname_created = await save_nickname(nickname)
        if not is_nickname_created:
            return web.HTTPFound("/errors")

        await create_session(self.request)
        return web.HTTPFound("/chat")


async def save_nickname(nickname: str) -> bool:
    if nickname == "":
        print("nickname is blank!")
        return False

    redis_conn = app["redis_conn"]
    if redis_conn.exists(nickname):
        print("duplicated nickname!")
        return False

    date = datetime.datetime.now()
    redis_conn.set(nickname, str(date))  # TODO set Time To Live
    return True


async def create_session(request: web.Request) -> None:
    data = await request.post()
    nickname = data.get("nickname")
    session = await get_session(request)
    session["nickname"] = nickname
    return


@aiohttp_jinja2.template("chat.html")
async def render_chatroom(request: web.Request):
    return


@aiohttp_jinja2.template("errors.html")
async def render_errors(request: web.Request):
    return


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    request.app["websockets"].add(ws)
    await ws.prepare(request)

    session = await get_session(request)
    nickname = session["nickname"]
    print(f"{nickname} is connected.")

    ws_queue = asyncio.Queue()

    redis_conn = app["redis_conn"]
    redis_pubsub = app["redis_pubsub"]
    # First get_message() returns subscribe/unsubscribe confirmation messages
    redis_pubsub.get_message()
    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == "close":
                    await ws.close()
                else:
                    # publish messages incoming client
                    redis_conn.publish("lablup", msg.data)
                    published_data = redis_pubsub.get_message()
                    published_message = published_data["data"]
                    message = {
                        "nickname": f"{nickname}",
                        "message": f"{published_message.decode()}",
                        "time": f"{datetime.datetime.now().replace(microsecond=0)}",
                    }
                    # send connected socket
                    for websocket in app["websockets"]:
                        await ws_queue.put(websocket)
                    while not ws_queue.empty():
                        ws = await ws_queue.get()
                        await ws.send_json(message)

            elif msg.type == aiohttp.WSMsgType.ERROR:
                print("ws connection closed with exception %s" % ws.exception())
    finally:
        # disconnect
        request.app["websockets"].discard(ws)
        app["redis_conn"].delete(nickname)
        session.invalidate()
        print(f"{nickname} connection closed")

    return ws


async def on_shutdown(app):
    # shutdown redis server
    app["redis_conn"].flushall()
    app["redis_conn"].close()

    # The Python GC will handle object cleanup while the connection_pool is managed outside of the Redis() object.
    # redis_pool = app["redis_pool"]
    # redis_pool.release(redis_conn)

    for ws in set(app["websockets"]):
        await ws.close(code=WSCloseCode.GOING_AWAY, message="Server shutdown")


if __name__ == "__main__":
    app = web.Application()
    app["websockets"] = weakref.WeakSet()
    app.on_startup.append(init_redis)
    app.on_startup.append(init_session)
    app.on_shutdown.append(on_shutdown)

    # routes configuration
    app.add_routes(
        [
            web.view("/", HomeHandler),
            web.get("/chat", render_chatroom),
            web.get("/chat-ws", websocket_handler),
            web.get("/errors", render_errors),
        ]
    )

    # TODO configure cors

    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader("templates"))
    web.run_app(app, host="0.0.0.0", port=8080)
