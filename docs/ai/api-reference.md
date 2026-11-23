# Flaxon public API reference (0.3.2)

Generated from each module's `__all__`, signatures and docstrings by
`scripts/generate_ai_docs.py`. Do not edit by hand.

## `flaxon`

- `Config(values: collections.abc.Mapping[str, typing.Any] | None = None, *, prefix: str = FLAXON_) -> None` — Configuration container with environment variable support.
- `ConfigurationError` — Raised for invalid framework configuration.
- `Flaxon(name: str, *, debug: bool | None = None, config: dict[str, typing.Any] | None = None, openapi: bool | dict[str, typing.Any] = False) -> None` — An async-first ASGI application with route and middleware support.
- `FlaxonError` — Base class for framework errors.
- `HTMLResponse(content: bytes | str = b, status_code: int = 200, headers: dict[str, str] | None = None, media_type: str | None = None) -> None` — An HTML response.
- `HTTPException(status_code: int, detail: str | None = None, *, code: str | None = None, extra: dict[str, typing.Any] | None = None) -> None` — An exception that can be rendered as an HTTP response.
- `JSONResponse(content: Any, status_code: int = 200, headers: dict[str, str] | None = None, *, legacy: bool = False) -> None` — A JSON response.
- `LegacyJSONResponse(content: Any, status_code: int = 200, headers: dict[str, str] | None = None) -> None` — Explicit historical JSON encoding for migrating existing clients.
- `MethodNotAllowed(detail: str = Method not allowed) -> None` — Raised when a route exists but does not accept the method.
- `NotFound(detail: str = Not found) -> None` — Raised when no route matches a request.
- `Query(default: Any = <sentinel>, alias: str | None = None, description: str | None = None, ge: int | float | None = None, le: int | float | None = None, min_length: int | None = None, max_length: int | None = None, deprecated: bool = False) -> None` — Declare a query-string parameter.
- `RedirectResponse(url: str, status_code: int = 307, headers: dict[str, str] | None = None) -> None` — A redirect response.
- `Request(scope: dict[str, typing.Any], receive: Any, app: Any = None) -> None` — Expose an ASGI HTTP request through a small, async-friendly API.
- `Response(content: bytes | str = b, status_code: int = 200, headers: dict[str, str] | None = None, media_type: str | None = None) -> None` — An HTTP response that can be sent directly as an ASGI application.
- `Router(prefix: str = ) -> None` — Register routes and resolve them by request path and method.
- `State(**kwargs: Any) -> None` — Application state container.
- `StreamingResponse(content: collections.abc.AsyncIterable[bytes] | collections.abc.Iterable[bytes], status_code: int = 200, headers: dict[str, str] | None = None, media_type: str | None = None) -> None` — A response that streams an iterable of byte chunks.
- `Teloce(app: Any, *, ui_dir: str | pathlib.Path = ui, project_root: str | pathlib.Path | None = None, build_dir: str | pathlib.Path = .flaxon/build, static_url: str = /_flaxon, entry: str = app.html, title: str | None = None, favicon: str | None = None, description: str | None = None, lang: str = en, theme_color: str | None = None, stylesheets: list[str | dict[str, typing.Any]] | None = None, scripts: list[str | dict[str, typing.Any]] | None = None, options: dict[str, typing.Any] | None = None, plugins: dict[str, typing.Any] | None = None, typecheck: bool = False, editor: str | None = vscode, editor_remote: str | None = None, editor_path_map: dict[str, str] | None = None, editor_configured: bool = False) -> None` — Compile and serve one Teloce SPA from application and module sources.
- `TextResponse(content: bytes | str = b, status_code: int = 200, headers: dict[str, str] | None = None, media_type: str | None = None) -> None` — A text response.
- `WebSocket(scope: dict[str, typing.Any], receive: Any, send: Any, manager: Any = None) -> None` — A convenient interface over ASGI WebSocket messages.
- `WebSocketDisconnect(code: int = 1005, reason: str = ) -> None` — Raised when a peer disconnects, or when sending to a connection that is already closed.
- `WebSocketManager(broadcaster: typing.Any | None = None, *, send_timeout: float | None = 10.0, max_connections: int | None = None) -> None` — Track connections and broadcast rooms for an application.
- `__version__` = `0.3.2`
- `__version_info__` — Built-in immutable sequence.
- `version` = `0.3.2`
- `version_info` — Built-in immutable sequence.

## `flaxon.routing`

- `CONVERTERS` — dict() -> new empty dictionary dict(mapping) -> new dictionary initialized from a mapping object's (key, value) pairs dict(iterable) -> new dictionary initialized as if via: d = {} for k, v in iterable: d[k] = v dict(**kwargs) -> new dictionary initialized with the name=value pairs in the keyword argument list. For example: dict(one=1, two=2)
- `Converter(regex: str, cast: collections.abc.Callable[[str], typing.Any]) -> None` — Route parameter converter.
- `MISSING` — The base class of the class hierarchy.
- `Mount(path: str, app: Any, *, name: str | None = None, middleware: list[type] | None = None) -> None` — Mount a sub-application or router at a specific path.
- `Query(default: Any = <sentinel>, alias: str | None = None, description: str | None = None, ge: int | float | None = None, le: int | float | None = None, min_length: int | None = None, max_length: int | None = None, deprecated: bool = False) -> None` — Declare a query-string parameter.
- `Route(path: str, endpoint: collections.abc.Callable[..., typing.Any], methods: set[str], name: str | None = None, registration_order: int = 0, summary: str | None = None, description: str | None = None, tags: list[str] | None = None, operation_id: str | None = None, responses: dict[str | int, typing.Any] | None = None, deprecated: bool = False, security: list[dict[str, list[str]]] | None = None) -> None` — A registered HTTP route.
- `Router(prefix: str = ) -> None` — Register routes and resolve them by request path and method.
- `WebSocketRoute(path: str, endpoint: collections.abc.Callable[..., typing.Any], name: str | None = None) -> None` — A registered WebSocket route.
- `compile_path(path: str) -> tuple[re.Pattern[str], list[tuple[str, str]]]` — Compile a Flaxon path template into a matching regular expression.
- `get_converter(name: str) -> flaxon.routing.converters.Converter` — Get a converter by name.
- `mount(path: str, app: Any, *, name: str | None = None) -> flaxon.routing.mount.Mount` — Convenience function for mounting an application.
- `register_converter(name: str, converter: flaxon.routing.converters.Converter) -> None` — Register a custom converter.

## `flaxon.http`

- `Cookies(data: dict[str, str] | None = None) -> None` — Dictionary-like request cookies with response cookie metadata.
- `HTMLResponse(content: bytes | str = b, status_code: int = 200, headers: dict[str, str] | None = None, media_type: str | None = None) -> None` — An HTML response.
- `Headers(headers: dict[str, str] | list[tuple[bytes, bytes]] | None = None) -> None` — A case-insensitive mapping for HTTP headers.
- `JSONResponse(content: Any, status_code: int = 200, headers: dict[str, str] | None = None, *, legacy: bool = False) -> None` — A JSON response.
- `LegacyJSONResponse(content: Any, status_code: int = 200, headers: dict[str, str] | None = None) -> None` — Explicit historical JSON encoding for migrating existing clients.
- `QueryParams(value: bytes | str | collections.abc.Mapping[str, str] | None = None) -> None` — Read URL query parameters while retaining repeated values.
- `RedirectResponse(url: str, status_code: int = 307, headers: dict[str, str] | None = None) -> None` — A redirect response.
- `Request(scope: dict[str, typing.Any], receive: Any, app: Any = None) -> None` — Expose an ASGI HTTP request through a small, async-friendly API.
- `Response(content: bytes | str = b, status_code: int = 200, headers: dict[str, str] | None = None, media_type: str | None = None) -> None` — An HTTP response that can be sent directly as an ASGI application.
- `StreamingResponse(content: collections.abc.AsyncIterable[bytes] | collections.abc.Iterable[bytes], status_code: int = 200, headers: dict[str, str] | None = None, media_type: str | None = None) -> None` — A response that streams an iterable of byte chunks.
- `TextResponse(content: bytes | str = b, status_code: int = 200, headers: dict[str, str] | None = None, media_type: str | None = None) -> None` — A text response.

