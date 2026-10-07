"""Router prefix isolation behavior and boundary cases."""

from flaxon.routing import Router


def test_router_prefix_is_applied_once(app, client):
    router = Router(prefix="/api/v1")

    @router.get("/jobs/<int:job_id>")
    async def job(job_id):
        return {"id": job_id}

    app.include_router(router)
    assert client.get("/api/v1/jobs/9").json() == {"id": 9}
    assert client.get("/jobs/9").status_code == 404
    assert client.get("/api/v1/api/v1/jobs/9").status_code == 404


def test_two_routers_keep_their_own_namespaces(app, client):
    for prefix in ["/public", "/private"]:
        router = Router(prefix=prefix)

        def endpoint(prefix=prefix):
            return {"prefix": prefix}

        router.get("/status")(endpoint)
        app.include_router(router)
    assert client.get("/public/status").json()["prefix"] == "/public"
    assert client.get("/private/status").json()["prefix"] == "/private"
