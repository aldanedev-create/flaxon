# Tasks

## Overview

Flaxon includes a background task system for running long-running jobs outside the normal request lifecycle.

Tasks support:

- Background execution
- Async and sync functions
- Task queues
- Workers
- Scheduling
- Retries
- Timeouts
- Priorities
- Result storage
- Task monitoring
- Custom backends

Common use cases:

- Sending emails
- Processing images/videos
- Generating reports
- Data processing
- Notifications
- Scheduled maintenance jobs

---

# Defining Tasks

Tasks are created using the `@task` decorator.

```python
from flaxon.tasks import task


@task(name="send_email")
async def send_email(
    to: str,
    subject: str,
    body: str,
):
    # Send email logic
    return {
        "sent": True,
        "to": to,
    }


@task(name="process_image")
def process_image(image_path: str):

    # CPU intensive processing
    return {
        "processed": True,
        "file": image_path,
    }
````

---

# Registering Tasks

Tasks must be registered before they can run.

```python
from flaxon.tasks import (
    TaskRegistry,
    TaskQueue,
)

registry = TaskRegistry()
queue = TaskQueue()


registry.register(
    "send_email",
    send_email,
)


registry.register(
    "process_image",
    process_image,
)
```

---

# Creating Tasks

Create a task instance and push it to the queue.

```python
from flaxon.tasks import Task


email_task = Task(
    "send_email",
    send_email,
    args=[
        "user@example.com",
        "Welcome",
        "Hello World",
    ],
)


await queue.push(email_task)
```

---

# Creating Tasks From Registry

```python
task = registry.create_task(
    "send_email",
    args=[
        "user@example.com",
        "Hello",
        "Welcome",
    ],
)


await queue.push(task)
```

---

# Running Workers

Workers execute queued tasks.

Start a worker:

```bash
flaxon worker app:app
```

Multiple workers:

```bash
flaxon worker app:app --concurrency 4
```

Specific queue:

```bash
flaxon worker app:app \
    --queue email \
    --concurrency 2
```

---

# Task Queues

Multiple queues can separate workloads.

Example:

```python
email_queue = TaskQueue(
    name="email"
)


image_queue = TaskQueue(
    name="images"
)
```

Push tasks:

```python
await email_queue.push(
    email_task
)


await image_queue.push(
    image_task
)
```

---

# Scheduling Tasks

Flaxon supports delayed and recurring tasks.

```python
from flaxon.tasks import Scheduler


scheduler = Scheduler(queue)
```

---

## Delayed Task

Run after a delay.

```python
scheduler.schedule(
    task=email_task,
    delay=60,
)
```

The task runs after:

```
60 seconds
```

---

## Recurring Tasks

Run repeatedly.

```python
scheduler.schedule(
    task=image_task,
    interval=300,
)
```

Runs every:

```
5 minutes
```

---

# Scheduled Decorator

```python
from flaxon.tasks import scheduled_task


@scheduled_task(
    interval=60
)
async def cleanup_tokens():

    await db.execute(
        "DELETE FROM expired_tokens"
    )
```

Runs every minute.

---

# Task Results

Tasks can store execution results.

```python
task = Task(
    "send_email",
    send_email,
    args=[
        "user@example.com",
        "Hello",
    ],
)


await queue.push(task)
```

Check result:

```python
import asyncio


while True:

    result = await queue.get_result(
        task.id
    )

    if result.is_done():
        break

    await asyncio.sleep(1)


print(result.result)
```

Example:

```json
{
    "sent": true,
    "to": "user@example.com"
}
```

---

# Retry Policies

Tasks can automatically retry after failures.

```python
from flaxon.tasks import RetryPolicy


policy = RetryPolicy(
    max_retries=5,
    delay=1,
    backoff=2,
    max_delay=60,
    random_jitter=0.1,
)
```

Use policy:

```python
@task(
    name="payment",
    retry_policy=policy,
)
async def process_payment():

    return {
        "success": True
    }
```

Retry behavior:

```
Attempt 1
↓
Wait 1 second

Attempt 2
↓
Wait 2 seconds

