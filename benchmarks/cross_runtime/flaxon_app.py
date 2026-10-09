"""One-worker, no optional middleware benchmark application."""
from flaxon import Flaxon
from flaxon.http import TextResponse
app = Flaxon('benchmark', debug=False)
@app.get('/plaintext')
async def plaintext():
    return TextResponse('Hello, World!')
@app.get('/json')
async def json_response():
    return {'message': 'Hello, World!'}
