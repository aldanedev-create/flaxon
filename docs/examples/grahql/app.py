"""Flaxon GraphQL example — verified against the actual flaxon.graphql API.

The framework has no String/Int scalar types (the docs example imports
`String`/`Int`, which don't exist and cause an ImportError). Plain Python
types like `str`/`int` work fine as field types, or use the real scalars
(ID, DateTime, Decimal, JSON, UUID, URL, Email) from flaxon.graphql.scalars.

Also note: this parser does NOT treat commas as insignificant whitespace
like standard GraphQL does. Separate arguments with spaces/newlines only,
e.g. createUser(name: "Bob" email: "bob@example.com") — no comma.

One more gotcha: int/float literals in a GraphQL query (e.g. authorId: 1)
arrive in resolvers as Python strings ("1"), not int/float — the parser
never casts them. Cast explicitly in your resolver (int(args["authorId"]))
before using them, e.g. for dict-key lookups.
"""

from pathlib import Path

from flaxon import Flaxon
from flaxon.graphql import Field, GraphQLSchema, List, ObjectType
from flaxon.graphql.scalars import ID
from flaxon.http import HTMLResponse

app = Flaxon("graphql-example", debug=True)
BASE_DIR = Path(__file__).parent

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
# ObjectType(name, fields_dict) — not a subclass, a plain instance built
# from a dict of Field(...) objects. Fields dicts are mutable afterward,
# which lets us resolve the User <-> Post forward reference below.

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
# Note: root-level fields (on Query/Mutation) MUST declare a resolver.
# There's no parent object to fall back to at the root, unlike nested
# fields on a dict (e.g. "id"/"name" above resolve automatically from
# the dict keys).

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
# enable_graphql() only takes (schema, url, enable_playground) — there is
# no subscription_backend kwarg (the docs example's call was wrong).
# It wires up POST /graphql plus a GraphiQL playground at /graphql/graphiql.

schema = GraphQLSchema(query=Query, mutation=Mutation)
app.enable_graphql(schema, url="/graphql")


@app.get("/")
async def home() -> HTMLResponse:
    return HTMLResponse((BASE_DIR / "index.html").read_text(encoding="utf-8"))
