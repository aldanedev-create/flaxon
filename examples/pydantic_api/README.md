# Pydantic API

Install the optional integration and run the modular application:

```bash
python -m pip install "flaxon[pydantic]" email-validator
flaxon run examples.pydantic_api.app:app --reload
```

The application factory mounts the `users` feature module at
`/api/users`. The Pydantic model is kept beside that feature in
`modules/users.py`, so adding another feature does not require putting all
schemas and routes into `app.py`.

Send a validated request:

```bash
curl -X POST http://127.0.0.1:8000/api/users/ \
  -H "content-type: application/json" \
  -d '{"name":"Ava","email":"ava@example.com","age":28}'
```