## `flaxon.validation`

- `AnyField(**kwargs: Any) -> None` — Validate and convert any field values.
- `BoolField(*, required: bool = False, default: Any = None, nullable: bool = False, validators: list[flaxon.validation.validators.Validator] | None = None, description: str | None = None, examples: list[typing.Any] | None = None) -> None` — Validate and convert bool field values.
- `ChoiceField(choices: list[typing.Any] | tuple[typing.Any, ...] | set[typing.Any], **kwargs: Any) -> None` — Validate and convert choice field values.
- `Coercer() -> None` — Coercer implementation for the validation subsystem.
- `CoercionError(message: str, *args: object) -> None` — Report a coercion failure.
- `DateField(format: str = %Y-%m-%d, **kwargs: Any) -> None` — Validate and convert date field values.
- `DateTimeField(format: str = %Y-%m-%dT%H:%M:%S, **kwargs: Any) -> None` — Validate and convert date time field values.
- `DecimalField(*, minimum: decimal.Decimal | None = None, maximum: decimal.Decimal | None = None, places: int | None = None, **kwargs: Any) -> None` — Validate and convert decimal field values.
- `EmailField(**kwargs: Any) -> None` — Validate and convert email field values.
- `Field(*, required: bool = False, default: Any = None, nullable: bool = False, validators: list[flaxon.validation.validators.Validator] | None = None, description: str | None = None, examples: list[typing.Any] | None = None) -> None` — Validate and convert field values.
- `FieldError(message: str, *args: object) -> None` — Report a field failure.
- `FloatField(*, minimum: float | None = None, maximum: float | None = None, **kwargs: Any) -> None` — Validate and convert float field values.
- `IntField(*, minimum: int | None = None, maximum: int | None = None, **kwargs: Any) -> None` — Validate and convert int field values.
- `ListField(item_field: flaxon.validation.fields.Field | None = None, *, min_items: int | None = None, max_items: int | None = None, **kwargs: Any) -> None` — Validate and convert list field values.
- `MessageMixin()` — Message mixin implementation for the validation subsystem.
- `NestedField` — Validate and convert nested field values.
- `Schema(**values: Any) -> None` — Schema implementation for the validation subsystem.
- `SchemaError(message: str, *args: object) -> None` — Report a schema failure.
- `SchemaMeta(name: str, bases: tuple[type, ...], namespace: dict[str, typing.Any]) -> type` — Schema meta implementation for the validation subsystem.
- `Serializer() -> None` — Serializer implementation for the validation subsystem.
- `SerializerMixin()` — Serializer mixin implementation for the validation subsystem.
- `StrField(*, min_length: int | None = None, max_length: int | None = None, strip: bool = True, pattern: str | None = None, **kwargs: Any) -> None` — Validate and convert str field values.
- `UUIDField(*, required: bool = False, default: Any = None, nullable: bool = False, validators: list[flaxon.validation.validators.Validator] | None = None, description: str | None = None, examples: list[typing.Any] | None = None) -> None` — Validate and convert uuid field values.
- `ValidationConfigurationError(message: str, *args: object) -> None` — Report a validation configuration failure.
- `ValidationError(fields: dict[str, list[str]]) -> None` — Report a validation failure.
- `ValidationMessages(custom_messages: dict[str, str] | None = None) -> None` — Validation messages implementation for the validation subsystem.
- `Validator(func: collections.abc.Callable[[typing.Any, typing.Any], None], message: str | None = None) -> None` — Validator implementation for the validation subsystem.
- `and_validators(*validators: flaxon.validation.validators.Validator) -> flaxon.validation.validators.Validator` — Perform the and validators operation for this subsystem.
- `coerce(value: Any, target_type: type[~T]) -> Optional[~T]` — Perform the coerce operation for this subsystem.
- `coerce_bool(value: Any) -> bool` — Coerce the bool.
- `coerce_date(value: Any) -> datetime.date` — Coerce the date.
- `coerce_datetime(value: Any) -> datetime.datetime` — Coerce the datetime.
- `coerce_decimal(value: Any) -> decimal.Decimal` — Coerce the decimal.
- `coerce_float(value: Any) -> float` — Coerce the float.
- `coerce_int(value: Any) -> int` — Coerce the int.
- `coerce_list(value: Any) -> list` — Coerce the list.
- `coerce_params(*types: type) -> collections.abc.Callable[[~F], ~F]` — Convert arguments using explicit types or function parameter annotations.
- `coerce_str(value: Any) -> str` — Coerce the str.
- `coerce_uuid(value: Any) -> uuid.UUID` — Coerce the uuid.
- `custom_validator(func: collections.abc.Callable[[typing.Any, typing.Any], None]) -> flaxon.validation.validators.Validator` — Build a validator for the configured custom constraint.
- `email_validator() -> flaxon.validation.validators.Validator` — Build a validator for the configured email constraint.
- `extend_messages(messages: dict[str, str]) -> None` — Perform the extend messages operation for this subsystem.
- `get_message(key: str, **kwargs: Any) -> str` — Return the message.
- `length_validator(min_length: int | None = None, max_length: int | None = None) -> flaxon.validation.validators.Validator` — Build a validator for the configured length constraint.
- `max_validator(max_value: Any) -> flaxon.validation.validators.Validator` — Build a validator for the configured max constraint.
- `min_validator(min_value: Any) -> flaxon.validation.validators.Validator` — Build a validator for the configured min constraint.
- `or_validators(*validators: flaxon.validation.validators.Validator) -> flaxon.validation.validators.Validator` — Perform the or validators operation for this subsystem.
- `pattern_validator(pattern: str) -> flaxon.validation.validators.Validator` — Build a validator for the configured pattern constraint.
- `range_validator(min_value: Any, max_value: Any) -> flaxon.validation.validators.Validator` — Build a validator for the configured range constraint.
- `register_serializer(type_: type, serializer: collections.abc.Callable[[typing.Any], typing.Any]) -> None` — Register the serializer.
- `required_validator(value: Any, field: Any, message: str | None = None) -> None` — Build a validator for the configured required constraint.
- `revalidate(func: ~F) -> ~F` — Perform the revalidate operation for this subsystem.
- `serialize(value: Any) -> Any` — Convert the supplied value into its serialized representation.
- `set_message(key: str, message: str) -> None` — Set the message.
- `to_json(value: Any) -> str` — Convert to the json.
- `to_json_pretty(value: Any, indent: int = 2) -> str` — Convert to the json pretty.
- `url_validator() -> flaxon.validation.validators.Validator` — Build a validator for the configured url constraint.
- `validate(schema_class: type[flaxon.validation.schema.Schema]) -> collections.abc.Callable[[~F], ~F]` — Check the supplied value against the configured constraints.
- `validate_body(schema_class: type[flaxon.validation.schema.Schema]) -> collections.abc.Callable[[~F], ~F]` — Validate the body.
- `validate_params(schema_class: type[flaxon.validation.schema.Schema]) -> collections.abc.Callable[[~F], ~F]` — Validate the params.
- `validate_query(schema_class: type[flaxon.validation.schema.Schema]) -> collections.abc.Callable[[~F], ~F]` — Validate the query.

## `flaxon.websocket`

