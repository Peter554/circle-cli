import webbrowser

import uvicorn
from htpy.starlette import HtpyResponse
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Route

from .pages.home import home as home_page


async def home(request: Request) -> HtpyResponse:
    return HtpyResponse(home_page())


app = Starlette(
    debug=True,
    routes=[
        Route("/", home),
    ],
)


def serve():
    # TODO Flags?
    webbrowser.open("http://localhost:5000")
    uvicorn.run("circle.server.main:app", port=5000, log_level="info")
