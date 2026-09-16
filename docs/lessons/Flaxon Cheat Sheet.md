# Flaxon Cheat Sheet

For feature details and caveats, see [Features](Features.md). For Admin/CMS details, see [Admin and CMS](../guides/admin-cms.md) and [Admin cheatsheet](Admin%20cheatsheet.md).

## App and routes

```python
from flaxon import Flaxon
app = Flaxon("my-app", debug=True)

@app.get("/")
async def home(): return {"ok": True}
```

Run: `flaxon run app:app --reload`. Routes use `@app.get/post/put/patch/delete`; converters are `<int:id>`, `<float:x>`, `<str:x>`, `<uuid:id>`, and `<path:value>`. Return dict/list for JSON, string for text, or a response class.

## Validation and security

```python
from flaxon.validation import Schema, fields
from flaxon.security.password import PasswordHasher

class Input(Schema):
    name = fields.StrField(required=True)

@app.post("/items")
async def create(data: Input): return data.to_dict()

hashed = PasswordHasher().hash("secret")
```

`request.session` is signed-cookie backed by default. Register dependencies with `app.container.register_instance` or `register_factory`. Add middleware with `app.add_middleware`; CSRF and rate limiting are in `flaxon.security`, other middleware is in `flaxon.middleware`. Security decorators: `jwt_required`, `role_required`, `permission_required`, `api_key_required`.

## Admin and CMS

```python
from flaxon.admin import AdminConfig, AdminDashboard
from flaxon.admin.cms import CMSConfig
from flaxon.database.adapters.sqlite import SQLiteAdapter

admin = AdminDashboard(
    app,
    config=AdminConfig(site_title="Acme Admin"),
    database=SQLiteAdapter("data/admin.db"),
    cms_config=CMSConfig(enabled=True),
)
admin.register(Product, list_display=["name", "price"], fields=["name", "price"])
```

Or use `app.enable_admin(url_prefix="/admin", config=..., ...)`. Run `flaxon migrate --direction up` before persistent use. The UI/API covers model CRUD and list controls, users/roles/permissions, profile/settings, audit activity, media, taxonomy, comments/moderation, revisions/restore, scheduled publishing/workflows, menus, and CSV/JSON import/export. Controls are permission- and configuration-aware.

## Database

```python
from flaxon.database.adapters.sqlite import SQLiteAdapter

db = SQLiteAdapter("data/app.db")
await db.connect()
await db.begin()
await db.execute("INSERT INTO users (name) VALUES (?)", "Ada")
await db.commit()                 # or await db.rollback()
rows = await db.fetch_all("SELECT * FROM users")
await db.disconnect()
```

SQL adapters: `SQLiteAdapter`, `PostgreSQLAdapter`, `MySQLAdapter`, `SQLAlchemyAdapter`. `CustomAdapter` wraps a project connection. `MongoDBAdapter` uses `find_*`, `insert_*`, `update_*`, `delete_*`, and `count`; `RedisAdapter` uses `get`, `set`, hashes, lists, and sets. MongoDB and Redis intentionally do not implement SQL methods. Drivers are `aiosqlite`, `asyncpg`, `aiomysql`, `motor`, `redis`, and `sqlalchemy[asyncio]` as applicable.

## Other modules

```python
from flaxon.caching import Cache
c = Cache(); await c.set("key", "value", ttl=60)

from flaxon.testing import TestClient
client = TestClient(app)
response = client.post("/items", json_data={"name": "Ada"})
```

WebSockets: `accept`, `join`, `leave`, `receive_json`, `send_json`, `iter_json`, `broadcast_json`, `close`. GraphQL: `app.enable_graphql(GraphQLSchema(query=query_type))`. OpenAPI: `app.enable_openapi(title="My API")`, serving `/openapi.json`, `/docs`, `/redoc`. Tasks: `flaxon worker app:app` and `flaxon schedule app:app`. Events use `EventRegistry` and `EventDispatcher`; mail uses `Mailer`; templates use `Jinax` and `request.render`. Health endpoints are `/health`, `/health/live`, `/health/ready`, and `/metrics`; debug history is `/__debug__`.

## CLI

| Command | Purpose |
|---|---|
| `flaxon run app:app --reload` | Start development server |
| `flaxon routes app:app` | List routes |
| `flaxon doctor app:app` | Check app health |
| `flaxon docs app:app -o openapi.json` | Export OpenAPI |
| `flaxon inspect app:app --middleware --config` | Inspect app |
| `flaxon migrate --direction up` | Apply migrations |
| `flaxon worker app:app` | Run task worker |
| `flaxon schedule app:app` | Run scheduled tasks |
| `flaxon test` | Run tests |

Full CLI reference: [CLI Cheatsheet](Cli.md).
