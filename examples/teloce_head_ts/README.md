# Pocket Converter: TypeScript and page-head resources

Use a Teloce release supporting `.ts` imports and `<script lang="ts">`. For
repository development, install both checkouts into the same virtual environment:

```bash
python -m pip install -e '/path/to/teloce-py' -e '/path/to/flaxon[standard]'
cd examples/teloce_head_ts
flaxon run app:app --reload
```

Visit http://127.0.0.1:8000. Convert 1 mile to 1.609 km. Click **How it works**
to exercise the CDN-hosted Bootstrap script. Inspect the tab icon, title and page
source. The message comes from the Python `/api/about` endpoint. `ui/app.vel`
imports `ui/units.ts`; browsers receive generated `.js`, not TypeScript.

`lang="en"` configures document language; `<script lang="ts">` selects TypeScript.
Teloce transpiles supported TypeScript syntax; this is not a full TypeScript type
checker. See Teloce's supported syntax before using enums or advanced constructs.

Bootstrap is pinned to 5.3.3. Internet access is required for its styling and
collapse behavior, but conversion and the local API do not depend on Bootstrap.
For offline deployment, download licensed resources to `public/` and use local
URLs. CDN scripts execute with page privileges: select trusted sources, pin
versions, and provide verified `integrity` plus `crossorigin="anonymous"` when
using SRI. CSP must allow the selected resources and Flaxon's module bootstrap.

This example is a teaching fixture, not a desktop launcher or production service.
