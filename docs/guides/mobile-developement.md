# Mobile Development

## Overview

Flaxon is designed to be an excellent backend framework for modern mobile applications. It provides fast JSON APIs, WebSocket support, authentication, file uploads, background tasks, and technology neutrality so you can build backends for any mobile platform.

Whether you're building an Android, iOS, Flutter, React Native, or .NET MAUI application, Flaxon provides the tools needed to create scalable and maintainable APIs.

---

# Why Flaxon for Mobile?

Flaxon is designed around modern mobile application requirements.

## Features

- Async-first architecture
- High-performance JSON APIs
- JWT authentication
- Session authentication
- OAuth2 support
- API versioning
- Built-in validation
- File uploads
- Chunked uploads
- WebSocket support
- GraphQL support
- Background tasks
- Push notification integration
- Offline synchronization
- Rate limiting
- Request validation
- Middleware support
- Database agnostic
- Production ready

---

# Supported Platforms

Flaxon works with virtually every mobile framework.

| Platform | Supported |
|----------|-----------|
| Android (Kotlin) | ✅ |
| Android (Java) | ✅ |
| Swift (iOS) | ✅ |
| Flutter | ✅ |
| React Native | ✅ |
| Ionic | ✅ |
| Capacitor | ✅ |
| Xamarin | ✅ |
| .NET MAUI | ✅ |
| Kotlin Multiplatform | ✅ |

---

# Architecture

A typical Flaxon mobile backend looks like this:

```text
                    Mobile Clients

        Android   iOS   Flutter   React Native

                    │
                    ▼

              HTTPS / WebSocket

                    │
                    ▼

               Flaxon Application

        Routing
        Validation
        Authentication
        Middleware
        WebSockets
        Background Tasks

                    │
                    ▼

        PostgreSQL
        MySQL
        SQLite
        MongoDB
        Redis
```

---

# Project Structure

A recommended project layout:

```text
mobile-backend/

├── app.py
├── routes/
│   ├── auth.py
│   ├── users.py
│   ├── posts.py
│   ├── notifications.py
│   ├── upload.py
│   └── sync.py
│
├── services/
│   ├── auth.py
│   ├── user_service.py
│   ├── notification_service.py
│   ├── upload_service.py
│   └── sync_service.py
│
├── middleware/
│
├── websocket/
│
├── schemas/
│
├── models/
│
├── uploads/
│
├── static/
│
└── tests/
```

---

# Creating Your First Mobile Backend

## Install Flaxon

```bash
pip install flaxon[standard]
```

---

## Create Your Application

```python
from flaxon import Flaxon

app = Flaxon(
    "mobile-backend",
    debug=True,
)
```

---

## Create a Health Endpoint

```python
@app.get("/health")
async def health():

    return {

        "status": "healthy",

        "framework": "Flaxon",

        "version": "1.0.0"

    }
```

---

## Run the Server

```bash
flaxon run app:app --reload
```

Your backend will be available at:

```text
http://localhost:8000
```

---

# Creating REST APIs

Mobile applications usually communicate using JSON.

```python
@app.get("/api/v1/posts")
async def posts():

    return [

        {

            "id": 1,

            "title": "Hello"

        },

        {

            "id": 2,

            "title": "Flaxon"

        }

    ]
```

Response:

```json
[
  {
    "id": 1,
    "title": "Hello"
  },
  {
    "id": 2,
    "title": "Flaxon"
  }
]
```

---

# API Versioning

Version your APIs to maintain backward compatibility.

```python
from flaxon import Router

v1 = Router(
    prefix="/api/v1"
)

v2 = Router(
    prefix="/api/v2"
)
```

Version 1:

```python
@v1.get("/users")
async def users():

    return {

        "version": "v1",

        "users": []

    }
```

Version 2:

```python
@v2.get("/users")
async def users():

    return {

        "version": "v2",

        "users": [],

        "pagination": {

            "page": 1

        }

    }
```

Register routers:

```python
app.include_router(v1)

app.include_router(v2)
```

---

# Request Validation

Validation keeps APIs predictable.

```python
from flaxon.validation import Schema
from flaxon.validation import fields


class RegisterRequest(Schema):

    username = fields.StrField(
        required=True,
        min_length=3,
    )

    email = fields.EmailField(
        required=True,
    )

    password = fields.StrField(
        required=True,
        min_length=8,
    )
```

Use the schema:

```python
@app.post("/api/v1/register")
async def register(data: RegisterRequest):

    return {

        "success": True,

        "user": data.to_dict()

    }
```

---

# Authentication

JWT authentication is recommended for mobile applications.