- `Heartbeat(interval: int = 30, timeout: int = 60) -> None` — WebSocket heartbeat manager.
- `HeartbeatMiddleware(app: Any, interval: int = 30, timeout: int = 60) -> None` — Heartbeat middleware for WebSocket connections.
- `Message(type: flaxon.websocket.message.MessageType, data: Any = None, raw: Any = None) -> None` — WebSocket message.
- `MessageType(value, names=None, *, module=None, qualname=None, type=None, start=1, boundary=None)` — WebSocket message types.
- `WebSocket(scope: dict[str, typing.Any], receive: Any, send: Any, manager: Any = None) -> None` — A convenient interface over ASGI WebSocket messages.
- `WebSocketDataError(message: str, code: int = 1003) -> None` — Raised when a peer sends a frame the endpoint cannot accept.
- `WebSocketDisconnect(code: int = 1005, reason: str = ) -> None` — Raised when a peer disconnects, or when sending to a connection that is already closed.
- `WebSocketEvents(socket: flaxon.websocket.connection.WebSocket) -> None` — WebSocket events manager.
- `WebSocketManager(broadcaster: typing.Any | None = None, *, send_timeout: float | None = 10.0, max_connections: int | None = None) -> None` — Track connections and broadcast rooms for an application.
- `WebSocketOriginMiddleware(app: Any, allowed_origins: collections.abc.Iterable[str] = (), *, allow_same_origin: bool = True, allow_missing_origin: bool = True) -> None` — Reject WebSocket handshakes from origins you have not allowed.
- `WebSocketState(value, names=None, *, module=None, qualname=None, type=None, start=1, boundary=None)` — Connection lifecycle state.

## `flaxon.tasks`

- `RetryPolicy(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0, max_delay: float = 60.0, random_jitter: float = 0.1, retry_on: list[type[Exception]] | None = None) -> None` — Select retryable errors and calculate backoff delays with optional jitter.
- `Scheduler(queue: flaxon.tasks.queue.TaskQueue) -> None` — Enqueue tasks when their configured time or interval becomes due.
- `Serializer() -> None` — Convert task values and encode JSON or trusted pickle payloads.
- `Signal(value, names=None, *, module=None, qualname=None, type=None, start=1, boundary=None)` — Lifecycle events emitted by background tasks.
- `SignalHandler() -> None` — Dispatch task notifications without stopping subsequent listeners.
- `SignalManager() -> None` — Keep signal subscriptions isolated by task identifier.
- `Task(name: str, func: collections.abc.Callable, *, args: tuple[typing.Any, ...] = (), kwargs: dict[str, typing.Any] | None = None, retry_policy: flaxon.tasks.retry.RetryPolicy | None = None, timeout: int | None = None, queue: str = default, priority: int = 0) -> None` — Execute a callable while recording status, retries, results, and errors.
- `TaskContext(task_id: str | None = None, task_name: str | None = None) -> None` — Expose task identity and copy-on-write task-local values.
- `TaskError(message: str, *args: object) -> None` — Base exception for background task failures.
- `TaskExecutionError(message: str = Task execution error) -> None` — A task callable could not be executed successfully.
- `TaskNotFoundError(message: str = Task not found) -> None` — A required task or task result could not be found.
- `TaskQueue(name: str = default, max_size: int = 1000) -> None` — An in-process priority queue with task lookup and cancellation helpers.
- `TaskQueueError(message: str = Task queue error) -> None` — A task queue operation failed.
- `TaskRegistrationError(message: str = Task registration error) -> None` — A task could not be registered.
- `TaskRegistry() -> None` — Map task names to callables for worker resolution.
- `TaskResult(id: str, name: str, status: Any, result: Any = None, error: str | None = None, created_at: datetime.datetime | None = None, started_at: datetime.datetime | None = None, completed_at: datetime.datetime | None = None, retry_count: int = 0) -> None` — A task status, result, error, and timing snapshot.
- `TaskResultError(message: str = Task result error) -> None` — A task result operation failed.
- `TaskStatus(value, names=None, *, module=None, qualname=None, type=None, start=1, boundary=None)` — The lifecycle states recorded by a background task.
- `TaskTimeoutError(message: str = Task timed out) -> None` — A task exceeded its execution timeout.
- `Worker(registry: flaxon.tasks.registry.TaskRegistry, queue: flaxon.tasks.queue.TaskQueue | None = None, concurrency: int = 10, queue_name: str = default, graceful_shutdown_timeout: int = 30) -> None` — Consume queued tasks with bounded retry delays after backend failures.
- `connect_signal(task_id: str, signal: flaxon.tasks.signals.Signal, handler: collections.abc.Callable[..., typing.Any]) -> None` — Subscribe a listener through the default task signal manager.
- `deserialize(value: Any) -> Any` — Recursively decode container values using the registered conversions.
- `disconnect_signal(task_id: str, signal: flaxon.tasks.signals.Signal, handler: collections.abc.Callable[..., typing.Any]) -> None` — Remove a listener from the default task signal manager.
- `emit_signal(task_id: str, signal: flaxon.tasks.signals.Signal, *args: Any, **kwargs: Any) -> None` — Emit a notification through the default task signal manager.
- `from_json(data: str) -> Any` — Parse JSON and recursively deserialize its values.
- `from_pickle(data: bytes) -> Any` — Load a pickle payload; the input must come from a trusted source.
- `get_all_task_data() -> dict[str, typing.Any]` — Return a shallow copy of the active task context data.
- `get_current_task_id() -> str | None` — Return the task identifier in the active context, if any.
- `get_current_task_name() -> str | None` — Return the task name in the active context, if any.
- `get_task(name: str) -> collections.abc.Callable | None` — Return a callable from the default task registry, if present.
- `get_task_data(key: str, default: Any = None) -> Any` — Read a value from the active task context.
- `register_task(name: str, func: collections.abc.Callable) -> None` — Register a callable with the default task registry.
- `retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0, max_delay: float = 60.0, random_jitter: float = 0.1, retry_on: list[type[Exception]] | None = None) -> collections.abc.Callable` — Decorate a callable with asynchronous retry handling.
- `scheduled_task(interval: int | None = None, delay: int | None = None, at: datetime.datetime | None = None, queue: str = default) -> collections.abc.Callable` — Wrap an async callable; actual scheduling uses Scheduler.schedule.
- `serialize(value: Any) -> Any` — Recursively convert registered types and container values for storage.
- `set_task_data(key: str, value: Any) -> None` — Write a value to the active task context.
- `task(name: str | None = None, *, retry_policy: flaxon.tasks.retry.RetryPolicy | None = None, timeout: int | None = None, queue: str = default, priority: int = 0) -> collections.abc.Callable` — Decorate a callable to construct a configured Task object.
- `to_json(value: Any) -> str` — Serialize a value as a JSON string.
- `to_pickle(value: Any) -> bytes` — Encode a Python value using pickle for trusted internal storage.

## `flaxon.testing`

- `Assertions()` — Assertions implementation for the testing subsystem.
- `AsyncTestClient(app: Any, base_url: str = http://testserver) -> None` — Async test client implementation for the testing subsystem.
- `AsyncWebSocketClient(app: Any, base_url: str = ws://testserver) -> None` — Async web socket client implementation for the testing subsystem.
- `DatabaseTestMixin(db_manager: typing.Any | None = None) -> None` — Database test mixin implementation for the testing subsystem.
- `Factory() -> None` — Factory implementation for the testing subsystem.
- `Fixture(name: str, setup: collections.abc.Callable, teardown: collections.abc.Callable | None = None) -> None` — Fixture implementation for the testing subsystem.
- `FixtureLoader() -> None` — Fixture loader implementation for the testing subsystem.
- `Mock(name: str, return_value: Any = None) -> None` — Mock implementation for the testing subsystem.
- `MockRegistry() -> None` — Mock registry implementation for the testing subsystem.
- `TestApp(app: Any, config: dict[str, typing.Any] | None = None) -> None` — Test app implementation for the testing subsystem.
- `TestClient(app: Any, base_url: str = http://testserver) -> None` — Test client implementation for the testing subsystem.
- `WebSocketClient(app: Any, base_url: str = ws://testserver) -> None` — Web socket client implementation for the testing subsystem.