Attempt 3
↓
Wait 4 seconds
```

---

# Task Timeouts

Prevent tasks from running forever.

```python
@task(
    name="long_task",
    timeout=30,
)
async def long_task():

    await process_data()
```

The task is cancelled after:

```
30 seconds
```

---

# Task Priorities

Higher priority tasks execute first.

```python
@task(
    name="urgent",
    priority=10,
)
async def urgent_task():
    pass



@task(
    name="normal",
    priority=1,
)
async def normal_task():
    pass
```

Priority:

```
10 → High
1  → Normal
0  → Low
```

---

# Task Signals

Listen for task events.

```python
from flaxon.tasks import (
    Signal,
    connect_signal,
)


def success(task_id, result):

    print(
        f"{task_id} completed"
    )


def failure(task_id, error):

    print(
        f"{task_id} failed"
    )


connect_signal(
    "send_email",
    Signal.ON_SUCCESS,
    success,
)


connect_signal(
    "send_email",
    Signal.ON_FAILURE,
    failure,
)
```

---

# Custom Storage Backend

Task results can be stored using custom backends.

Example Redis backend:

```python
import json


class RedisBackend:

    def __init__(self, redis):

        self.redis = redis


    async def store_task(self, task):

        await self.redis.set(
            f"task:{task.id}",
            json.dumps(
                task.to_dict()
            ),
        )


    async def get_task(self, task_id):

        data = await self.redis.get(
            f"task:{task_id}"
        )

        return Task.from_dict(
            json.loads(data)
        )
```

Enable backend:

```python
queue = TaskQueue(
    backend=RedisBackend(redis)
)
```

---

# Task Monitoring

Check queue status.

```python
@app.get("/tasks/status")
async def task_status():

    return {

        "pending":
            await queue.pending_count(),

        "running":
            await queue.running_count(),

        "completed":
            await queue.completed_count(),

        "failed":
            await queue.failed_count(),

    }
```

---

# Complete Example

```python
import asyncio

from flaxon import Flaxon

from flaxon.tasks import (
    Task,
    TaskQueue,
    TaskRegistry,
    RetryPolicy,
    task,
)


app = Flaxon(
    "tasks-demo"
)


queue = TaskQueue()

registry = TaskRegistry()



@task(
    name="send_email",
    retry_policy=RetryPolicy(
        max_retries=3
    ),
)
async def send_email(
    to,
    subject,
    body,
):

    await asyncio.sleep(1)

    return {
        "sent": True,
        "to": to,
    }



registry.register(
    "send_email",
    send_email,
)



@app.post("/email")
async def email(request):

    data = await request.json()


    job = Task(
        "send_email",
        send_email,
        args=[
            data["to"],
            data["subject"],
            data["body"],
        ],
    )


    await queue.push(job)


    return {

        "task_id": job.id,

        "status": "queued",

    }



@app.get("/tasks/<task_id>")
async def task_status(task_id):

    result = await queue.get_result(
        task_id
    )


    if result is None:

        return {
            "status": "not_found"
        }


    return result.to_dict()



@app.get("/health/tasks")
async def health():

    return {

        "pending":
            await queue.pending_count(),

        "running":
            await queue.running_count(),

        "completed":
            await queue.completed_count(),

        "failed":
            await queue.failed_count(),

    }
```

---

# Best Practices

* Keep tasks small and focused.
* Use retries for unreliable operations.
* Set timeouts for external services.
* Use queues to separate workloads.
* Store large results externally.
* Monitor failed tasks.
* Use idempotent tasks.
* Avoid blocking async workers.
* Use scheduled tasks for maintenance.
* Use dedicated workers for heavy processing.

---

# Next Steps

Continue with:

* WebSockets
* Events
* Background Workers
* Caching
* Database Integration
* Performance Optimization


## Use this capability in a full-stack app

Flaxon serves Python APIs and Teloce interfaces in one project. Keep validation,
authorization and privileged operations on the server; components call those
endpoints and present their results. Follow the [full-stack lessons](../fullstack/index.md)
and [Teloce integration reference](../api/teloce.md) to connect this capability
to pages, components and application modules.
