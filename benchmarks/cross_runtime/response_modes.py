"""Compare complete ASGI dispatch with modern and legacy JSON on identical data."""
import asyncio
import json
import statistics
import time
from flaxon import Flaxon

async def measure(mode, payload, count):
    app = Flaxon('serialization-benchmark', debug=False, config={'JSON_SERIALIZER': mode})
    @app.get('/json')
    async def endpoint():
        return payload
    async def receive():
        return {'type': 'http.request', 'body': b''}
    async def send(message):
        if message['type'] == 'http.response.body':
            assert message['body']
    scope = {'type': 'http', 'method': 'GET', 'path': '/json', 'headers': [], 'query_string': b''}
    for _ in range(100):
        await app(scope, receive, send)
    start = time.perf_counter()
    for _ in range(count):
        await app(scope, receive, send)
    return count / (time.perf_counter() - start)

async def main():
    result = []
    for name, payload, count in [('small', {'ok': True, 'message': 'hello'}, 10000),
                                 ('1000 rows', [{'id': i, 'name': f'Task {i}', 'done': False} for i in range(1000)], 500)]:
        samples = {'modern': [], 'legacy': []}
        for repeat in range(5):
            for mode in (('modern', 'legacy') if repeat % 2 else ('legacy', 'modern')):
                samples[mode].append(await measure(mode, payload, count))
        result.append({'payload': name, 'samples_rps': samples,
                       'median_rps': {mode: statistics.median(values) for mode, values in samples.items()}})
    print(json.dumps({'method': 'Five alternating repeats, complete in-process ASGI dispatch; no network', 'results': result}, indent=2))

asyncio.run(main())
