# GraphQL API Example

This example demonstrates a complete Flaxon GraphQL API with:

- Queries
- Mutations
- GraphQL types with resolvers
- GraphiQL playground


## Running the Example

Create a new Flaxon project:

```bash
flaxon new graphql-example

cd graphql-example
```

Install dependencies:

```bash
pip install flaxon
```

Create `app.py` with the code below.

Run:

```bash
flaxon run app:app --reload
```

The CLI handles host/port automatically (defaults to `127.0.0.1:8000`) —
`app.py` just needs to define `app` at module level. No `app.run(...)` call
or `if __name__ == "__main__"` block is needed (there is no `app.run()`
method on the Flaxon app object).

---

# Application Code

## app.py

```python
from flaxon import Flaxon
from flaxon.graphql import GraphQLSchema, ObjectType, Field, List
from flaxon.graphql.scalars import ID

app = Flaxon("graphql-example", debug=True)


# --------------------
# Data Storage
# --------------------

users = [{"id": 1, "name": "Alice", "email": "alice@example.com"}]
posts = [{"id": 1, "title": "First Post", "content": "Hello GraphQL", "author_id": 1}]

user_id_counter = 2
post_id_counter = 2


# --------------------
# GraphQL Types
# --------------------
# ObjectType(name, fields_dict) is a plain instance built from a dict of
# Field(...) objects — it is NOT meant to be subclassed. There is no
# built-in String/Int scalar; use plain Python types (str, int, float) as
# field types, or the real scalars (ID, DateTime, Decimal, JSON, UUID,
# URL, Email) from flaxon.graphql.scalars.
#
# fields dicts are mutable after construction, which lets us resolve the
# User <-> Post forward reference below.

def resolve_user_posts(parent, args, context, info):
    return [p for p in posts if p["author_id"] == parent["id"]]


# Build Post first, without "author" (it depends on UserType, defined next).
PostType = ObjectType("Post", {
    "id": Field(ID),
    "title": Field(str),
    "content": Field(str),
    "authorId": Field(ID, resolver=lambda parent, args, ctx, info: parent["author_id"]),
})

UserType = ObjectType("User", {
    "id": Field(ID),
    "name": Field(str),
    "email": Field(str),
    "posts": Field(List(PostType), resolver=resolve_user_posts),
})


def resolve_post_author(parent, args, context, info):
    return next((u for u in users if u["id"] == parent["author_id"]), None)


# Patch the forward reference in now that UserType exists.
PostType.fields["author"] = Field(UserType, resolver=resolve_post_author)
PostType.fields["author"].name = "author"


# --------------------
# Queries
# --------------------
# Root-level fields (on Query/Mutation) MUST declare a resolver — there is
# no parent object to fall back to at the root, unlike nested fields on a
# dict (e.g. "id"/"name" above resolve automatically from the dict keys).

def resolve_hello(parent, args, context, info):
    return f"Hello {args.get('name', 'World')}!"


def resolve_users(parent, args, context, info):
    return users


def resolve_posts(parent, args, context, info):
    return posts


Query = ObjectType("Query", {
    "hello": Field(str, args={"name": str}, resolver=resolve_hello),
    "users": Field(List(UserType), resolver=resolve_users),
    "posts": Field(List(PostType), resolver=resolve_posts),
})


# --------------------
# Mutations
# --------------------

def resolve_create_user(parent, args, context, info):
    global user_id_counter
    user = {"id": user_id_counter, "name": args["name"], "email": args["email"]}
    user_id_counter += 1
    users.append(user)
    return user


def resolve_create_post(parent, args, context, info):
    global post_id_counter
    post = {
        "id": post_id_counter,
        "title": args["title"],
        "content": args["content"],
        # GraphQL int literals arrive as strings in resolvers — cast explicitly.
        "author_id": int(args["authorId"]),
    }
    post_id_counter += 1
    posts.append(post)
    return post


Mutation = ObjectType("Mutation", {
    "createUser": Field(
        UserType,
        args={"name": str, "email": str},
        resolver=resolve_create_user,
    ),
    "createPost": Field(
        PostType,
        args={"title": str, "content": str, "authorId": int},
        resolver=resolve_create_post,
    ),
})


# --------------------
# GraphQL Setup
# --------------------
# enable_graphql(schema, url, enable_playground) wires up POST /graphql
# plus a GraphiQL playground at /graphql/graphiql. It does not take a
# subscription_backend argument — subscriptions aren't wired up this way
# in this framework and need manual integration with SubscriptionManager
# and websockets (out of scope for this example).

schema = GraphQLSchema(query=Query, mutation=Mutation)
app.enable_graphql(schema, url="/graphql")


@app.get("/")
async def home():
    return {
        "message": "Welcome to Flaxon GraphQL",
        "endpoint": "/graphql",
        "playground": "/graphql/graphiql",
    }
```

Run the example with `flaxon run app:app --reload`.

---

# Testing the API

## GraphiQL Playground

Open:

```
http://localhost:8000/graphql/graphiql
```

---

# Queries

## Hello

```graphql
query {
  hello(name: "Flaxon")
}
```

---

## Get Users

```graphql
query {
  users {
    id
    name
    email
    posts {
      id
      title
    }
  }
}
```

---

## Get Posts

```graphql
query {
  posts {
    id
    title
    content
    author {
      name
    }
  }
}
```

---

# Mutations

> **Important:** this parser does **not** treat commas between arguments
> as insignificant whitespace the way standard GraphQL does. Separate
> arguments with spaces or newlines only — a comma causes a parse error
> (`Unexpected character: ,`).

## Create User

```graphql
mutation {
  createUser(name: "Bob" email: "bob@example.com") {
    id
    name
    email
  }
}
```

---

## Create Post

```graphql
mutation {
  createPost(title: "New Post" content: "GraphQL Example" authorId: 1) {
    id
    title
    author {
      name
    }
  }
}
```

---

# Using curl

## Query

```bash
curl -X POST http://localhost:8000/graphql \
-H "Content-Type: application/json" \
-d '{"query":"{ hello(name: \"Flaxon\") }"}'
```

---

## Mutation

```bash
curl -X POST http://localhost:8000/graphql \
-H "Content-Type: application/json" \
-d '{"query":"mutation { createUser(name: \"Bob\" email: \"bob@example.com\") { id name } }"}'
```

---

# Production Improvements

Recommended next steps:

- Add GraphQL authentication (see `flaxon.security.login_required`)
- Add database integration
- Add custom scalar types beyond the built-ins (`ID`, `DateTime`, `Decimal`, `JSON`, `UUID`, `URL`, `Email`)
- Wire up subscriptions manually via `flaxon.graphql.subscriptions.SubscriptionManager`
- Deploy with a production ASGI server
