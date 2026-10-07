
# Tasks API

## Task

Task definition.

## Constructor

```python
Task(
    name: str,
    func: Callable,
    *,
    retry_policy: RetryPolicy | None = None,
    timeout: int | None = None,
    queue: str = "default",
    priority: int = 0
)
````

## Methods

### run

```python
async def run(
    *args: Any,
    **kwargs: Any
) -> Any
```

Run the task.

---

### cancel

```python
def cancel() -> None
```

Cancel the task.

---

### to_result

```python
def to_result() -> TaskResult
```

Convert the task into a `TaskResult`.

---

## Properties

| Property     | Type       | Description         |
| ------------ | ---------- | ------------------- |
| id           | str        | Task ID             |
| name         | str        | Task name           |
| status       | TaskStatus | Task status         |
| created_at   | datetime   | Created timestamp   |
| started_at   | datetime   | Started timestamp   |
| completed_at | datetime   | Completed timestamp |
| retry_count  | int        | Retry count         |

---

# TaskStatus

Task status enum.

| Value     | Description     |
| --------- | --------------- |
| PENDING   | Task is pending |
| RUNNING   | Task is running |
| COMPLETED | Task completed  |
| FAILED    | Task failed     |
| RETRY     | Task will retry |
| CANCELLED | Task cancelled  |
| TIMEOUT   | Task timed out  |

---

# TaskQueue

Task queue.

## Constructor

```python
TaskQueue(
    name: str = "default",
    max_size: int = 1000
)
```

## Methods

### push

```python
async def push(
    task: Task
) -> None
```

Push a task to the queue.

---

### pop

```python
async def pop(
    timeout: float | None = None
) -> Task | None
```

Pop a task from the queue.

---

### get

```python
async def get(
    task_id: str
) -> Task | None
```

Get a task by ID.

---

### remove

```python
async def remove(
    task_id: str
) -> bool
```

Remove a task.

---

### cancel

```python
async def cancel(
    task_id: str
) -> bool
```

Cancel a task.

---

### clear

```python
async def clear() -> None
```

Clear the queue.

---

### size

```python
async def size() -> int
```

Get queue size.

---

### pending_count

```python
async def pending_count() -> int
```

Get pending task count.

---

### running_count

```python
async def running_count() -> int
```

Get running task count.

---

### completed_count

```python
async def completed_count() -> int
```

Get completed task count.

---

### failed_count

```python
async def failed_count() -> int
```

Get failed task count.

---

# Worker

Task worker.

## Constructor

```python
Worker(
    registry: TaskRegistry,
    queue: TaskQueue | None = None,
    concurrency: int = 10,
    queue_name: str = "default"
)
```

## Methods

### start

```python
async def start() -> None
```

Start the worker.

---

### stop

```python
def stop() -> None
```

Stop the worker.

---

### shutdown

```python
def shutdown() -> None
```

Shutdown the worker.

---

### is_running

```python
def is_running() -> bool
```

Check whether the worker is running.

---

# Scheduler

Task scheduler.

## Constructor

```python
Scheduler(
    queue: TaskQueue
)
```

## Methods

### schedule

```python
def schedule(
    task: Task,
    delay: int | None = None,
    at: datetime | None = None,
    interval: int | None = None
) -> None
```

Schedule a task.

---

### start

```python
async def start() -> None
```

Start the scheduler.

---

### stop

```python
async def stop() -> None
```

Stop the scheduler.

---

# RetryPolicy

Task retry configuration.

## Constructor

```python
RetryPolicy(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    max_delay: float = 60.0,
    random_jitter: float = 0.1,
    retry_on: list[type[Exception]] | None = None
)
```

## Methods

### should_retry

```python
def should_retry(
    retry_count: int,
    error: Exception
) -> bool
```

Check if retry should be attempted.

---

### get_delay

```python
def get_delay(
    retry_count: int
) -> float
```

Get retry delay.

---

# TaskResult

Task execution result.

## Attributes

| Attribute   | Type       | Description   |
| ----------- | ---------- | ------------- |
| id          | str        | Task ID       |
| name        | str        | Task name     |
| status      | TaskStatus | Task status   |
| result      | Any        | Task result   |
| error       | str | None | Error message |
| retry_count | int        | Retry count   |

---

## Methods

### is_pending

```python
def is_pending() -> bool
```

Check if pending.

---

### is_running

```python
def is_running() -> bool
```

Check if running.

---

### is_completed

```python
def is_completed() -> bool
```

Check if completed.

---

### is_failed

```python
def is_failed() -> bool
```

Check if failed.

---

### is_retry

```python
def is_retry() -> bool
```

Check if retrying.

---

### is_cancelled

```python
def is_cancelled() -> bool
```

Check if cancelled.

---

### is_timeout

```python
def is_timeout() -> bool
```

Check if timed out.

---

### is_done

```python
def is_done() -> bool
```

Check if task is finished.

---

### get_duration

```python
def get_duration() -> float | None
```

Get task execution duration.

---

### to_dict

```python
def to_dict() -> dict[str, Any]
```

Convert result to dictionary.

---

# Admin Durable Jobs

The Admin production layer exposes a small persistent job contract for work
such as thumbnail generation. It uses the configured AdminStore and records
retry state, errors, and completion:

```python
from flaxon.admin import DurableJobStore, DurableJobWorker

jobs = DurableJobStore(admin.store)
worker = DurableJobWorker(jobs)
worker.register("media.thumbnail", make_thumbnail)
job = jobs.enqueue("media.thumbnail", {"relative": "images/photo.jpg"}, max_attempts=4)
await worker.run_once()
```

Handlers are registered by name so the worker can be started separately from
the web process. For multiple workers, use a shared persistent store and add a
distributed claim/lease implementation appropriate to the database or Redis
deployment.


## Use this capability in a full-stack app

Flaxon serves Python APIs and Teloce interfaces in one project. Keep validation,
authorization and privileged operations on the server; components call those
endpoints and present their results. Follow the [full-stack lessons](../fullstack/index.md)
and [Teloce integration reference](../api/teloce.md) to connect this capability
to pages, components and application modules.
