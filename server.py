import aiohttp_jinja2
import aiohttp_session
import jinja2
from aiohttp import web
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet


@aiohttp_jinja2.template("index.html")
class HomeHandler(web.View):
    async def get(self):
        return

    async def post(self):
        data = await self.request.post()
        nickname = data.get("nickname")
        session = await aiohttp_session.get_session(self.request)
        session["nickname"] = nickname
        return web.HTTPFound("/chat")


@aiohttp_jinja2.template("chat.html")
async def chat_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    # async for msg in ws:
    #     if msg.type == aiohttp.WSMsgType.TEXT:
    #         if msg.data == "close":
    #             await ws.close()
    #         else:
    #             await ws.send_str(msg.data + "/answer")
    #     elif msg.type == aiohttp.WSMsgType.ERROR:
    #         print("ws connection closed with exception %s" % ws.exception())
    #
    # print("websocket connection closed")

    # TODO: Set Redis pub/sub, webSocket

    return


if __name__ == "__main__":
    app = web.Application()

    # set session key
    key = fernet.Fernet.generate_key()
    encoded_key = key.decode("utf-8")
    aiohttp_session.setup(
        app,
        EncryptedCookieStorage(encoded_key, httponly=True, max_age=60 * 60),  # 1 hour
    )

    # routes configuration
    app.add_routes(
        [
            web.view("/", HomeHandler),
            web.get("/chat", chat_handler),
        ]
    )

    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader("templates"))
    web.run_app(app)
