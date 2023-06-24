import asyncio

import aiohttp
import aiohttp_jinja2
import jinja2
from aiohttp import web


@aiohttp_jinja2.template("index.html")
class HomeHandler(web.View):
    async def get(self):
        return

    # TODO
    async def post(self):
        pass


async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    # TODO
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

    return ws


if __name__ == "__main__":
    app = web.Application()
    app.add_routes(
        [
            web.get("/", HomeHandler),
            web.post("/", HomeHandler),
            web.get("/ws", websocket_handler),
        ]
    )
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader("templates"))
    web.run_app(app)
