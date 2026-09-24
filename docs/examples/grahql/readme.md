# GraphQL Example

This runnable example serves a small GraphQL API and a browser demo from the
same Flaxon application. It includes queries, mutations, nested resolvers,
GraphiQL, and the normal Flaxon health endpoints.

The directory is named `grahql` for compatibility with the existing example
path. The application itself and the documentation use the correct GraphQL
spelling.

## Run it

From the repository root:

```bash
python -m pip install -e .
flaxon run docs.examples.grahql.app:app --reload
```

Open:

- Demo UI: <http://127.0.0.1:8000/>
- GraphQL endpoint: <http://127.0.0.1:8000/graphql>
- GraphiQL: <http://127.0.0.1:8000/graphql/graphiql>
- Altair: <http://127.0.0.1:8000/graphql/altair>

## Copyable request

```bash
curl -X POST http://127.0.0.1:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ users { id name email posts { id title } } }"}'
```

Create a user. Flaxon GraphQL's current parser expects arguments separated by
spaces or newlines, not commas:

```graphql
mutation {
  createUser(name: "Bob" email: "bob@example.com") {
    id
    name
    email
  }
}
```

The demo stores records in memory so it is deterministic and requires no
database. For production, move the resolver reads and writes into a service or
repository, add authentication and authorization, and use a persistent
database. The browser page uses relative URLs, so it also works when the app
is served on a non-local host.
