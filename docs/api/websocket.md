
# WebSocket API

## WebSocket

WebSocket connection handler.

### Constructor

```python
WebSocket(
    scope: dict[str, Any],
    receive: Any,
    send: Any,
    manager: Any = None
)
````

### Properties

| Property      | Type             | Description                              |
| ------------- | ---------------- | ---------------------------------------- |
| `path_params` | `dict[str, Any]` | Path parameters                          |
| `state`       | `WebSocketState` | Connection state                         |
| `accepted`    | `bool`           | Whether the connection has been accepted |
| `closed`      | `bool`           | Whether the connection has been closed   |

---

## Methods

### accept

```python
async def accept(
    subprotocol: str | None = None,
    headers: list[tuple[bytes, bytes]] | None = None
) -> None
```

Accept the WebSocket connection.

---

### receive

```python
async def receive() -> dict[str, Any]
```

Receive a WebSocket message.

---

### receive_text

```python
async def receive_text() -> str
```

Receive a text message.

---

### receive_bytes

```python
async def receive_bytes() -> bytes
```

Receive a binary message.

---

### receive_json

```python
async def receive_json() -> Any
```

Receive a JSON message.

---

### send_text

```python
async def send_text(value: str) -> None
```

Send a text message.

---

### send_bytes

```python
async def send_bytes(value: bytes) -> None
```

Send a binary message.

---

### send_json

```python
async def send_json(value: Any) -> None
```

Send a JSON message.

---

### close

```python
async def close(code: int = 1000, reason: str = "") -> None
```

Close the WebSocket connection.

---

### join

```python
async def join(room: str) -> None
```

Join a room.

---

### leave

```python
async def leave(room: str) -> None
```

Leave a room.

---

### broadcast_json

```python
async def broadcast_json(room: str, value: Any) -> None
```

Broadcast JSON data to all connections in a room.

---

### broadcast_text

```python
async def broadcast_text(room: str, value: str) -> None
```

Broadcast text data to all connections in a room.

---

### iter_json

```python
def iter_json(self) -> AsyncIterator[Any]
```

Iterate over incoming JSON messages.

---

### iter_text

```python
def iter_text(self) -> AsyncIterator[str]
```

Iterate over incoming text messages.

---

# WebSocketManager

WebSocket connection manager for handling rooms and connected clients.

## Methods

### join

```python
async def join(room: str, socket: WebSocket) -> None
```

Add a connection to a room.

---

### leave

```python
async def leave(room: str, socket: WebSocket) -> None
```

Remove a connection from a room.

---

### leave_all

```python
async def leave_all(socket: WebSocket) -> None
```

Remove a connection from all rooms.

---

### broadcast_text

```python
async def broadcast_text(room: str, message: str) -> None
```

Broadcast a text message.

---

### broadcast_json

```python
async def broadcast_json(room: str, data: Any) -> None
```

Broadcast JSON data.

---

### broadcast_bytes

```python
async def broadcast_bytes(room: str, data: bytes) -> None
```

Broadcast binary data.

---

### get_room_size

```python
def get_room_size(room: str) -> int
```

Get the number of connections in a room.

---

### get_rooms

```python
def get_rooms() -> list[str]
```

Get all room names.

---

### get_connection_rooms

```python
def get_connection_rooms(socket: WebSocket) -> list[str]
```

Get all rooms a connection belongs to.

---

### clear

```python
def clear() -> None
```

Clear all rooms and connections.

---

# WebSocketDisconnect

WebSocket disconnect exception.

## Constructor

```python
WebSocketDisconnect(
    code: int = 1000,
    reason: str = ""
)
```

## Attributes

| Attribute | Type  | Description  |
| --------- | ----- | ------------ |
| `code`    | `int` | Close code   |
| `reason`  | `str` | Close reason |

---

# WebSocketState

WebSocket connection states.

| Value        | Description |
| ------------ | ----------- |
| `CONNECTING` | Connecting  |
| `CONNECTED`  | Connected   |
| `CLOSING`    | Closing     |
| `CLOSED`     | Closed      |

````

---

# Validation API

## Schema

Base schema class for data validation.

## Class Methods

### load

```python
@classmethod
def load(cls, data: Any) -> Schema
````

