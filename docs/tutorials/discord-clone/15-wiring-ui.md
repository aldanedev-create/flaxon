# Lesson 15: Wiring the UI to the API

The SPA is a set of small, focused components, each bound to one slice of the
API. The lesson is *composition*: `ui/app.html` holds the shared state and the
WebSocket; the leaf components are presentational and emit events upward.

- **AuthScreen** — login/register tabs; emits `authenticated` so the shell can
  load the user's servers.
- **ServerSidebar** — server list plus create/join popovers; selects a server.
- **ChannelSidebar** — channel list plus a create-channel form (owner sees the
  form; members see only channels they may view, including private grants).
- **MessageView** — chat surface, composer, typing indicator, delete button;
  receives `nameById` to resolve author names and auto-scrolls on new messages.
- **MemberList** — members with `onlineIds` highlighting who is present.
- **BotPanel** — bot CRUD, join server, subscribe, add command, invoke, and a
  token list with revoke.

Because authorization is enforced server-side, the UI only has to *reflect* it:
a member who cannot create channels simply never sees the form, and a private
channel they lack access to is absent from `ChannelSidebar`. The UI trusts
nothing the API has not already authorized.

**Checkpoint:** register in the SPA, create a server, open the seeded `#general`,
send a message, and watch it appear. Create a bot in BotPanel, join it to the
server, add `/ping`, and invoke it — the `pong!` reply should render. Open a
second browser profile, join the same server via its invite code, and confirm
both see the same live messages.
