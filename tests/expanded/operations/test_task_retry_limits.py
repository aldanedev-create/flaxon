"""Task retry limits behavior and boundary cases."""

import pytest

from flaxon.tasks.exceptions import TaskNotFoundError
from flaxon.tasks.registry import TaskRegistry
from flaxon.tasks.retry import RetryPolicy


@pytest.mark.parametrize("count,allowed", [(0, True), (1, True), (2, False), (3, False)])
def test_retry_budget_is_finite(count, allowed):
    assert RetryPolicy(max_retries=2).should_retry(count, ConnectionError()) == allowed


def test_retry_policy_only_retries_selected_exceptions():
    policy = RetryPolicy(retry_on=[ConnectionError])
    assert policy.should_retry(0, ConnectionError())
    assert not policy.should_retry(0, ValueError())


def test_exponential_delay_is_capped_without_random_jitter():
    policy = RetryPolicy(delay=1, backoff=2, max_delay=5, random_jitter=0)
    assert [policy.get_delay(count) for count in [1, 2, 3, 4, 5]] == [1, 2, 4, 5, 5]


def test_removed_job_is_not_resolved_from_registry():
    registry = TaskRegistry()
    registry.register("job", lambda: 1)
    assert registry.get_required("job")() == 1
    registry.remove("job")
    with pytest.raises(TaskNotFoundError):
        registry.get_required("job")