```python
from flaxon.security import JWTBackend

backend = JWTBackend(
    secret_key="your-secret-key"
)
```

---

## Login

```python
@app.post("/api/v1/login")
async def login(request):

    data = await request.json()

    user = await authenticate(

        data["email"],

        data["password"]

    )

    if not user:

        raise HTTPException(

            401,

            "Invalid credentials"

        )

    token = await backend.create_token(user)

    return {

        "access_token": token,

        "user": user.to_dict()

    }
```

---

## Protecting Routes

```python
from flaxon.security import login_required


@app.get("/api/v1/profile")
@login_required
async def profile(request):

    user = getattr(

        request,

        "user"

    )

    return user.to_dict()
```

---

## Refresh Tokens

Refresh tokens allow users to stay signed in without repeatedly entering credentials.

```python
@app.post("/api/v1/auth/refresh")
async def refresh(request):

    data = await request.json()

    access_token = await refresh_service.refresh(

        data["refresh_token"]

    )

    return {

        "access_token": access_token

    }
```

---

# Device Registration

Register mobile devices to support push notifications.

```python
from flaxon.validation import Schema
from flaxon.validation import fields


class DeviceRegistration(Schema):

    device_id = fields.StrField(
        required=True
    )

    platform = fields.ChoiceField(

        [

            "android",

            "ios",

            "flutter",

            "react-native"

        ],

        required=True

    )

    notification_token = fields.StrField(
        required=True
    )
```

```python
@app.post("/api/v1/devices")
async def register_device(

    data: DeviceRegistration

):

    await device_service.register(

        data.device_id,

        data.platform,

        data.notification_token

    )

    return {

        "success": True

    }
```

# Android Development (Kotlin)

Flaxon works seamlessly with Android applications using Retrofit, OkHttp, Ktor, or any HTTP client.

---

## REST API Example

```python
@app.get("/api/v1/posts")
async def get_posts(request):

    page = request.query.get_int("page", 1)
    limit = request.query.get_int("limit", 20)

    posts = await post_service.get_posts(
        page=page,
        limit=limit,
    )

    return {
        "data": posts,
        "pagination": {
            "page": page,
            "limit": limit,
        },
    }
```

---

## Retrofit Client

```kotlin
interface ApiService {

    @GET("api/v1/posts")
    suspend fun getPosts(
        @Query("page") page: Int
    ): PostsResponse

    @POST("api/v1/login")
    suspend fun login(
        @Body request: LoginRequest
    ): LoginResponse

}
```

---

# iOS Development (Swift)

Flaxon APIs work with URLSession, Alamofire, or any HTTP library.

---

## Example Endpoint

```python
@app.get("/api/v1/profile")
@login_required
async def profile(request):

    user = getattr(request, "user")

    return user.to_dict()
```

---

## Swift Client

```swift
struct APIClient {

    func login(
        email: String,
        password: String
    ) async throws -> LoginResponse {

        let url = URL(
            string: "https://example.com/api/v1/login"
        )!

        // Request implementation...

    }

}
```

---

# Flutter Development

Flutter communicates with Flaxon using the HTTP package or Dio.

Example endpoint:

```python
@app.get("/api/v1/products")
async def products():

    return [
        {
            "id": 1,
            "name": "Laptop"
        },
        {
            "id": 2,
            "name": "Keyboard"
        },
    ]
```

Flutter:

```dart
final response = await http.get(
  Uri.parse(
    "https://example.com/api/v1/products"
  ),
);
```

---

# React Native

Flaxon works with Fetch or Axios.

```javascript
const response = await fetch(
    "https://example.com/api/v1/posts"
);

const data = await response.json();
```

Axios:

```javascript
const response = await axios.get(
    "/api/v1/posts"
);
```

---

# GraphQL

Flaxon also supports GraphQL for mobile applications.

Enable GraphQL:

```python
from flaxon.graphql import GraphQLSchema

schema = GraphQLSchema(
    query=Query
)

app.enable_graphql(schema)
```

Endpoint:

```
/graphql
```

---

## GraphQL Query

```graphql
query {

    users {

        id

        username

        email

    }

}
```

---

## GraphQL Variables

```graphql
query GetUser($id: Int!) {

    user(id: $id) {

        id

        username

    }

}
```

Variables:

```json
{
    "id": 1
}
```

---

# Pagination

Large datasets should always be paginated.

```python
@app.get("/api/v1/users")
async def users(request):

    page = request.query.get_int(
        "page",
        1,
    )

    per_page = request.query.get_int(
        "per_page",
        20,
    )

    users = await user_service.paginate(
        page,
        per_page,
    )

    return {

        "data": users,

        "pagination": {

            "page": page,

            "per_page": per_page,

            "total": 500,

            "total_pages": 25,

        }

    }
```

