# Request performance and authentication migration

Flaxon keeps security headers and request IDs enabled. Public HTTP handlers
no longer allocate a stored session or emit a session cookie automatically.

## Sessions

`request.session` remains a synchronous mapping. A request without a valid
cookie creates an unsaved session on first access. Setting, updating, clearing,
regenerating or deleting values makes it dirty; Flaxon saves the dirty session
and sends its signed cookie at response time. Reading an empty session does not
create server-side state. Existing signed cookies are verified and loaded before
the handler, preserving synchronous access to database/Redis session data.
This is lazy creation, not lazy asynchronous loading of existing sessions.

```python
@app.get('/public')
async def public():
    return {'message': 'No session cookie needed'}

@app.post('/preferences')
async def preferences(request):
    request.session['theme'] = 'dark'
    return {'saved': True}
```

Directly constructed session cookie managers default to Secure, HttpOnly and
SameSite=Lax. `Flaxon(debug=True)` explicitly permits HTTP development cookies;
production uses Secure cookies. Do not enable debug to work around production
HTTPS configuration. Application-owned cookies still need explicit secure flags.

Reads do not refresh expiry. Nested mutable values must be reassigned to the
session mapping after editing so the dirty flag is set. Keep session regeneration
on login and revocation on logout. CSRF protection remains required for mutations.

## Typed query parameters

```python
@app.get('/items/<int:item_id>')
async def items(item_id: int, verbose: bool = False, n: int = 0):
    return {'id': item_id, 'verbose': verbose, 'n': n}
```

`/items/1?verbose=true&n=3` returns converted values. `?n=abc` and
`?verbose=maybe` return 422. A scalar without a default is required. Optional
scalars need an explicit `None` default to be optional. Supported inferred types
are str, int, float and bool, including optional versions of those types.
Unannotated parameters with defaults still use their defaults. For collections,
aliases or constraints, declare an explicit `Query(...)` or parse deliberately.

Resolution order is path values, reserved request/socket arguments, registered
container dependencies, explicit Query, inferred scalar query, then body schemas
and ordinary defaults. Existing container values stay dynamic per request.
OpenAPI includes inferred queries. This is a behavior change: URLs that supplied
previously ignored scalar parameters may now change the result or return 422.

Endpoint signatures and type hints are prepared at registration. Define model
classes before registering handlers. Replace/re-register an endpoint instead of
mutating its annotations after registration.

## JWT migration

Flaxon JWT and JWTBackend now use PyJWT. Algorithms are explicitly configured
HS256, HS384 or HS512; an untrusted header cannot change the algorithm. Expiration
is required. Use at least 32 random bytes for HS256, 48 for HS384 and 64 for HS512.
Configure issuer and audience for tokens shared with another service.

```python
from flaxon.security import JWT

tokens = JWT(settings.SECRET_KEY, issuer='project-manager', audience='project-api',
             key_id='2026-10', verification_keys={'2026-09': previous_secret})
token = tokens.encode({'user_id': '42'})
claims = tokens.decode(token)
```

Only explicitly configured keys can be selected by kid. Unknown key IDs fail.
Keep old keys only for the intended rotation period. Never fetch a key from a
URL supplied in a token. Without kid, the configured signing key is used.

Old Flaxon tokens used hexadecimal HMAC signatures and are intentionally rejected.
Deploy the producer and consumer together and have users sign in again. There is
no automatic insecure legacy-token fallback. JWTBackend token revocation is local
to its instance; multiple workers require a shared revocation implementation or
short-lived tokens and centrally managed refresh tokens.

## Password migration

New framework hashes use Argon2id with 19 MiB memory, time cost 2 and parallelism 1.
argon2-cffi and PyJWT are core dependencies. Legacy PBKDF2-SHA256 hashes still verify.
Admin upgrades a legacy password hash after successful verification, and preserves
it after a failed attempt. Applications using the standalone helpers must save
upgrades themselves:

```python
from flaxon.security import hash_password, verify_password, needs_rehash

if verify_password(password, user.password_hash):
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        await user.save(update_fields=['password_hash'])
```

Explicit PBKDF2 remains available with a default 600,000 iterations. Benchmark
hashing on deployment hardware; do not reduce cost just to improve HTTP benchmark
scores. Hashing is synchronous: async handlers should offload expensive hashing
to a bounded worker pool and rate-limit authentication requests. The full-stack
course already uses Argon2 and application-owned ORM sessions; its customer login
flow does not need conversion to the framework session or JWT system.

## Exceptions and checks

Unexpected authentication and permission errors now propagate instead of being
silently treated as an ordinary denial. Optional plugin and callback failures
remain isolated but emit warnings without logging submitted payloads. Database
initialization cleanup re-raises the original error.

The mypy platform setting is corrected. Repository-wide typing and style debt is
recorded in the benchmark audit; do not confuse passing critical lint checks with
a completely lint-clean or fully typed repository.

## Application performance

Use persistent database connections, index actual filter/order columns, avoid
queries inside loops, paginate lists, and measure query counts. Keep ownership
filters on every data query. Cache public or correctly scoped data with explicit
expiry and invalidation; do not cache one user's response under a shared key.
Move blocking I/O off the event loop. Run multiple workers only after sharing
sessions, rate limits, task coordination and WebSocket fan-out appropriately.
MinifyJS changes browser assets; it does not accelerate Python API handlers.