## `flaxon.db`

- `Database(app: Any, settings: Any) -> None` — One isolated database context per Flaxon application, never a global fallback.
- `Model(**kwargs: Any) -> None` — Base class for all Tortoise ORM Models.
- `atomic(connection_name: str | None = None) -> collections.abc.Callable[[~F], ~F]` — Transaction decorator.
- `fields` — module
- `in_transaction` — Transaction context manager.

## `flaxon.admin`

- `ADMIN_EXTENSION_GROUP` = `flaxon.admin`
- `ADMIN_SCHEMA_DOWN` = `
DROP TABLE IF EXISTS flaxon_cms_menus; DROP TABLE IF EXISTS flaxon_cms_comments; DROP TABLE IF EXISTS flaxon_cms_terms; DROP TABLE IF EXISTS flaxon_cms_taxonomies; DROP TABLE IF EXISTS flaxon_admin_operations; DROP TABLE IF EXISTS flaxon_admin_store; DROP TABLE IF EXISTS flaxon_admin_activity; DROP TABLE IF EXISTS flaxon_admin_settings; DROP TABLE IF EXISTS flaxon_admin_users;
`
- `ADMIN_SCHEMA_UP` = `
CREATE TABLE IF NOT EXISTS flaxon_admin_users (id VARCHAR(64) PRIMARY KEY, username VARCHAR(150) NOT NULL UNIQUE, email VARCHAR(320), password_hash TEXT NOT NULL, roles TEXT NOT NULL DEFAULT '[]', permissions TEXT NOT NULL DEFAULT '[]', active BOOLEAN NOT NULL DEFAULT TRUE, metadata TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS flaxon_admin_settings (key VARCHAR(150) PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS flaxon_admin_activity (id VARCHAR(64) PRIMARY KEY, action VARCHAR(100) NOT NULL, resource VARCHAR(150) NOT NULL, record_id VARCHAR(150), username VARCHAR(150), details TEXT NOT NULL DEFAULT '{}', created_at TIMESTAMP NOT NULL);
CREATE TABLE IF NOT EXISTS flaxon_admin_store (namespace VARCHAR(255) NOT NULL, key VARCHAR(255) NOT NULL, value TEXT NOT NULL, PRIMARY KEY(namespace, key));
CREATE TABLE IF NOT EXISTS flaxon_admin_operations (id VARCHAR(64) PRIMARY KEY, kind VARCHAR(80) NOT NULL, payload TEXT NOT NULL, created_at TIMESTAMP NOT NULL);
CREATE TABLE IF NOT EXISTS flaxon_cms_taxonomies (id VARCHAR(64) PRIMARY KEY, name VARCHAR(150) NOT NULL, slug VARCHAR(180) NOT NULL UNIQUE, description TEXT);
CREATE TABLE IF NOT EXISTS flaxon_cms_terms (id VARCHAR(64) PRIMARY KEY, taxonomy_id VARCHAR(64) NOT NULL, name VARCHAR(150) NOT NULL, slug VARCHAR(180) NOT NULL, parent_id VARCHAR(64));
CREATE TABLE IF NOT EXISTS flaxon_cms_comments (id VARCHAR(64) PRIMARY KEY, content_type VARCHAR(150) NOT NULL, record_id VARCHAR(150) NOT NULL, author_name VARCHAR(150), author_email VARCHAR(320), body TEXT NOT NULL, status VARCHAR(30) NOT NULL DEFAULT 'pending', created_at TIMESTAMP NOT NULL);
CREATE TABLE IF NOT EXISTS flaxon_cms_menus (name VARCHAR(150) PRIMARY KEY, items TEXT NOT NULL DEFAULT '[]');
`
- `Action()` — Base class for a class-based admin action.
- `ActionContext(dashboard: Any, request: Any, user: Any, model_name: str | None, admin_model: Any, params: dict[str, typing.Any]) -> None` — Runtime context handed to :meth:`Action.handle`.
- `ActionResult(kind: str, message: str = , url: str | None = None, filename: str | None = None, content: str | bytes = , content_type: str = text/plain; charset=utf-8, errors: list[dict[str, typing.Any]] = <factory>, data: dict[str, typing.Any] = <factory>) -> None` — Describe the outcome of an action in a transport-independent way.
- `AdminActivity(action: str, resource: str, record_id: str | None = None, username: str = system, timestamp: float = <factory>, details: dict[str, typing.Any] = <factory>) -> None` — Admin activity implementation for the admin subsystem.
- `AdminAuth(users: list[dict[str, typing.Any]] | None = None, backend: flaxon.security.authentication.SessionBackend | None = None, store: typing.Any | None = None, session_idle_timeout: int | None = None, permission_provider: flaxon.admin.authorization.AuthorizationProvider | None = None, strict_permissions: bool = False, password_hasher: flaxon.security.password.PasswordHasher | None = None, cookie_secure: bool = True) -> None` — Small injectable admin auth service backed by Flaxon's token backend.
- `AdminConfig(site_title: str = Flaxon Admin, site_header: str = Flaxon Administration, index_title: str = Welcome to Flaxon Admin, enable_dark_mode: bool = True, enable_search: bool = True, enable_actions: bool = True, enable_filters: bool = True, enable_pagination: bool = True, logo_url: str | None = None, custom_styles: str | None = None, custom_scripts: str | None = None, timezone: str = UTC, settings: dict[str, typing.Any] | None = None, action_bulk_limit: int = 1000, allow_impersonation: bool = False, import_max_rows: int = 5000, import_max_bytes: int = 5242880, enable_extensions: bool = True, disabled_extensions: tuple[str, ...] = (), extensions: list[typing.Any] | None = None) -> None` — Admin config implementation for the admin subsystem.
- `AdminControlPlane(dashboard: Any) -> None` — Admin pages and APIs for service-owned microservice deployments.
- `AdminControlPlaneModule(name: str = admin-control-plane, **kwargs: Any) -> None` — Module marker for extensions that add Admin control-plane features.
- `AdminDashboard(app: Any, config: flaxon.admin.config.AdminConfig | None = None, url_prefix: str = /admin, template_dir: str | None = None, registry: flaxon.admin.registry.Registry | None = None, users: list[dict[str, typing.Any]] | None = None, auth_backend: typing.Any | None = None, upload_dir: str = uploads, store: flaxon.admin.services.AdminStore | None = None, storage_path: str | None = None, redis_url: str | None = None, database: typing.Any | None = None, password_reset_sender: typing.Any | None = None, email_verification_sender: typing.Any | None = None, require_email_verification: bool = False, max_upload_size: int = 10485760, allowed_upload_types: set[str] | None = None, media_storage: typing.Any | None = None, redis_protocol: int = 2, redis_max_connections: int = 100, thumbnail_sync_limit: int = 2097152, session_idle_timeout: int | None = None, media_scanner: typing.Any | None = None, media_retention_days: int = 365, webauthn_provider: typing.Any | None = None, permission_provider: flaxon.admin.authorization.AuthorizationProvider | None = None, strict_permissions: bool = False, max_image_dimensions: tuple[int, int] = (10000, 10000), password_hasher: flaxon.security.password.PasswordHasher | None = None, microservices: bool | dict[str, typing.Any] = True, cookie_secure: bool | None = None, session_bound_csrf: bool = False) -> None` — Admin dashboard implementation for the admin subsystem.
- `AdminError` — Report a admin failure.
- `AdminExtension(*, root: str | pathlib.Path | None = None) -> None` — Base class for a ``flaxon-admin-*`` package.
- `AdminRateLimit(app: Any, prefix: str = /admin, requests: int = 120, window_seconds: int = 60, redis_url: str | None = None, redis_protocol: int = 2, redis_max_connections: int = 100) -> None` — Rate-limit mutating requests under an admin prefix.
- `AdminStore(path: str = flaxon-admin.sqlite3) -> None` — SQLite-backed JSON store for admin metadata and CMS records.
- `AdminStoreSessionBackend(store: flaxon.admin.services.AdminStore, prefix: str = sessions, idle_timeout: int | None = None) -> None` — Persistent single-node sessions backed by the configured AdminStore.
- `AdminView(admin_model: Any, request: flaxon.http.request.Request, dashboard: Any) -> None` — Admin view implementation for the admin subsystem.
- `ApproveOrders()` — Example bulk action: mark selected orders as approved.
- `AsyncAuthorizationProvider(*args, **kwargs)` — Optional contract for providers backed by a remote policy service.
- `AuthorizationProvider(*args, **kwargs)` — Synchronous authorization contract used at request boundaries.
- `BULK` = `bulk`
- `BooleanFilter(field: str, *, label: str | None = None) -> None` — A three-state boolean filter: all, true, false.
- `CasbinAuthorizationProvider(enforcer: Any) -> None` — Optional adapter for applications that already use PyCasbin.
- `ChangeListView(admin_model: Any, request: flaxon.http.request.Request, dashboard: Any) -> None` — Change list view implementation for the admin subsystem.
- `Component(name: str, source: str | pathlib.Path) -> None` — One ``.vel`` single-file component owned by an extension.
- `CreateView(admin_model: Any, request: flaxon.http.request.Request, dashboard: Any) -> None` — Create view implementation for the admin subsystem.
- `DateRangeFilter(field: str, *, label: str | None = None) -> None` — A from/to date range over a date or datetime field.
- `DefaultAuthorizationProvider(role_permissions: collections.abc.Callable[[], dict[str, list[str]]], *, strict: bool = False) -> None` — Built-in group and direct-permission evaluator.
- `DeleteView(admin_model: Any, request: flaxon.http.request.Request, dashboard: Any, object_id: str) -> None` — Delete view implementation for the admin subsystem.
- `DetailView(admin_model: Any, request: flaxon.http.request.Request, dashboard: Any, object_id: str) -> None` — Detail view implementation for the admin subsystem.
- `DurableJob(id: str, name: str, payload: dict[str, typing.Any], status: str = queued, attempts: int = 0, max_attempts: int = 3, error: str | None = None, run_after: float = 0.0, created_at: float = 0.0, updated_at: float = 0.0, history: list[dict[str, typing.Any]] | None = None, worker_id: str | None = None, lease_until: float = 0.0) -> None` — Durable job implementation for the admin subsystem.
- `DurableJobStore(store: Any, namespace: str = admin_jobs) -> None` — Persistent job queue with retry history and idempotent completion.
- `DurableJobWorker(jobs: flaxon.admin.production.DurableJobStore) -> None` — Durable job worker implementation for the admin subsystem.
- `EXTENSION_DISTRIBUTION_PREFIX` = `flaxon-admin-`
- `EventBus(store: typing.Any | None = None) -> None` — Small event-bus contract with a durable outbox-compatible fallback.
- `ExportCsv()` — Example bulk action: export selected records as injection-safe CSV.
- `ExtensionError` — Raised when an admin extension cannot be loaded or compiled.
- `ExtensionPage(name: str, component: flaxon.admin.extensions.Component, *, label: str | None = None, url: str | None = None, permission: str = admin.view_dashboard, icon: str = fa-puzzle-piece, category: str = Extensions, description: str = , props: Any = None, methods: set[str] | None = None) -> None` — A custom admin page rendered from a Teloce component.
- `Filter(field: str, *, label: str | None = None) -> None` — Base filter: one URL parameter, one field, one equality test.
- `ImmutableAuditLog(store: Any, namespace: str = audit) -> None` — Append-only hash chained audit log with verification and retention.
- `ImpersonationManager(dashboard: Any, *, enabled: bool = False) -> None` — Start, inspect and stop impersonation for the current session.
- `Lens(name: Any, *, label: str | None = None, columns: list[str] | None = None, filters: Any = (), query: dict[str, typing.Any] | None = None) -> None` — A named alternate index for a resource.
- `Metric(title: str, *, description: str = , range: str = 30d, ttl: float = 60, permission: str = admin.view_dashboard, date_field: str | None = None, model: Any = None, field: str | None = None, cache: flaxon.admin.metrics.TTLCache | None = None) -> None` — Base class for a dashboard card.
- `MetricRange(key: str, start: datetime.datetime | None = None, end: datetime.datetime | None = None) -> None` — A resolved, immutable time window for a metric calculation.
- `ModelNotFoundError` — Report a model not found failure.
- `NotificationService(store: Any, namespace: str = notifications, max_messages: int = 5000) -> None` — Notification service implementation for the admin subsystem.
- `PARTITION` = `partition`
- `PROGRESS` = `progress`
- `Partition(title: str, *, description: str = , range: str = 30d, ttl: float = 60, permission: str = admin.view_dashboard, date_field: str | None = None, model: Any = None, field: str | None = None, cache: flaxon.admin.metrics.TTLCache | None = None) -> None` — A breakdown by a field rendered as inline horizontal bars.
- `PermissionCatalog() -> None` — Application-local catalog of readable Admin capabilities.
- `PermissionDefinition(key: str, label: str, category: str, description: str = , dangerous: bool = False) -> None` — A permission displayed in the Admin permission matrix.
- `PermissionDeniedError` — Report a permission denied failure.
- `Policy(**actions: Any) -> None` — A deny-only bundle of per-action rules for one resource.
- `PostgreSQLAdminStore(dsn: str) -> None` — PostgreSQL implementation of the synchronous AdminStore contract.
- `Progress(title: str, *, current_filter: dict[str, typing.Any] | None = None, **kwargs: Any) -> None` — A current/target ratio rendered as an inline progress bar.
- `Prompt(name: str, label: str | None = None, kind: str = text, required: bool = False, choices: tuple[typing.Any, ...] = (), default: Any = None) -> None` — A single field an action asks the operator to fill before running.
- `RedisAdminSessionBackend(redis_url: str = redis://localhost:6379/0, prefix: str = flaxon:admin:session, *, protocol: int = 2, max_connections: int = 100, socket_timeout: float = 5.0, idle_timeout: int | None = None) -> None` — Session backend compatible with ``AdminAuth`` for multi-worker deployments.
- `RedisPolicySynchronizer(enforcer: Any, *, redis_url: str | None = None, redis_client: typing.Any | None = None, channel: str = flaxon:admin:policy, protocol: int = 2, max_connections: int = 100) -> None` — Synchronize application-owned Casbin policies across workers.
- `Registry() -> None` — Registry implementation for the admin subsystem.
- `RemoteModelAdapter(client: flaxon.admin.microservices.RemoteServiceClient, resource: str) -> None` — Model-shaped adapter for Admin registry entries backed by a service.
- `RemoteServiceClient(base_url: str, *, token: str | None = None, timeout: float = 5.0, retries: int = 2) -> None` — Dependency-free JSON client for service-owned APIs.
- `RemoteServiceError` — A remote service request failed after retry/circuit-breaker handling.
- `ResumableUploadStore(store: Any, namespace: str = uploads) -> None` — Chunk store that survives restarts and validates the final digest.
- `SINGLE` = `single`
- `STANDALONE` = `standalone`
- `SelectFilter(field: str, choices: Any = (), *, label: str | None = None) -> None` — A dropdown restricted to a fixed set of choices.
- `ServiceRecord(name: str, display_name: str, base_url: str = , environment: str = default, version: str = , status: str = unknown, health_url: str = /health/ready, openapi_url: str = /openapi.json, tags: list[str] = <factory>, owner: str = , metadata: dict[str, typing.Any] = <factory>, updated_at: float = <factory>) -> None` — Serializable service ownership and routing metadata.
- `ServiceRegistry(store: typing.Any | None = None, namespace: str = control_plane) -> None` — Atomic persistent catalog for services, instances and dependencies.
- `ServiceTokenManager(store: typing.Any | None = None) -> None` — One-time-display service/API keys with hashed persistent storage.
- `TABLE` = `table`
- `TREND` = `trend`
- `TTLCache(clock: collections.abc.Callable[[], float] | None = None) -> None` — A tiny in-process cache with per-entry TTL and prefix invalidation.
- `Table(title: str, *, columns: list[str] | None = None, limit: int = 5, **kwargs: Any) -> None` — A small tabular metric rendered with inline SVG text rows.
- `TeloceCard(title: str, component: flaxon.admin.extensions.Component, *, calculate: Any, props: Any = None, **options: Any) -> None` — A dashboard card whose markup is a Teloce component.
- `TeloceField(name: str, component: flaxon.admin.extensions.Component, *, props: dict[str, typing.Any] | None = None, fallback: str = text, fallback_choices: collections.abc.Iterable[tuple[typing.Any, str]] = (), **options: Any) -> None` — A form field whose control is a Teloce component.
- `Tool(label: str, page: flaxon.admin.extensions.ExtensionPage, *, icon: str = fa-toolbox, description: str = , permission: str | None = None) -> None` — A dashboard shortcut contributed by an extension.
- `Trend(title: str, *, description: str = , range: str = 30d, ttl: float = 60, permission: str = admin.view_dashboard, date_field: str | None = None, model: Any = None, field: str | None = None, cache: flaxon.admin.metrics.TTLCache | None = None) -> None` — A daily time series rendered as an inline line chart.
- `UpdateView(admin_model: Any, request: flaxon.http.request.Request, dashboard: Any, object_id: str) -> None` — Update view implementation for the admin subsystem.
- `VALUE` = `value`
- `Value(title: str, *, aggregate: str = count, **kwargs: Any) -> None` — A single aggregate number (count, sum, avg, min or max).
- `WebAuthnService(store: Any, provider: typing.Any | None = None, namespace: str = webauthn) -> None` — Adapter boundary for a real WebAuthn implementation.
- `admin_action(name: str | None = None) -> collections.abc.Callable[[collections.abc.Callable[..., typing.Any]], collections.abc.Callable[..., typing.Any]]` — Decorator to mark a function or method as an admin bulk action.
- `admin_display(header: str | None = None) -> collections.abc.Callable[[collections.abc.Callable[..., typing.Any]], collections.abc.Callable[..., typing.Any]]` — Decorator to mark a method as a custom column display in admin views.
- `admin_model(**options: Any) -> collections.abc.Callable[[type], type]` — Decorator to register a model class with the default admin registry.
- `canonical_model_permission(model_name: str, action: str) -> str` — Return a readable, stable model permission key.
- `default_group_definitions(strict: bool = True) -> tuple[dict[str, list[str]], dict[str, str]]` — Return named built-in groups and their descriptions.
- `load_extensions(*, group: str = flaxon.admin, disabled: collections.abc.Iterable[str] = (), entry_points: Any = None) -> list[flaxon.admin.extensions.AdminExtension]` — Load extensions from installed ``flaxon-admin-*`` distributions.
- `resolve_range(key: str, *, now: datetime.datetime | None = None, start: datetime.datetime | None = None, end: datetime.datetime | None = None) -> flaxon.admin.metrics.MetricRange` — Resolve a named range (30d/60d/mtd/qtd/ytd/custom) to concrete bounds.
- `write_admin_migration(directory: str | pathlib.Path = migrations, name: str = flaxon_admin) -> pathlib.Path` — Generate a migration JSON file consumed by ``flaxon migrate``.

