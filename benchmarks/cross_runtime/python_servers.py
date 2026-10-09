"""Equivalent Python HTTP handlers for the same Uvicorn configuration."""
from fastapi import FastAPI
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

fastapi_app = FastAPI()

@fastapi_app.get('/plaintext')
async def fastapi_plaintext():
    return PlainTextResponse('Hello, World!')

@fastapi_app.get('/json')
async def fastapi_json():
    return {'message': 'Hello, World!'}

async def starlette_plaintext(request):
    return PlainTextResponse('Hello, World!')

async def starlette_json(request):
    return JSONResponse({'message': 'Hello, World!'})

starlette_app = Starlette(routes=[Route('/plaintext', starlette_plaintext), Route('/json', starlette_json)])
