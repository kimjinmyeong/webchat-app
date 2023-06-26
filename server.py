import datetime

import aiohttp
import aiohttp_jinja2
import jinja2
import redis
from aiohttp import web
from aiohttp_session import get_session, setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet

# initializing the redis instance
# r = redis.Redis(
#     host="127.0.0.1",
#     port=6379,
#     decode_responses=True,  # <-- this will ensure that binary data is decoded
# )


@aiohttp_jinja2.template("index.html")
class HomeHandler(web.View):
    async def get(self):
        return

    async def post(self):
        data = await self.request.post()
        nickname = data.get("nickname")
        session = await get_session(self.request)
        session["nickname"] = nickname
        return web.HTTPFound("/chat")


@aiohttp_jinja2.template("chat.html")
async def enter_chatroom(request: web.Request):
    return


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    session = await get_session(request)
    nickname = session["nickname"]
    print(f"{nickname} is connected.")

    # TODO: Applying Redis pub/sub
    async def receive_message_handler(ws: web.WebSocketResponse):
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == "close":
                    await ws.close()
                else:
                    data = {
                        "nickname": f"{nickname}",
                        "message": f"{msg.data}",
                        "time": f"{datetime.datetime.now().replace(microsecond=0)}",
                    }
                    await ws.send_json(data)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print("ws connection closed with exception %s" % ws.exception())

    await receive_message_handler(ws)
    session.invalidate()
    print(f"{nickname} connection closed")
    return ws


if __name__ == "__main__":
    app = web.Application()

    # set session key
    key = fernet.Fernet.generate_key()
    encoded_key = key.decode("utf-8")
    setup(
        app,
        EncryptedCookieStorage(encoded_key, httponly=True, max_age=60 * 60),  # 1 hour
    )

    # routes configuration
    app.add_routes(
        [
            web.view("/", HomeHandler),
            web.get("/chat", enter_chatroom),
            web.get("/chat-ws", websocket_handler),
        ]
    )

    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader("templates"))
    web.run_app(app, host="127.0.0.1", port=8080)
