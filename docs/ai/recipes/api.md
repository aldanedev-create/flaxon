# Recipe: a minimal API

The smallest Flaxon application with a JSON route. Run it with
`uvicorn app:app` after installing `flaxon[standard]`.

```python
from flaxon import Flaxon

app = Flaxon("hello")


@app.get("/hello")
async def hello():
    return {"message": "Hello, Flaxon!"}
```

Verify without a running server:

```python
from flaxon.testing import TestClient

response = TestClient(app).get("/hello")
assert response.status_code == 200
assert response.json()["message"] == "Hello, Flaxon!"
```