## `flaxon.admin.extensions`

- `ADMIN_EXTENSION_GROUP` = `flaxon.admin`
- `AdminExtension(*, root: str | pathlib.Path | None = None) -> None` — Base class for a ``flaxon-admin-*`` package.
- `Component(name: str, source: str | pathlib.Path) -> None` — One ``.vel`` single-file component owned by an extension.
- `EXTENSION_DISTRIBUTION_PREFIX` = `flaxon-admin-`
- `ExtensionError` — Raised when an admin extension cannot be loaded or compiled.
- `ExtensionPage(name: str, component: flaxon.admin.extensions.Component, *, label: str | None = None, url: str | None = None, permission: str = admin.view_dashboard, icon: str = fa-puzzle-piece, category: str = Extensions, description: str = , props: Any = None, methods: set[str] | None = None) -> None` — A custom admin page rendered from a Teloce component.
- `ExtensionRegistry(dashboard: Any) -> None` — Owns extension discovery, validation, compilation and asset serving.
- `TeloceCard(title: str, component: flaxon.admin.extensions.Component, *, calculate: Any, props: Any = None, **options: Any) -> None` — A dashboard card whose markup is a Teloce component.
- `TeloceField(name: str, component: flaxon.admin.extensions.Component, *, props: dict[str, typing.Any] | None = None, fallback: str = text, fallback_choices: collections.abc.Iterable[tuple[typing.Any, str]] = (), **options: Any) -> None` — A form field whose control is a Teloce component.
- `Tool(label: str, page: flaxon.admin.extensions.ExtensionPage, *, icon: str = fa-toolbox, description: str = , permission: str | None = None) -> None` — A dashboard shortcut contributed by an extension.
- `load_extensions(*, group: str = flaxon.admin, disabled: collections.abc.Iterable[str] = (), entry_points: Any = None) -> list[flaxon.admin.extensions.AdminExtension]` — Load extensions from installed ``flaxon-admin-*`` distributions.

