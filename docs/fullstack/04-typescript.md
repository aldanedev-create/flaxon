# Lesson 4: Use TypeScript without sending types to browsers

Move shared calculations or transformations into `.ts` modules:

```ts
// ui/task-label.ts
export function taskLabel(title: string, complete: boolean): string {
  return complete ? `${title} — complete` : title;
}
```

Import the helper inside `<script lang="ts">` in a `.vel` component. Teloce
transpiles supported type syntax and rewrites `.ts` imports to emitted `.js`.
The Python head option `lang="en"` has a different purpose: it declares the
human language of the HTML document.

The [converter example](../../examples/teloce_head_ts) exercises exactly this
path with `units.ts`. Use a Teloce release containing that support. Supported
syntax is not every TypeScript construct; do not assume enums, namespaces or
parameter properties work in the pure-Python transpiler. Transpilation also
isn't semantic type checking. A separate type-checking tool can be part of CI
when the project's requirements warrant it.

**Checkpoint:** build and inspect the helper output. There should be no type
annotation, `.ts` import or TypeScript served to the browser. Introduce a syntax
error and confirm the build reports it instead of silently shipping bad code.


## One component, several typed modules

The root `.html` component imports the component, API helpers and type-only
contract. Teloce removes browser-invisible types and rewrites local module paths.

### `examples/teloce_taskboard/ui/app.html`

```html
<template>
  <main>
    <h1>Taskboard</h1>
    <p role="status">{{ message }}</p>

    <form @submit.prevent="save">
      <label for="task-title">New task</label>
      <input id="task-title" v-model="title" maxlength="200" required>
      <button type="submit" :disabled="saving">Add task</button>
    </form>

    <button @click="refresh" :disabled="loading">Refresh tasks</button>
    <p v-if="!loading && tasks.length === 0">No tasks yet. Add your first one.</p>
    <section aria-label="Tasks">
      <TaskRow v-for="task in tasks" :key="task.id" :task="task" />
    </section>
  </main>
</template>

<script lang="ts">
import TaskRow from "./components/TaskRow.html";
import { loadTasks, createTask } from "./api.ts";
import type { Task } from "./types.ts";

export default {
  components: { TaskRow },
  data() {
    const tasks: Task[] = [];
    return { tasks, title: "", message: "Loading…", loading: false, saving: false };
  },
  methods: {
    async refresh() {
      this.loading = true;
      try {
        this.tasks = await loadTasks();
        this.message = "Ready";
      } catch {
        this.message = "Could not load tasks. Use Refresh to retry.";
      } finally {
        this.loading = false;
      }
    },
    async save() {
      if (this.saving) return;
      this.saving = true;
      try {
        const task: Task = await createTask(this.title);
        this.tasks = [...this.tasks, task];
        this.title = "";
        this.message = "Task added.";
      } catch {
        this.message = "Could not save the task. Check the title and retry.";
      } finally {
        this.saving = false;
      }
    },
  },
  async mounted() {
    await this.refresh();
  },
};
</script>

<style scoped>
main { max-width: 42rem; margin: 2rem auto; padding: 1rem; font-family: system-ui; }
label { display: block; }
input { margin: 0.5rem 0; padding: 0.5rem; }
button { padding: 0.5rem; margin: 0.5rem; }
section { display: grid; gap: 1rem; }
</style>
```
### `examples/teloce_taskboard/ui/format.ts`

```ts
import type { Task } from "./types.ts";

export function taskStatus(task: Task): string {
  return task.complete ? "Complete" : "Open";
}
```

Follow the actions in order: `mounted()` calls `refresh()`, which loads data;
`save()` creates one task, appends the successful result and clears the field.
Both methods restore their waiting state in `finally`, including on failures.

Choose `.html` in Flaxon's HTML-mode source tree or `.vel` for the explicit SFC
extension. The same template/script/style structure applies. Keep module helpers
inside configured source roots so the builder can emit them. Browser code cannot
import Python; it crosses the server boundary through HTTP/WebSockets.


[Course contents](index.md) · [Previous lesson](03-typed-api.md) · [Next lesson](05-head-and-cdn.md)
