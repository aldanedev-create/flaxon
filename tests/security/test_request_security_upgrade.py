"""Compatibility and failure boundaries for request and authentication upgrades."""
import asyncio
import gzip
import time
from contextlib import closing
from unittest.mock import patch

import jwt
import pytest

from flaxon import Flaxon
from flaxon.admin.services import AdminAuth
from flaxon.exceptions import Unauthorized
from flaxon.middleware.compression import CompressionMiddleware
from flaxon.security import JWT, JWTBackend, PasswordHasher, User
from flaxon.testing import TestClient

SECRET = 'a' * 64


def test_public_requests_do_not_allocate_sessions_and_mutations_persist():
    app = Flaxon('lazy', debug=True)
    @app.get('/public')
    async def public():
        return {'ok': True}
    @app.get('/read')
    async def read(request):
        return {'count': request.session.get('count', 0)}
    @app.post('/write')
    async def write(request):
        request.session['count'] = request.session.get('count', 0) + 1
        return {'count': request.session['count']}
    with closing(TestClient(app)) as client:
        for _ in range(3):
            assert 'set-cookie' not in client.get('/public').headers
        assert not app.sessions.backend._sessions
        assert 'set-cookie' not in client.get('/read').headers
        assert not app.sessions.backend._sessions
        written = client.post('/write')
        assert written.json() == {'count': 1}
        cookie = written.headers['set-cookie'].split(';')[0]
        response = client.get('/read', headers={'cookie': cookie})
        assert response.json() == {'count': 1}
        assert 'set-cookie' not in response.headers
        assert client.post('/write', headers={'cookie': cookie}).json() == {'count': 2}
        assert len(app.sessions.backend._sessions) == 1


def test_typed_queries_and_cached_metadata():
    app = Flaxon('query')
    @app.get('/items/<int:item_id>')
    async def items(item_id: int, verbose: bool = False, n: int = 0, search: str | None = None):
        return {'id': item_id, 'verbose': verbose, 'n': n, 'search': search}
    with closing(TestClient(app)) as client:
        with patch('inspect.signature', side_effect=AssertionError('Request inspected endpoint')):
            assert client.get('/items/1?verbose=true&n=3&search=hello').json() == {
                'id': 1, 'verbose': True, 'n': 3, 'search': 'hello'}
            assert client.get('/items/1?n=abc').status_code == 422
            assert client.get('/items/1?verbose=maybe').status_code == 422
            assert client.get('/items/1').json()['n'] == 0


def test_dependency_values_are_not_cached():
    app = Flaxon('dependencies')
    values = iter([10, 20])
    app.container.register_factory('value', lambda: next(values))
    @app.get('/')
    async def home(value: int):
        return {'value': value}
    with closing(TestClient(app)) as client:
        assert client.get('/').json()['value'] == 10
        assert client.get('/').json()['value'] == 20


def test_standard_jwt_interoperability_and_registered_claims():
    token_manager = JWT(SECRET, issuer='flaxon', audience='api', key_id='current')
    token = token_manager.encode({'user_id': 1})
    assert jwt.decode(token, SECRET, algorithms=['HS256'], issuer='flaxon', audience='api')['user_id'] == 1
    external = jwt.encode({'exp': time.time() + 60, 'iss': 'flaxon', 'aud': 'api'}, SECRET, algorithm='HS256')
    assert token_manager.decode(external)['iss'] == 'flaxon'
    for claims in [{'exp': time.time() + 60}, {'exp': time.time() + 60, 'iss': 'wrong', 'aud': 'api'},
                   {'exp': time.time() + 60, 'iss': 'flaxon', 'aud': 'wrong'}]:
        with pytest.raises(Unauthorized):
            token_manager.decode(jwt.encode(claims, SECRET, algorithm='HS256'))
    with pytest.raises(Unauthorized):
        token_manager.decode(jwt.encode({'exp': time.time() + 60}, SECRET, algorithm='HS512'))
    with pytest.raises(Unauthorized):
        token_manager.decode(jwt.encode({'exp': time.time() + 60}, SECRET, algorithm='HS256', headers={'kid': 'untrusted'}))


def test_jwt_rotation_and_local_revocation():
    manager = JWT(SECRET, key_id='current', verification_keys={'old': 'b' * 64})
    old = jwt.encode({'exp': time.time() + 60}, 'b' * 64, algorithm='HS256', headers={'kid': 'old'})
    assert manager.decode(old)['exp'] > time.time()
    async def scenario():
        backend = JWTBackend(SECRET)
        token = await backend.create_token(User(1))
        assert await backend.validate_token(token)
        await backend.revoke_token(token)
        assert await backend.validate_token(token) is None
    asyncio.run(scenario())


def test_admin_legacy_password_is_upgraded_on_success_only():
    legacy = PasswordHasher(algorithm='pbkdf2_sha256', iterations=100000).hash('Password1!')
    auth = AdminAuth([{'username': 'owner', 'password_hash': legacy}])
    assert not auth.verify('owner', 'wrong')
    assert auth.users['owner']['password_hash'] == legacy
    assert auth.verify('owner', 'Password1!')
    upgraded = auth.users['owner']['password_hash']
    assert upgraded.startswith('$argon2id$')
    assert auth.hasher.verify('Password1!', upgraded)
    assert not auth.hasher.needs_rehash(upgraded)


def test_compression_emits_one_start_and_preserves_chunked_body():
    async def scenario():
        body = b'hello' * 100
        async def app(scope, receive, send):
            await send({'type': 'http.response.start', 'status': 200,
                        'headers': [(b'content-type', b'text/plain'), (b'content-length', str(len(body)).encode())]})
            await send({'type': 'http.response.body', 'body': body[:250], 'more_body': True})
            await send({'type': 'http.response.body', 'body': body[250:], 'more_body': False})
        messages = []
        async def send(message):
            messages.append(message)
        await CompressionMiddleware(app, minimum_size=10)({'type': 'http', 'method': 'GET', 'headers': [(b'accept-encoding', b'gzip')]}, None, send)
        assert [m['type'] for m in messages] == ['http.response.start', 'http.response.body']
        assert gzip.decompress(messages[1]['body']) == body
    asyncio.run(scenario())
