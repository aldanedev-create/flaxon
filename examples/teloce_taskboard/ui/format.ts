import type { Task } from "./types.ts";

export function taskStatus(task: Task): string {
  return task.complete ? "Complete" : "Open";
}