Load and validate data.

---

## Methods

### to_dict

```python
def to_dict(self) -> dict[str, Any]
```

Convert schema data into a dictionary.

---

### to_json

```python
def to_json(self) -> dict[str, Any]
```

Convert schema data into a JSON-serializable dictionary.

---

### validate

```python
def validate(self) -> None
```

Validate schema data.

---

# Fields

## StrField

String validation field.

```python
StrField(
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False,
    min_length: int | None = None,
    max_length: int | None = None,
    strip: bool = True,
    pattern: str | None = None
)
```

---

## IntField

Integer validation field.

```python
IntField(
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False,
    minimum: int | None = None,
    maximum: int | None = None
)
```

---

## FloatField

Float validation field.

```python
FloatField(
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False,
    minimum: float | None = None,
    maximum: float | None = None
)
```

---

## BoolField

Boolean validation field.

```python
BoolField(
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False
)
```

---

## ChoiceField

Choice validation field.

```python
ChoiceField(
    choices: list[Any] | tuple[Any, ...] | set[Any],
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False
)
```

---

## EmailField

Email validation field.

```python
EmailField(
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False,
    min_length: int | None = None,
    max_length: int | None = None
)
```

---

## DateField

Date validation field.

```python
DateField(
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False,
    format: str = "%Y-%m-%d"
)
```

---

## DateTimeField

DateTime validation field.

```python
DateTimeField(
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False,
    format: str = "%Y-%m-%dT%H:%M:%S"
)
```

---

## DecimalField

Decimal validation field.

```python
DecimalField(
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False,
    minimum: Decimal | None = None,
    maximum: Decimal | None = None,
    places: int | None = None
)
```

---

## UUIDField

UUID validation field.

```python
UUIDField(
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False
)
```

---

## ListField

List validation field.

```python
ListField(
    item_field: Field | None = None,
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False,
    min_items: int | None = None,
    max_items: int | None = None
)
```

---

## NestedField

Nested schema validation field.

```python
NestedField(
    schema_class: type[Schema],
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False
)
```

---

## AnyField

Accepts any value.

```python
AnyField(
    *,
    required: bool = False,
    default: Any = None,
    nullable: bool = False
)
```

---

# Validators

## required_validator

```python
required_validator(
    value: Any,
    field: Any,
    message: str | None = None
) -> None
```

---

## length_validator

```python
length_validator(
    min_length: int | None = None,
    max_length: int | None = None
) -> Validator
```

---

## min_validator

```python
min_validator(min_value: Any) -> Validator
```

---

## max_validator

```python
max_validator(max_value: Any) -> Validator
```

---

## range_validator

```python
range_validator(
    min_value: Any,
    max_value: Any
) -> Validator
```

---

## email_validator

```python
email_validator() -> Validator
```

---

## url_validator

```python
url_validator() -> Validator
```

---

## pattern_validator

```python
pattern_validator(pattern: str) -> Validator
```

---

## and_validators

```python
and_validators(*validators: Validator) -> Validator
```

Combine validators using AND logic.

---

## or_validators

```python
or_validators(*validators: Validator) -> Validator
```

Combine validators using OR logic.

---

## custom_validator

```python
custom_validator(
    func: Callable[[Any, Any], None]
) -> Validator
```

Create a custom validator.

---

# Exceptions

## ValidationError

```python
ValidationError(fields: dict[str, list[str]])
```

Raised when validation fails.

---

## FieldError

```python
FieldError(message: str)
```

Raised when a field validation fails.

## Use this capability in a full-stack app

Flaxon serves Python APIs and Teloce interfaces in one project. Keep validation,
authorization and privileged operations on the server; components call those
endpoints and present their results. Follow the [full-stack lessons](../fullstack/index.md)
and [Teloce integration reference](../api/teloce.md) to connect this capability
to pages, components and application modules.
