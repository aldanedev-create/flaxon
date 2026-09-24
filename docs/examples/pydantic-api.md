# Pydantic API Example

This runnable example shows a feature module with a Pydantic request model.
The root application only creates Flaxon and mounts the feature:

```text
examples/pydantic_api/
|-- app.py
`-- modules/
    `-- users.py
```

Install the optional integration and the email validator used by
`EmailStr`:

```bash
python -m pip install "flaxon[pydantic]" email-validator
```

Run it from the repository root:

```bash
flaxon run examples.pydantic_api.app:app --reload
```

Send a request to the mounted module:

```bash
curl -X POST http://127.0.0.1:8000/api/users/ \
  -H "content-type: application/json" \
  -d '{"name":"Ava","email":"ava@example.com","age":28}'
```

Use `FlaxonModule` for the feature boundary, Pydantic for the request
contract, and a service or repository for the database write. This keeps the
same business operation reusable from HTTP, tasks, or other integrations.

Source files: [app.py](https://github.com/aldanedev-create/Flaxon-Backend-Framework/tree/main/examples/pydantic_api)
