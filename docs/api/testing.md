# Testing API

## TestClient

Synchronous test client.

### Constructor

```python
TestClient(app: Any, base_url: str = "http://testserver")
```

## Methods

### get

```python
def get(path: str, **kwargs: Any) -> TestResponse
```

Send a GET request.

### post

```python
def post(path: str, **kwargs: Any) -> TestResponse
```

Send a POST request.

### put

```python
def put(path: str, **kwargs: Any) -> TestResponse
```

Send a PUT request.

### patch

```python
def patch(path: str, **kwargs: Any) -> TestResponse
```

Send a PATCH request.

### delete

```python
def delete(path: str, **kwargs: Any) -> TestResponse
```

Send a DELETE request.

### options

```python
def options(path: str, **kwargs: Any) -> TestResponse
```

Send an OPTIONS request.

### head

```python
def head(path: str, **kwargs: Any) -> TestResponse
```

Send a HEAD request.

### request

```python
def request(method: str, path: str, **kwargs: Any) -> TestResponse
```

Send a custom request.

---

# AsyncTestClient

Asynchronous test client.

## Constructor

```python
AsyncTestClient(app: Any, base_url: str = "http://testserver")
```

## Methods

### get

```python
async def get(path: str, **kwargs: Any) -> TestResponse
```

Send a GET request.

### post

```python
async def post(path: str, **kwargs: Any) -> TestResponse
```

Send a POST request.

### put

```python
async def put(path: str, **kwargs: Any) -> TestResponse
```

Send a PUT request.

### patch

```python
async def patch(path: str, **kwargs: Any) -> TestResponse
```

Send a PATCH request.

### delete

```python
async def delete(path: str, **kwargs: Any) -> TestResponse
```

Send a DELETE request.

### options

```python
async def options(path: str, **kwargs: Any) -> TestResponse
```

Send an OPTIONS request.

### head

```python
async def head(path: str, **kwargs: Any) -> TestResponse
```

Send a HEAD request.

### request

```python
async def request(method: str, path: str, **kwargs: Any) -> TestResponse
```

Send a custom request.

---

# WebSocketClient

Synchronous WebSocket client.

## Constructor

```python
WebSocketClient(app: Any, base_url: str = "ws://testserver")
```

## Methods

### connect

```python
async def connect(
    path: str,
    headers: dict[str, str] | None = None
) -> None
```

Connect to a WebSocket endpoint.

### disconnect

```python
async def disconnect(code: int = 1000) -> None
```

Disconnect from the WebSocket.

### send_text

```python
async def send_text(text: str) -> None
```

Send a text message.

### send_bytes

```python
async def send_bytes(data: bytes) -> None
```

Send binary data.

### send_json

```python
async def send_json(data: Any) -> None
```

Send JSON data.

### receive_text

```python
async def receive_text() -> str
```

Receive a text message.

### receive_json

```python
async def receive_json() -> Any
```

Receive JSON data.

---

# TestResponse

Test response object.

## Attributes

| Attribute | Type | Description |
|---|---|---|
| status_code | int | HTTP status code |
| headers | dict[str, str] | Response headers |
| content | bytes | Response content |

## Properties

### text

```python
@property
def text(self) -> str
```

Get response as text.

### json

```python
def json(self) -> Any
```

Get response as JSON.

---

# Assertions

Test assertion helpers.

## assert_status

```python
@staticmethod
def assert_status(response: Any, expected: int) -> None
```

Assert HTTP status code.

## assert_json

```python
@staticmethod
def assert_json(response: Any) -> dict[str, Any]
```

Assert response is JSON.

## assert_json_array

```python
@staticmethod
def assert_json_array(response: Any) -> list[Any]
```

Assert response is a JSON array.

## assert_has_key

```python
@staticmethod
def assert_has_key(data: dict[str, Any], key: str) -> None
```

Assert dictionary contains a key.

## assert_key_value

```python
@staticmethod
def assert_key_value(
    data: dict[str, Any],
    key: str,
    expected: Any
) -> None
```

Assert key has expected value.

## assert_success

```python
@staticmethod
def assert_success(data: dict[str, Any]) -> None
```

Assert success response.

## assert_error

```python
@staticmethod
def assert_error(data: dict[str, Any]) -> None
```

Assert error response.

## assert_error_code

```python
@staticmethod
def assert_error_code(data: dict[str, Any], code: str) -> None
```

Assert error code.

## assert_validation_error

```python
@staticmethod
def assert_validation_error(
    data: dict[str, Any],
    field: str | None = None
) -> None
```

Assert validation error.

## assert_redirect

```python
@staticmethod
def assert_redirect(
    response: Any,
    expected_location: str | None = None
) -> None
```

Assert redirect response.

## assert_header

```python
@staticmethod
def assert_header(
    response: Any,
    key: str,
    expected: str | None = None
) -> None
```

Assert header exists and matches.

---

# Fixture

Test fixture.

## Constructor

```python
Fixture(
    name: str,
    setup: Callable,
    teardown: Callable | None = None
)
```

## Methods

### load

```python
async def load() -> Any
```

Load fixture.

### unload

```python
async def unload() -> None
```

Unload fixture.

---

# FixtureLoader

Fixture loader.

## Methods

### register

```python
def register(fixture: Fixture) -> None
```

Register fixture.

### get

```python
def get(name: str) -> Fixture | None
```

Get fixture.

### load

```python
async def load(name: str) -> Any
```

Load fixture.

### load_all

```python
async def load_all() -> dict[str, Any]
```

Load all fixtures.

### unload

```python
async def unload(name: str) -> None
```

Unload fixture.

### unload_all

```python
async def unload_all() -> None
```

Unload all fixtures.

### clear

```python
def clear() -> None
```

Clear all fixtures.

---

# Factory

Test data factory.

## Methods

### sequence

```python
def sequence(name: str) -> int
```

Generate a sequence number.

### random_string

```python
def random_string(length: int = 10) -> str
```

Generate a random string.

### random_email

```python
def random_email() -> str
```

Generate a random email.

### random_int

```python
def random_int(min: int = 0, max: int = 100) -> int
```

Generate a random integer.

### random_float

```python
def random_float(
    min: float = 0.0,
    max: float = 100.0
) -> float
```

Generate a random float.

### random_bool

```python
def random_bool() -> bool
```

Generate a random boolean.

### random_uuid

```python
def random_uuid() -> str
```

Generate a random UUID.

### build

```python
def build(**kwargs: Any) -> dict[str, Any]
```

Build an object.

### create

```python
def create(**kwargs: Any) -> dict[str, Any]
```

Create and save an object.

---

# DatabaseTestMixin

Database testing helpers.

## Methods

### setup_database

```python
async def setup_database() -> None
```

Set up the test database.

### teardown_database

```python
async def teardown_database() -> None
```

Tear down the test database.

### clear_database

```python
async def clear_database() -> None
```

Clear the test database.

### transaction

```python
async def transaction() -> Any
```

Start a test transaction.
## Use this capability in a full-stack app

Flaxon serves Python APIs and Teloce interfaces in one project. Keep validation,
authorization and privileged operations on the server; components call those
endpoints and present their results. Follow the [full-stack lessons](../fullstack/index.md)
and [Teloce integration reference](../api/teloce.md) to connect this capability
to pages, components and application modules.
