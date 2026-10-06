export interface Task {
  id: number;
  title: string;
  complete: boolean;
}

export interface TaskList {
  items: Task[];
}
