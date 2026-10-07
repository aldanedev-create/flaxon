"""Durable job claims behavior and boundary cases."""

from flaxon.admin.production import DurableJobStore


def test_idempotent_enqueue_does_not_replace_original_payload(admin_store):
    jobs = DurableJobStore(admin_store)
    jobs.enqueue("email", {"to": "first"}, job_id="one")
    duplicate = jobs.enqueue("email", {"to": "second"}, job_id="one")
    assert duplicate.payload == {"to": "first"}
    assert len(jobs.list()) == 1


def test_two_workers_cannot_claim_same_job(admin_store):
    first = DurableJobStore(admin_store)
    second = DurableJobStore(admin_store)
    first.enqueue("email", {}, job_id="one")
    assert len(first.claim_due()) == 1
    assert second.claim_due() == []


def test_completed_job_is_not_claimed_again(admin_store):
    jobs = DurableJobStore(admin_store)
    jobs.enqueue("email", {}, job_id="one")
    jobs.claim_due()
    jobs.complete("one")
    assert jobs.claim_due() == []