Response:

```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 500,
    "total_pages": 25
  }
}
```

---

# Searching

```python
@app.get("/api/v1/search")
async def search(request):

    query = request.query.get("q", "")

    results = await search_service.search(query)

    return {

        "query": query,

        "results": results

    }
```

---

# Filtering

```python
@app.get("/api/v1/products")
async def products(request):

    category = request.query.get("category")

    return await product_service.filter(
        category
    )
```

---

# Sorting

```python
@app.get("/api/v1/posts")
async def posts(request):

    sort = request.query.get(
        "sort",
        "created_at",
    )

    return await post_service.list(
        sort=sort
    )
```

---

# Single File Upload

```python
from flaxon.files import FileUpload

upload = FileUpload(
    max_size=20 * 1024 * 1024
)

@app.post("/api/v1/upload")
async def upload_file(request):

    files = await upload.parse(request)

    uploaded = []

    for file in files:

        uploaded.append({

            "filename": file.filename,

            "size": file.size

        })

    return {

        "files": uploaded

    }
```

---

# Multiple Uploads

```python
@app.post("/api/v1/uploads")
async def upload(request):

    files = await upload.parse(request)

    results = []

    for file in files:

        path = storage.save(file)

        results.append({

            "name": file.filename,

            "url": storage.get_url(path)

        })

    return {

        "files": results

    }
```

---

# Chunked Uploads

Useful for videos and large files.

```python
@app.post("/api/v1/upload/chunk")
async def upload_chunk(request):

    data = await request.json()

    chunk = await request.body()

    await chunk_storage.save(

        data["upload_id"],

        data["index"],

        chunk,

    )

    return {

        "received": True

    }
```

---

# Downloading Files

```python
@app.get("/api/v1/files/<filename>")
async def download(filename):

    return FileResponse(
        f"uploads/{filename}"
    )
```

---

# Image Upload Example

```python
@app.post("/api/v1/profile/photo")
@login_required
async def upload_avatar(request):

    files = await upload.parse(request)

    avatar = files[0]

    path = storage.save(avatar)

    return {

        "avatar": storage.get_url(path)

    }
```

---

# Mobile API Best Practices

- Always return JSON.
- Use pagination.
- Validate every request.
- Compress responses.
- Version your APIs.
- Return meaningful HTTP status codes.
- Keep payloads small.
- Support offline synchronization.
- Use HTTPS in production.
- Prefer JWT authentication.
# Android Development (Kotlin)

Flaxon works seamlessly with Android applications using Retrofit, OkHttp, Ktor, or any HTTP client.

---

## REST API Example

```python
@app.get("/api/v1/posts")
async def get_posts(request):

    page = request.query.get_int("page", 1)
    limit = request.query.get_int("limit", 20)

    posts = await post_service.get_posts(
        page=page,
        limit=limit,
    )

    return {
        "data": posts,
        "pagination": {
            "page": page,
            "limit": limit,
        },
    }
```

---

## Retrofit Client

```kotlin
interface ApiService {

    @GET("api/v1/posts")
    suspend fun getPosts(
        @Query("page") page: Int
    ): PostsResponse

    @POST("api/v1/login")
    suspend fun login(
        @Body request: LoginRequest
    ): LoginResponse

}
```

---

# iOS Development (Swift)

Flaxon APIs work with URLSession, Alamofire, or any HTTP library.

---

## Example Endpoint

```python
@app.get("/api/v1/profile")
@login_required
async def profile(request):

    user = getattr(request, "user")

    return user.to_dict()
```

---

## Swift Client

```swift
struct APIClient {

    func login(
        email: String,
        password: String
    ) async throws -> LoginResponse {

        let url = URL(
            string: "https://example.com/api/v1/login"
        )!

        // Request implementation...

    }

}
```

---

# Flutter Development

Flutter communicates with Flaxon using the HTTP package or Dio.

Example endpoint:

```python
@app.get("/api/v1/products")
async def products():

    return [
        {
            "id": 1,
            "name": "Laptop"
        },
        {
            "id": 2,
            "name": "Keyboard"
        },
    ]
```

Flutter:

```dart
final response = await http.get(
  Uri.parse(
    "https://example.com/api/v1/products"
  ),
);
```

---

# React Native

Flaxon works with Fetch or Axios.

```javascript
const response = await fetch(
    "https://example.com/api/v1/posts"
);

const data = await response.json();
```

Axios:

```javascript
const response = await axios.get(
    "/api/v1/posts"
);
```

---

# GraphQL

Flaxon also supports GraphQL for mobile applications.