## `flaxon.admin.resources`

- `BADGE` = `badge`
- `BELONGS_TO` = `select`
- `BOOLEAN` = `checkbox`
- `Badge(name: str, label: str | None = None, *, required: bool = False, default: Any = None, choices: list[typing.Any] | tuple[typing.Any, ...] | None = None, help_text: str = , validators: list[flaxon.validation.validators.Validator] | None = None, widget: str | None = None, min_length: int | None = None, max_length: int | None = None, minimum: float | None = None, maximum: float | None = None, pattern: str | None = None, index: bool = True, detail: bool = True, form: bool = True, sortable: bool = False, searchable: bool = False, filterable: bool = False, readonly: bool = False) -> None` — The Badge field type.
- `BelongsTo(name: str, label: str | None = None, *, related_model: Any = None, **kwargs: Any) -> None` — A searchable async select for a foreign-key relation.
- `Boolean(name: str, label: str | None = None, *, required: bool = False, default: Any = None, choices: list[typing.Any] | tuple[typing.Any, ...] | None = None, help_text: str = , validators: list[flaxon.validation.validators.Validator] | None = None, widget: str | None = None, min_length: int | None = None, max_length: int | None = None, minimum: float | None = None, maximum: float | None = None, pattern: str | None = None, index: bool = True, detail: bool = True, form: bool = True, sortable: bool = False, searchable: bool = False, filterable: bool = False, readonly: bool = False) -> None` — The Boolean field type.
- `CODE` = `textarea`
- `COLOR` = `color`
- `CURRENCY` = `number`
- `Code(name: str, label: str | None = None, *, required: bool = False, default: Any = None, choices: list[typing.Any] | tuple[typing.Any, ...] | None = None, help_text: str = , validators: list[flaxon.validation.validators.Validator] | None = None, widget: str | None = None, min_length: int | None = None, max_length: int | None = None, minimum: float | None = None, maximum: float | None = None, pattern: str | None = None, index: bool = True, detail: bool = True, form: bool = True, sortable: bool = False, searchable: bool = False, filterable: bool = False, readonly: bool = False) -> None` — The Code field type.
- `Color(name: str, label: str | None = None, *, required: bool = False, default: Any = None, choices: list[typing.Any] | tuple[typing.Any, ...] | None = None, help_text: str = , validators: list[flaxon.validation.validators.Validator] | None = None, widget: str | None = None, min_length: int | None = None, max_length: int | None = None, minimum: float | None = None, maximum: float | None = None, pattern: str | None = None, index: bool = True, detail: bool = True, form: bool = True, sortable: bool = False, searchable: bool = False, filterable: bool = False, readonly: bool = False) -> None` — The Color field type.
- `Currency(name: str, label: str | None = None, *, required: bool = False, default: Any = None, choices: list[typing.Any] | tuple[typing.Any, ...] | None = None, help_text: str = , validators: list[flaxon.validation.validators.Validator] | None = None, widget: str | None = None, min_length: int | None = None, max_length: int | None = None, minimum: float | None = None, maximum: float | None = None, pattern: str | None = None, index: bool = True, detail: bool = True, form: bool = True, sortable: bool = False, searchable: bool = False, filterable: bool = False, readonly: bool = False) -> None` — The Currency field type.
- `DATE` = `date`
- `DATETIME` = `datetime-local`
- `Date(name: str, label: str | None = None, *, required: bool = False, default: Any = None, choices: list[typing.Any] | tuple[typing.Any, ...] | None = None, help_text: str = , validators: list[flaxon.validation.validators.Validator] | None = None, widget: str | None = None, min_length: int | None = None, max_length: int | None = None, minimum: float | None = None, maximum: float | None = None, pattern: str | None = None, index: bool = True, detail: bool = True, form: bool = True, sortable: bool = False, searchable: bool = False, filterable: bool = False, readonly: bool = False) -> None` — The Date field type.
- `DateTime(name: str, label: str | None = None, *, required: bool = False, default: Any = None, choices: list[typing.Any] | tuple[typing.Any, ...] | None = None, help_text: str = , validators: list[flaxon.validation.validators.Validator] | None = None, widget: str | None = None, min_length: int | None = None, max_length: int | None = None, minimum: float | None = None, maximum: float | None = None, pattern: str | None = None, index: bool = True, detail: bool = True, form: bool = True, sortable: bool = False, searchable: bool = False, filterable: bool = False, readonly: bool = False) -> None` — The DateTime field type.
- `EMAIL` = `email`
- `Email(name: str, label: str | None = None, *, required: bool = False, default: Any = None, choices: list[typing.Any] | tuple[typing.Any, ...] | None = None, help_text: str = , validators: list[flaxon.validation.validators.Validator] | None = None, widget: str | None = None, min_length: int | None = None, max_length: int | None = None, minimum: float | None = None, maximum: float | None = None, pattern: str | None = None, index: bool = True, detail: bool = True, form: bool = True, sortable: bool = False, searchable: bool = False, filterable: bool = False, readonly: bool = False) -> None` — The Email field type.
- `FILE` = `file`
- `Field(name: str, label: str | None = None, *, required: bool = False, default: Any = None, choices: list[typing.Any] | tuple[typing.Any, ...] | None = None, help_text: str = , validators: list[flaxon.validation.validators.Validator] | None = None, widget: str | None = None, min_length: int | None = None, max_length: int | None = None, minimum: float | None = None, maximum: float | None = None, pattern: str | None = None, index: bool = True, detail: bool = True, form: bool = True, sortable: bool = False, searchable: bool = False, filterable: bool = False, readonly: bool = False) -> None` — Base class for a declarative admin field.
- `File(name: str, label: str | None = None, *, required: bool = False, default: Any = None, choices: list[typing.Any] | tuple[typing.Any, ...] | None = None, help_text: str = , validators: list[flaxon.validation.validators.Validator] | None = None, widget: str | None = None, min_length: int | None = None, max_length: int | None = None, minimum: float | None = None, maximum: float | None = None, pattern: str | None = None, index: bool = True, detail: bool = True, form: bool = True, sortable: bool = False, searchable: bool = False, filterable: bool = False, readonly: bool = False) -> None` — The File field type.
- `HAS_MANY` = `many`
- `HasMany(name: str, label: str | None = None, *, related_model: Any = None, **kwargs: Any) -> None` — A related table with inline creation for a reverse FK relation.
- `IMAGE` = `image`
- `Image(name: str, label: str | None = None, *, required: bool = False, default: Any = None, choices: list[typing.Any] | tuple[typing.Any, ...] | None = None, help_text: str = , validators: list[flaxon.validation.validators.Validator] | None = None, widget: str | None = None, min_length: int | None = None, max_length: int | None = None, minimum: float | None = None, maximum: float | None = None, pattern: str | None = None, index: bool = True, detail: bool = True, form: bool = True, sortable: bool = False, searchable: bool = False, filterable: bool = False, readonly: bool = False) -> None` — The Image field type.
- `JSON(name: str, label: str | None = None, *, required: bool = False, default: Any = None, choices: list[typing.Any] | tuple[typing.Any, ...] | None = None, help_text: str = , validators: list[flaxon.validation.validators.Validator] | None = None, widget: str | None = None, min_length: int | None = None, max_length: int | None = None, minimum: float | None = None, maximum: float | None = None, pattern: str | None = None, index: bool = True, detail: bool = True, form: bool = True, sortable: bool = False, searchable: bool = False, filterable: bool = False, readonly: bool = False) -> None` — The JSON field type.
- `KEY_VALUE` = `textarea`
- `KeyValue(name: str, label: str | None = None, *, required: bool = False, default: Any = None, choices: list[typing.Any] | tuple[typing.Any, ...] | None = None, help_text: str = , validators: list[flaxon.validation.validators.Validator] | None = None, widget: str | None = None, min_length: int | None = None, max_length: int | None = None, minimum: float | None = None, maximum: float | None = None, pattern: str | None = None, index: bool = True, detail: bool = True, form: bool = True, sortable: bool = False, searchable: bool = False, filterable: bool = False, readonly: bool = False) -> None` — The KeyValue field type.
- `MANY_TO_MANY` = `many`
- `MARKDOWN` = `textarea`
- `ManyToMany(name: str, label: str | None = None, *, related_model: Any = None, pivot_fields: list[str] | None = None, **kwargs: Any) -> None` — Attach/detach relations, optionally carrying pivot fields.
- `Markdown(name: str, label: str | None = None, *, required: bool = False, default: Any = None, choices: list[typing.Any] | tuple[typing.Any, ...] | None = None, help_text: str = , validators: list[flaxon.validation.validators.Validator] | None = None, widget: str | None = None, min_length: int | None = None, max_length: int | None = None, minimum: float | None = None, maximum: float | None = None, pattern: str | None = None, index: bool = True, detail: bool = True, form: bool = True, sortable: bool = False, searchable: bool = False, filterable: bool = False, readonly: bool = False) -> None` — The Markdown field type.
- `NUMBER` = `number`
- `Number(name: str, label: str | None = None, *, required: bool = False, default: Any = None, choices: list[typing.Any] | tuple[typing.Any, ...] | None = None, help_text: str = , validators: list[flaxon.validation.validators.Validator] | None = None, widget: str | None = None, min_length: int | None = None, max_length: int | None = None, minimum: float | None = None, maximum: float | None = None, pattern: str | None = None, index: bool = True, detail: bool = True, form: bool = True, sortable: bool = False, searchable: bool = False, filterable: bool = False, readonly: bool = False) -> None` — The Number field type.
- `PASSWORD` = `password`
- `Password(name: str, label: str | None = None, *, required: bool = False, default: Any = None, choices: list[typing.Any] | tuple[typing.Any, ...] | None = None, help_text: str = , validators: list[flaxon.validation.validators.Validator] | None = None, widget: str | None = None, min_length: int | None = None, max_length: int | None = None, minimum: float | None = None, maximum: float | None = None, pattern: str | None = None, index: bool = True, detail: bool = True, form: bool = True, sortable: bool = False, searchable: bool = False, filterable: bool = False, readonly: bool = False) -> None` — The Password field type.
- `Resource() -> None` — Describe a model as a full admin in a handful of lines.
- `SELECT` = `select`
- `SLUG` = `text`
- `Select(name: str, label: str | None = None, *, required: bool = False, default: Any = None, choices: list[typing.Any] | tuple[typing.Any, ...] | None = None, help_text: str = , validators: list[flaxon.validation.validators.Validator] | None = None, widget: str | None = None, min_length: int | None = None, max_length: int | None = None, minimum: float | None = None, maximum: float | None = None, pattern: str | None = None, index: bool = True, detail: bool = True, form: bool = True, sortable: bool = False, searchable: bool = False, filterable: bool = False, readonly: bool = False) -> None` — The Select field type.
- `Slug(name: str, label: str | None = None, *, required: bool = False, default: Any = None, choices: list[typing.Any] | tuple[typing.Any, ...] | None = None, help_text: str = , validators: list[flaxon.validation.validators.Validator] | None = None, widget: str | None = None, min_length: int | None = None, max_length: int | None = None, minimum: float | None = None, maximum: float | None = None, pattern: str | None = None, index: bool = True, detail: bool = True, form: bool = True, sortable: bool = False, searchable: bool = False, filterable: bool = False, readonly: bool = False) -> None` — The Slug field type.
- `TAG` = `textarea`
- `TEXT` = `text`
- `TEXTAREA` = `textarea`
- `Tags(name: str, label: str | None = None, *, required: bool = False, default: Any = None, choices: list[typing.Any] | tuple[typing.Any, ...] | None = None, help_text: str = , validators: list[flaxon.validation.validators.Validator] | None = None, widget: str | None = None, min_length: int | None = None, max_length: int | None = None, minimum: float | None = None, maximum: float | None = None, pattern: str | None = None, index: bool = True, detail: bool = True, form: bool = True, sortable: bool = False, searchable: bool = False, filterable: bool = False, readonly: bool = False) -> None` — The Tags field type.
- `Text(name: str, label: str | None = None, *, required: bool = False, default: Any = None, choices: list[typing.Any] | tuple[typing.Any, ...] | None = None, help_text: str = , validators: list[flaxon.validation.validators.Validator] | None = None, widget: str | None = None, min_length: int | None = None, max_length: int | None = None, minimum: float | None = None, maximum: float | None = None, pattern: str | None = None, index: bool = True, detail: bool = True, form: bool = True, sortable: bool = False, searchable: bool = False, filterable: bool = False, readonly: bool = False) -> None` — The Text field type.
- `Textarea(name: str, label: str | None = None, *, required: bool = False, default: Any = None, choices: list[typing.Any] | tuple[typing.Any, ...] | None = None, help_text: str = , validators: list[flaxon.validation.validators.Validator] | None = None, widget: str | None = None, min_length: int | None = None, max_length: int | None = None, minimum: float | None = None, maximum: float | None = None, pattern: str | None = None, index: bool = True, detail: bool = True, form: bool = True, sortable: bool = False, searchable: bool = False, filterable: bool = False, readonly: bool = False) -> None` — The Textarea field type.
- `URL(name: str, label: str | None = None, *, required: bool = False, default: Any = None, choices: list[typing.Any] | tuple[typing.Any, ...] | None = None, help_text: str = , validators: list[flaxon.validation.validators.Validator] | None = None, widget: str | None = None, min_length: int | None = None, max_length: int | None = None, minimum: float | None = None, maximum: float | None = None, pattern: str | None = None, index: bool = True, detail: bool = True, form: bool = True, sortable: bool = False, searchable: bool = False, filterable: bool = False, readonly: bool = False) -> None` — The URL field type.
- `augment_schema(schema: dict[str, typing.Any], resource: flaxon.admin.resources.Resource | None) -> dict[str, typing.Any]` — Expose resource field metadata to the existing admin templates.

