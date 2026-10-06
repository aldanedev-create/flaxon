# Lesson 8: Persist data and authorize every operation

Replace the in-memory list with SQLite for a small deployment or another
supported database for larger workloads. Use database-generated identifiers,
transactions and migrations. Do not block the ASGI event loop with slow
synchronous file or database work; use an async adapter or controlled thread
execution. Read the [database guide](../guides/databases.md) for actual adapter
and lifecycle APIs.

For accounts, choose sessions or another documented authentication mechanism.
Every task query must enforce ownership/team membership on the server, including
read, update and delete. A hidden UI button is not authorization. Context and
browser storage are user-visible, so never send server secrets to components.
Cookie-based authenticated mutations need appropriate CSRF protection and
secure cookie policy; consult the [security guide](../security.md).

Keep validation, authorization and the database write in a coherent operation.
Return an intentional not-found/forbidden response without leaking another
user's records. Separate user-facing errors from internal diagnostic details.

**Checkpoint:** create records for two accounts. Try accessing each record with
the other account, restart the application to check persistence, and provoke a
failed write to ensure the transaction rolls back.


## Readable persistence boundaries

A browser contract can remain simple even when the server becomes richer:

```ts
// ui/account-types.ts
export interface CurrentUser {
  id: number;
  displayName: string;
}

export interface TaskDraft {
  title: string;
}
```

Do not include password hashes, session signing keys or internal access tokens
in those payloads. Persist records through a repository/service, validate writes
at the HTTP boundary and enforce team ownership in the service's queries.
Use a database transaction for related writes, and migrations for schema changes.

When adding file uploads, parse the request form using the documented `Request`
API, restrict size/type, choose a server-controlled storage name and prevent path
traversal. Return an opaque document ID and authorized download endpoint rather
than exposing an arbitrary filesystem path. The UI should show upload progress
or waiting state and a useful failure message.

Flaxon supports different authentication choices; pick one, then configure its
middleware and cookie/token lifecycle from the authentication guide. Don't mix
session, JWT and API-key examples into a single unexplained login implementation.
The course does not make a demo login production-ready by changing its title.


[Course contents](index.md) · [Previous lesson](07-modules.md) · [Next lesson](09-live-updates.md)