Enable GraphQL:

```python
from flaxon.graphql import GraphQLSchema

schema = GraphQLSchema(
    query=Query
)

app.enable_graphql(schema)
```

Endpoint:

```
/graphql
```

---

## GraphQL Query

```graphql
query {

    users {

        id

        username

        email

    }

}
```

---

## GraphQL Variables

```graphql
query GetUser($id: Int!) {

    user(id: $id) {

        id

        username

    }

}
```

Variables:

```json
{
    "id": 1
}
```

---

# Pagination

Large datasets should always be paginated.

```python
@app.get("/api/v1/users")
async def users(request):

    page = request.query.get_int(
        "page",
        1,
    )

    per_page = request.query.get_int(
        "per_page",
        20,
    )

    users = await user_service.paginate(
        page,
        per_page,
    )

    return {

        "data": users,

        "pagination": {

            "page": page,

            "per_page": per_page,

            "total": 500,

            "total_pages": 25,

        }

    }
```

Response:

```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 500,
    "total_pages": 25
  }
}
```

---

# Searching

```python
@app.get("/api/v1/search")
async def search(request):

    query = request.query.get("q", "")

    results = await search_service.search(query)

    return {

        "query": query,

        "results": results

    }
```

---

# Filtering

```python
@app.get("/api/v1/products")
async def products(request):

    category = request.query.get("category")

    return await product_service.filter(
        category
    )
```

---

# Sorting

```python
@app.get("/api/v1/posts")
async def posts(request):

    sort = request.query.get(
        "sort",
        "created_at",
    )

    return await post_service.list(
        sort=sort
    )
```

---

# Single File Upload

```python
from flaxon.files import FileUpload

upload = FileUpload(
    max_size=20 * 1024 * 1024
)

@app.post("/api/v1/upload")
async def upload_file(request):

    files = await upload.parse(request)

    uploaded = []

    for file in files:

        uploaded.append({

            "filename": file.filename,

            "size": file.size

        })

    return {

        "files": uploaded

    }
```

---

# Multiple Uploads

```python
@app.post("/api/v1/uploads")
async def upload(request):

    files = await upload.parse(request)

    results = []

    for file in files:

        path = storage.save(file)

        results.append({

            "name": file.filename,

            "url": storage.get_url(path)

        })

    return {

        "files": results

    }
```

---

# Chunked Uploads

Useful for videos and large files.

```python
@app.post("/api/v1/upload/chunk")
async def upload_chunk(request):

    data = await request.json()

    chunk = await request.body()

    await chunk_storage.save(

        data["upload_id"],

        data["index"],

        chunk,

    )

    return {

        "received": True

    }
```

---

# Downloading Files

```python
@app.get("/api/v1/files/<filename>")
async def download(filename):

    return FileResponse(
        f"uploads/{filename}"
    )
```

---

# Image Upload Example

```python
@app.post("/api/v1/profile/photo")
@login_required
async def upload_avatar(request):

    files = await upload.parse(request)

    avatar = files[0]

    path = storage.save(avatar)

    return {

        "avatar": storage.get_url(path)

    }
```

---

# Mobile API Best Practices

- Always return JSON.
- Use pagination.
- Validate every request.
- Compress responses.
- Version your APIs.
- Return meaningful HTTP status codes.
- Keep payloads small.
- Support offline synchronization.
- Use HTTPS in production.
- Prefer JWT authentication.

# WebSockets

Flaxon includes first-class WebSocket support for real-time mobile applications such as chat, notifications, multiplayer games, live dashboards, and collaborative features.

## Basic WebSocket

```python
from flaxon.websocket import WebSocket

@app.websocket("/ws/mobile")
async def mobile_socket(socket: WebSocket):

    await socket.accept()

    try:
        async for message in socket.iter_json():
            await socket.send_json({
                "echo": message
            })

    finally:
        await socket.close()
```

---

## Authenticated WebSocket

```python
from flaxon.security import JWTBackend

backend = JWTBackend(secret_key="your-secret")

@app.websocket("/ws/mobile")
async def websocket(socket: WebSocket):

    token = socket.query.get("token")

    user = await backend.validate_token(token)

    if not user:
        await socket.close(code=4001)
        return

    await socket.accept()

    async for message in socket.iter_json():
        await socket.send_json({
            "user": user.username,
            "message": message,
        })
```

---

## Chat Rooms

```python
@app.websocket("/ws/chat")
async def chat(socket: WebSocket):

    room = socket.query.get("room")

    await socket.accept()

    await socket.join(room)

    try:

        async for message in socket.iter_json():

            await socket.broadcast_json(
                room,
                message,
            )

    finally:

        await socket.leave(room)
```

