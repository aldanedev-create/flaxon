# Lesson 2: Build useful components and scoped styles

Start with loading, success, empty and failure states. The quick-start component
already handles a failed API request; add a retry button that invokes a shared
`loadTasks` method rather than duplicating fetch logic. Preserve current rows
when refreshing so a temporary failure does not erase the user's context.

Extract a row into `ui/components/TaskRow.html` when it has a distinct job:

```html
<template><article><h2>{{ title }}</h2><p>{{ status }}</p></article></template>
<script>export default { props: ["title", "status"] };</script>
<style scoped>article { padding: 1rem; border: 1px solid #bbb; }</style>
```

Import it from the parent component and register it through Teloce's component
API; see the existing [SiteLedger components](../../examples/teloce_siteledger).
Scoped CSS limits component styling, while shared typography belongs in the
application shell. Use real labels, buttons, visible focus and status regions.
Do not make a clickable `div` the only way to perform an action.

**Checkpoint:** show zero tasks, a failed request and a populated list. Navigate
with the keyboard. Confirm a row's styles do not unexpectedly affect another
page. Component extraction should clarify responsibilities rather than create
one file for every line of markup.


## Readable child component

This `.html` file is a component, not a whole browser document. The parent owns
the task object; the child displays it and derives a label with a typed helper.

### `examples/teloce_taskboard/ui/components/TaskRow.html`

```html
<template>
  <article>
    <h2>{{ task.title }}</h2>
    <p>{{ status }}</p>
  </article>
</template>

<script lang="ts">
import { taskStatus } from "../format.ts";

export default {
  props: ["task"],
  computed: {
    status() {
      return taskStatus(this.task);
    },
  },
};
</script>

<style scoped>
article {
  padding: 1rem;
  border: 1px solid #b9c7d5;
  border-radius: 0.5rem;
}

h2 {
  font-size: 1.1rem;
}
</style>
```

## Events, slots and directives

For an editable row, emit an intent instead of mutating a parent-owned prop:

```html
<template>
  <article :class="{ complete: task.complete }">
    <h2 v-text="task.title"></h2>
    <button @click="$emit('select', task.id)">Open task</button>
    <slot></slot>
  </article>
</template>
<script lang="ts">
export default {
  props: ["task"],
  emits: ["select"],
};
</script>
```

A parent handles `@select="openTask"` and supplies slot content. `:class` binds
presentation, `v-text` renders escaped text, `v-if` creates/removes content,
`v-show` controls visibility, and `v-for` repeats keyed rows. `v-model` connects
input state; event modifiers such as `@submit.prevent` prevent default behavior.
The original `<if>`, `<for>` and `:model` forms remain available too.

Use `computed` for derived values, `watch` for side effects and `methods` for
user actions. Keep expensive work and third-party widget creation out of computed
values. Initialize widgets in `mounted()` and destroy them in `beforeUnmount()`.
Never feed untrusted user HTML to `v-html` without appropriate sanitization.


[Course contents](index.md) · [Previous lesson](01-first-app.md) · [Next lesson](03-typed-api.md)
