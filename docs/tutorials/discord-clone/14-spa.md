# Lesson 14: The Teloce SPA

The browser UI lives in `ui/` and is rendered by Teloce, Flaxon's typed
component framework. Components use `<template>`, `<script lang="ts">`, and
`<style scoped>`; imports reference `.html` and `.ts` files. The shell is
`ui/app.html`, which imports the feature components and owns the cross-cutting
state: `currentUser`, `servers`, `channels`, `messages`, `nameById`,
`onlineIds`, and `typingNames`.

A central API client (`ui/api.ts`) keeps every request consistent — it attaches
the CSRF token on mutations and uses **trailing-slash** collection endpoints
(`/api/servers/`, `/api/bots/`) because Flaxon modules mount their root route
that way:

```ts
export const servers = {
  list: () => api.get<ServerList>("/api/servers/"),
  create: (name: string) => api.post<{ server: ServerPublic }>("/api/servers/", { name }),
};
```

The app component also owns the WebSocket layer: it opens one socket, subscribes
to the active channel, notifies typing, and dispatches incoming frames
(`subscribed`, `message.create`, `message.delete`, `presence.update`,
`typing.update`, `channel.created`) into the local state. A missed frame is
never fatal — history is refetched over HTTP.

**Checkpoint:** `python management.py build` compiles the components into
`.flaxon/build` and `GET /` serves the shell (HTTP 200, HTML, with the app mount
point). `tests/test_teloce.py` asserts both. Open the app in a browser and watch
the Network tab: you should see the compiled `.js`, the stylesheet, and API
calls — not server-rendered chat rows.
