import pathlib
import webbrowser

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Route
from starlette.templating import Jinja2Templates

templates = Jinja2Templates(directory=pathlib.Path(__file__).parent / "templates")


async def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


app = Starlette(
    debug=True,
    routes=[
        Route("/", home),
    ],
)


def serve():
    webbrowser.open("http://localhost:5000")
    uvicorn.run("circle.server.main:app", port=5000, log_level="info")