---

# Push Notifications

Flaxon integrates with Firebase Cloud Messaging (FCM), Apple Push Notification Service (APNs), or custom notification providers.

## Firebase Cloud Messaging

```python
import firebase_admin
from firebase_admin import messaging

firebase_admin.initialize_app()

class NotificationService:

    async def send(
        self,
        token,
        title,
        body,
    ):

        message = messaging.Message(

            notification=messaging.Notification(
                title=title,
                body=body,
            ),

            token=token,

        )

        return await messaging.send_async(message)
```

---

## Sending Notifications

```python
@app.post("/api/v1/notifications")

async def send_notification(request):

    data = await request.json()

    tokens = await device_service.tokens(
        data["user_id"]
    )

    for token in tokens:

        await notification_service.send(
            token,
            data["title"],
            data["body"],
        )

    return {
        "sent": len(tokens)
    }
```

---

# Offline Synchronization

Many mobile applications continue working without an internet connection.

Flaxon supports synchronization endpoints for offline-first applications.

## Sync Endpoint

```python
@app.post("/api/v1/sync")

async def sync(request):

    payload = await request.json()

    last_sync = payload.get(
        "last_sync",
        0,
    )

    return {

        "server_time": time.time(),

        "changes": {

            "users": await user_service.changed_since(last_sync),

            "posts": await post_service.changed_since(last_sync),

            "messages": await message_service.changed_since(last_sync),

        },

        "has_more": False,

    }
```

---

## Conflict Resolution

```python
@app.post("/api/v1/sync/conflict")

async def conflict(request):

    data = await request.json()

    strategy = data.get("strategy")

    if strategy == "server":

        await sync_service.server_wins(data)

    elif strategy == "client":

        await sync_service.client_wins(data)

    elif strategy == "merge":

        await sync_service.merge(data)

    return {
        "resolved": True
    }
```

---

# Background Tasks

Long-running operations should not block API requests.

```python
@app.post("/api/v1/email")

async def send_email(request):

    data = await request.json()

    app.background.create_task(

        email_service.send(

            data["email"],

            data["subject"],

            data["body"],

        )

    )

    return {
        "queued": True
    }
```

---

# Mobile Middleware

Middleware can customize behavior for mobile clients.

```python
from flaxon.middleware import Middleware

class MobileMiddleware(Middleware):

    async def __call__(self, scope, receive, send):

        headers = dict(scope.get("headers", []))

        agent = headers.get(
            b"user-agent",
            b"",
        ).decode()

        scope["mobile"] = any(

            value in agent.lower()

            for value in (

                "android",

                "iphone",

                "ipad",

            )

        )

        await self.app(
            scope,
            receive,
            send,
        )

app.add_middleware(
    MobileMiddleware
)
```

---

# Performance Tips

For the best mobile experience:

- Enable response compression.
- Cache frequently requested data.
- Keep JSON payloads small.
- Use pagination.
- Prefer async database drivers.
- Avoid unnecessary queries.
- Use connection pooling.
- Use Redis for caching and sessions.
- Batch requests when possible.
- Use WebSockets instead of polling.

---

# Security

Recommended production settings:

- HTTPS only
- JWT authentication
- Refresh tokens
- Secure password hashing
- Request validation
- CORS configuration
- Rate limiting
- CSRF protection (where applicable)
- Secure file uploads
- Audit logging

---

# Complete Mobile Backend

A production-ready mobile backend typically includes:

- JWT authentication
- User registration
- Password reset
- Device registration
- Push notifications
- REST API
- GraphQL (optional)
- WebSockets
- File uploads
- Offline synchronization
- Background jobs
- Health checks
- Metrics
- Logging
- Rate limiting
- API versioning

---

# Project Structure

```text
mobile_backend/
│
├── app.py
├── routes/
│   ├── auth.py
│   ├── users.py
│   ├── posts.py
│   ├── uploads.py
│   ├── notifications.py
│   └── websocket.py
│
├── middleware/
├── services/
├── models/
├── schemas/
├── storage/
├── templates/
├── static/
└── tests/
```

---

# Next Steps

Continue with these guides:

- Authentication
- Databases
- Middleware
- GraphQL
- WebSockets
- Security
- Performance
- Deployment
- Admin Dashboard
## Use this capability in a full-stack app

Flaxon serves Python APIs and Teloce interfaces in one project. Keep validation,
authorization and privileged operations on the server; components call those
endpoints and present their results. Follow the [full-stack lessons](../fullstack/index.md)
and [Teloce integration reference](../api/teloce.md) to connect this capability
to pages, components and application modules.
