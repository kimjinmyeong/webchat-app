import datetime
import weakref
import aiohttp
import aiohttp_jinja2
import asyncio
import jinja2
import redis.asyncio as redis
from aiohttp import web, WSCloseCode
from aiohttp_session import get_session, setup, redis_storage


async def init_redis(app):
    # initialize the redis instances
    redis_pool = redis.ConnectionPool(host="redis", port=6379)
    redis_conn = await redis.Redis(connection_pool=redis_pool)
    redis_pubsub = redis_conn.pubsub()
    await redis_pubsub.subscribe("lablup")

    # test redis connection
    try:
        response = await redis_conn.ping()
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
    redis_conn = app["redis_conn"]
    storage = redis_storage.RedisStorage(redis_conn, httponly=True)
    setup(app, storage)


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
    if await redis_conn.exists(nickname):
        print("duplicated nickname!")
        return False

    date = datetime.datetime.now()
    await redis_conn.set(nickname, str(date))  # TODO set Time To Live
    return True


async def create_session(request: web.Request) -> None:
    data = await request.post()
    nickname = data.get("nickname")
    session = await get_session(request)
    session["nickname"] = nickname


@aiohttp_jinja2.template("chat.html")
async def render_chatroom(request: web.Request):
    return


@aiohttp_jinja2.template("errors.html")
async def render_errors(request: web.Request):
    return


async def send_messages(message: str) -> None:
    ws_queue = asyncio.Queue()
    messages = {
        "message": f"{message}",
        "time": f"{datetime.datetime.now().replace(microsecond=0)}",
    }
    for websocket in app["websockets"]:
        await ws_queue.put(websocket)
    while not ws_queue.empty():
        ws = await ws_queue.get()
        await ws.send_json(messages)


async def listen_to_redis(redis_pubsub):
    while True:
        try:
            message = await redis_pubsub.get_message()
        except RuntimeError:
            # RuntimeError: readuntil() called while another coroutine is already waiting for incoming data
            # Even if above error occurs, the server continues to function.
            pass
        finally:
            if message:
                if message["type"] == "message":
                    await send_messages(message["data"].decode())
            await asyncio.sleep(0.01)


async def websocket_handler(ws: web.WebSocketResponse, nickname: str) -> None:
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == "close":
                await ws.close()
            else:
                await app["redis_conn"].publish("lablup", f"{nickname}: {msg.data}")

        elif msg.type == aiohttp.WSMsgType.ERROR:
            print("ws connection closed with exception %s" % ws.exception())


async def chatroom_handler(request: web.Request) -> web.WebSocketResponse:
    session = await get_session(request)
    nickname = session["nickname"]

    ws = web.WebSocketResponse()
    app["websockets"].add(ws)
    await ws.prepare(request)

    redis_conn = app["redis_conn"]
    redis_pubsub = app["redis_pubsub"]

    websocket_listener = asyncio.create_task(websocket_handler(ws, nickname))
    redis_listener = asyncio.create_task(listen_to_redis(redis_pubsub))

    # Get the currently running tasks
    running_tasks = [task for task in asyncio.all_tasks() if not task.done()]

    # Print the number of running tasks
    print("Number of running tasks:", len(running_tasks))

    await redis_conn.publish("lablup", f"{nickname} has entered")
    await websocket_listener

    # Cleanup tasks and resources
    await redis_conn.publish("lablup", f"{nickname} has left")

    session.invalidate()
    app["websockets"].discard(ws)
    await app["redis_conn"].delete(nickname)

    redis_listener.cancel()
    websocket_listener.cancel()

    return ws


async def on_shutdown(app):
    await app["redis_conn"].flushall()
    await app["redis_conn"].close()
    for ws in app["websockets"]:
        await ws.close(code=WSCloseCode.GOING_AWAY, message="Server shutdown")


if __name__ == "__main__":
    app = web.Application()
    app["websockets"] = weakref.WeakSet()
    app.on_startup.append(init_redis)
    app.on_startup.append(init_session)
    app.on_shutdown.append(on_shutdown)

    app.add_routes(
        [
            web.view("/", HomeHandler),
            web.get("/chat", render_chatroom),
            web.get("/chat-ws", chatroom_handler),
            web.get("/errors", render_errors),
        ]
    )

    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader("templates"))
    web.run_app(app, host="0.0.0.0", port=8080)
