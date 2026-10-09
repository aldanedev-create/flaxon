"""Equivalent ASGI workloads; every application has 1,000 dynamic routes.

JSON is serialized by each framework's normal response path on every request.
No response caching or pre-encoded JSON is used.
"""
from flaxon import Flaxon
from flaxon.http import TextResponse
from fastapi import FastAPI
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from litestar import Litestar, get
from litestar.response import Response as LitestarResponse
from sanic import Sanic
from sanic.response import text as sanic_text, json as sanic_json
import falcon
import falcon.asgi

SMALL = {'message': 'Hello, World!'}
ROWS = [{'id': i, 'name': f'Task {i}', 'done': False} for i in range(1000)]

flaxon_app = Flaxon('framework-benchmark', debug=False)
fastapi_app = FastAPI()
sanic_app = Sanic('framework_benchmark')
sanic_app.config.ACCESS_LOG = False
falcon_app = falcon.asgi.App()
starlette_routes = []
litestar_handlers = []


def install_fixed(path, kind):
    payload = 'Hello, World!' if kind == 'text' else SMALL if kind == 'json' else ROWS
    async def flaxon_handler():
        return TextResponse(payload) if kind == 'text' else payload
    async def fastapi_handler():
        return PlainTextResponse(payload) if kind == 'text' else payload
    async def starlette_handler(request):
        return PlainTextResponse(payload) if kind == 'text' else JSONResponse(payload)
    async def sanic_handler(request):
        return sanic_text(payload) if kind == 'text' else sanic_json(payload)
    async def litestar_handler() -> LitestarResponse:
        return LitestarResponse(payload, media_type='text/plain' if kind == 'text' else 'application/json')
    class Resource:
        async def on_get(self, req, resp):
            if kind == 'text':
                resp.content_type = falcon.MEDIA_TEXT
                resp.text = payload
            else:
                resp.media = payload
    name = kind + '_handler'
    flaxon_app.get(path, name=name)(flaxon_handler)
    fastapi_app.get(path)(fastapi_handler)
    starlette_routes.append(Route(path, starlette_handler))
    sanic_app.add_route(sanic_handler, path, name=name)
    litestar_handler.__name__ = name
    litestar_handlers.append(get(path)(litestar_handler))
    falcon_app.add_route(path, Resource())


for path, kind in [('/plaintext', 'text'), ('/json', 'json'), ('/large-json', 'large')]:
    install_fixed(path, kind)


def install_dynamic(index):
    async def flaxon_handler(item_id: int):
        return {'id': item_id, 'route': index}
    async def fastapi_handler(item_id: int):
        return {'id': item_id, 'route': index}
    async def starlette_handler(request):
        return JSONResponse({'id': request.path_params['item_id'], 'route': index})
    async def sanic_handler(request, item_id):
        return sanic_json({'id': item_id, 'route': index})
    async def litestar_handler(item_id: int) -> dict[str, int]:
        return {'id': item_id, 'route': index}
    class Resource:
        async def on_get(self, req, resp, item_id):
            resp.media = {'id': item_id, 'route': index}
    base = f'/routes/{index}'
    flaxon_app.get(base + '/<int:item_id>', name=f'route_{index}')(flaxon_handler)
    fastapi_app.get(base + '/{item_id}')(fastapi_handler)
    starlette_routes.append(Route(base + '/{item_id:int}', starlette_handler))
    sanic_app.add_route(sanic_handler, base + '/<item_id:int>', name=f'route_{index}')
    litestar_handler.__name__ = f'route_{index}'
    litestar_handlers.append(get(base + '/{item_id:int}')(litestar_handler))
    falcon_app.add_route(base + '/{item_id:int}', Resource())


for index in range(1000):
    install_dynamic(index)

starlette_app = Starlette(routes=starlette_routes)
litestar_app = Litestar(route_handlers=litestar_handlers)
