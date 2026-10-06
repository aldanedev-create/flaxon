# Taskboard course example

A readable Python API with Teloce `.html` components using `<script lang="ts">`.
The browser imports `api.ts`, `types.ts`, and `format.ts`; the compiler emits `.js`.

```bash
python -m pip install -e /path/to/teloce-py -e '/path/to/flaxon[standard]'
cd examples/teloce_taskboard
flaxon run app:app --reload
```

Open http://127.0.0.1:8000. Add a task, refresh the list, and inspect Network tools.
Validation runs in Python. The typed API helper handles HTTP failures; types alone
do not validate untrusted JSON. Tasks reset on restart. This example has no login,
production database, delete action or globally unique concurrent IDs.

Read [lessons 1–10](../../docs/fullstack/index.md). The files here are the working
baseline for lessons 1–4; later lessons describe extensions and alternative
rendering choices. The [converter](../teloce_head_ts) demonstrates CDN resources.
