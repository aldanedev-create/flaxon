import type { Task, TaskList } from "./types.ts";

export async function loadTasks(): Promise<Task[]> {
  const response = await fetch("/api/tasks");

  if (!response.ok) {
    throw new Error("Could not load tasks. Try again.");
  }

  const payload: TaskList = await response.json();
  return payload.items;
}

export async function createTask(title: string): Promise<Task> {
  const response = await fetch("/api/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });

  if (!response.ok) {
    throw new Error("Could not save the task. Check its title and try again.");
  }

  return await response.json();
}
