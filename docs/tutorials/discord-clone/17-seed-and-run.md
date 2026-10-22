# Lesson 17: Seed data and running the app

`seed.py` loads demo data after `migrate`. Run order matters:

```bash
python management.py migrate     # create tables + admin store
python seed.py                   # demo user, server, channels, role, bot
python management.py runserver   # http://127.0.0.1:8000  and  /admin/
```

`seed.py` is **safe to re-run**: every row is created only if it does not
already exist, so running it twice creates nothing the second time. It seeds:

- a `demo` owner and an `alice` member (`password123`),
- a `Flaxon HQ` server with `general`, `random`, and a private `staff` channel,
- a `Moderator` role (with `MANAGE_CHANNELS`) assigned to alice,
- a `Greeter` bot joined to the server, subscribed to `message.create`, with a
  `/ping` command and a one-time token printed to the console,
- a pinned, published `Welcome to Flaxon HQ` announcement.

The one-time bot token is printed exactly once — copy it if you want to exercise
the external token-authenticated path; the in-app BotPanel mints its own.

**Checkpoint:** after seeding, log in as `demo`/`password123` and confirm the
server, its channels (including the private `staff` channel visible to the owner),
and the Greeter bot are present. As `alice`, confirm you can see `general` and
`random` but not `staff` unless granted. Create an admin with
`python management.py setup-admin` and sign in at `/admin/`.