## `flaxon.admin.metrics`

- `Metric(title: str, *, description: str = , range: str = 30d, ttl: float = 60, permission: str = admin.view_dashboard, date_field: str | None = None, model: Any = None, field: str | None = None, cache: flaxon.admin.metrics.TTLCache | None = None) -> None` — Base class for a dashboard card.
- `MetricRange(key: str, start: datetime.datetime | None = None, end: datetime.datetime | None = None) -> None` — A resolved, immutable time window for a metric calculation.
- `PARTITION` = `partition`
- `PROGRESS` = `progress`
- `Partition(title: str, *, description: str = , range: str = 30d, ttl: float = 60, permission: str = admin.view_dashboard, date_field: str | None = None, model: Any = None, field: str | None = None, cache: flaxon.admin.metrics.TTLCache | None = None) -> None` — A breakdown by a field rendered as inline horizontal bars.
- `Progress(title: str, *, current_filter: dict[str, typing.Any] | None = None, **kwargs: Any) -> None` — A current/target ratio rendered as an inline progress bar.
- `TABLE` = `table`
- `TREND` = `trend`
- `TTLCache(clock: collections.abc.Callable[[], float] | None = None) -> None` — A tiny in-process cache with per-entry TTL and prefix invalidation.
- `Table(title: str, *, columns: list[str] | None = None, limit: int = 5, **kwargs: Any) -> None` — A small tabular metric rendered with inline SVG text rows.
- `Trend(title: str, *, description: str = , range: str = 30d, ttl: float = 60, permission: str = admin.view_dashboard, date_field: str | None = None, model: Any = None, field: str | None = None, cache: flaxon.admin.metrics.TTLCache | None = None) -> None` — A daily time series rendered as an inline line chart.
- `VALUE` = `value`
- `Value(title: str, *, aggregate: str = count, **kwargs: Any) -> None` — A single aggregate number (count, sum, avg, min or max).
- `resolve_range(key: str, *, now: datetime.datetime | None = None, start: datetime.datetime | None = None, end: datetime.datetime | None = None) -> flaxon.admin.metrics.MetricRange` — Resolve a named range (30d/60d/mtd/qtd/ytd/custom) to concrete bounds.

## `flaxon.admin.actions`

- `Action()` — Base class for a class-based admin action.
- `ActionContext(dashboard: Any, request: Any, user: Any, model_name: str | None, admin_model: Any, params: dict[str, typing.Any]) -> None` — Runtime context handed to :meth:`Action.handle`.
- `ActionResult(kind: str, message: str = , url: str | None = None, filename: str | None = None, content: str | bytes = , content_type: str = text/plain; charset=utf-8, errors: list[dict[str, typing.Any]] = <factory>, data: dict[str, typing.Any] = <factory>) -> None` — Describe the outcome of an action in a transport-independent way.
- `ApproveOrders()` — Example bulk action: mark selected orders as approved.
- `BULK` = `bulk`
- `ExportCsv()` — Example bulk action: export selected records as injection-safe CSV.
- `Prompt(name: str, label: str | None = None, kind: str = text, required: bool = False, choices: tuple[typing.Any, ...] = (), default: Any = None) -> None` — A single field an action asks the operator to fill before running.
- `SINGLE` = `single`
- `STANDALONE` = `standalone`
