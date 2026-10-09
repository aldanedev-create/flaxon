# Python framework comparison results

Flaxon placed third of six by median throughput for plaintext and small JSON, and fourth for the last dynamic route in an application with 1,000 routes. Large-response results are partly client-limited. This run supports a workload-specific top-three statement; it does not establish Flaxon as one of the fastest Python frameworks generally.

## Median requests per second

| Framework | Plaintext | Small JSON | 1,000-row JSON | 1,000-route lookup |
| --- | ---: | ---: | ---: | ---: |
| Flaxon | 28,943 | 28,833 | 2,824 | 4,462 |
| FastAPI | 15,920 | 13,581 | 236 | 1,260 |
| Starlette | 34,262 | 30,614 | 2,787 | 2,591 |
| Litestar | 23,442 | 23,908 | 2,862 | 18,164 |
| Sanic | 14,457 | 14,314 | 2,849 | 13,122 |
| Falcon | 36,876 | 32,929 | 3,046 | 18,710 |

Validated 3,320,345 measured responses with 0 errors across 72 samples. Warmup responses are not counted.

## Sample ranges and latency

| Framework | Workload | Min–max req/s | Median p95 ms | Median client CPU |
| --- | --- | ---: | ---: | ---: |
| Flaxon | /plaintext | 27,896–30,241 | 1.666 | 44.0% |
| Flaxon | /json | 28,622–29,335 | 1.772 | 46.7% |
| Flaxon | /large-json | 2,636–2,885 | 16.594 | 100.3% |
| Flaxon | /routes/999/42 | 4,200–4,482 | 9.699 | 14.9% |
| FastAPI | /plaintext | 15,749–19,440 | 3.037 | 30.7% |
| FastAPI | /json | 13,266–15,074 | 3.480 | 27.3% |
| FastAPI | /large-json | 221–245 | 310.835 | 12.6% |
| FastAPI | /routes/999/42 | 1,249–1,266 | 31.054 | 8.3% |
| Starlette | /plaintext | 31,876–34,476 | 1.453 | 48.3% |
| Starlette | /json | 28,879–31,637 | 1.627 | 47.0% |
| Starlette | /large-json | 2,752–3,118 | 18.207 | 96.6% |
| Starlette | /routes/999/42 | 2,558–2,675 | 14.590 | 13.2% |
| Litestar | /plaintext | 22,697–23,800 | 2.183 | 34.9% |
| Litestar | /json | 21,258–24,367 | 2.224 | 37.1% |
| Litestar | /large-json | 2,656–2,907 | 15.068 | 100.3% |
| Litestar | /routes/999/42 | 16,458–19,747 | 2.678 | 36.5% |
| Sanic | /plaintext | 12,947–14,865 | 3.358 | 30.1% |
| Sanic | /json | 12,401–15,164 | 3.295 | 31.8% |
| Sanic | /large-json | 2,812–2,986 | 18.723 | 98.3% |
| Sanic | /routes/999/42 | 11,705–13,431 | 3.689 | 31.1% |
| Falcon | /plaintext | 33,888–39,351 | 1.367 | 49.6% |
| Falcon | /json | 31,415–34,388 | 1.613 | 48.3% |
| Falcon | /large-json | 2,983–3,101 | 17.743 | 97.9% |
| Falcon | /routes/999/42 | 16,231–19,093 | 2.654 | 32.6% |

## Interpretation

- Falcon and Starlette had higher median plaintext and small-JSON throughput than Flaxon in this run. Flaxon exceeded FastAPI, Litestar and Sanic in these two workloads.
- For the dynamic route among 1,000 routes, Falcon, Litestar and Sanic exceeded Flaxon. Improving Flaxon’s dynamic route indexing is a measurable opportunity.
- Several large-response samples saturated the client CPU. Similar throughput among most frameworks in this workload is not proof of equivalent server capacity.
- FastAPI’s conventional dictionary/list return path includes encoding work that explicit responses can avoid. These adapters exercise normal response APIs; they do not rank every framework’s maximum tuned performance.
- Sanic uses ASGI mode, not its native server. This controlled-server result must not be generalized to Sanic’s native deployment.
- Three short repeats on one shared host do not establish a universal ranking. No development-time or bug-reduction percentages are measured.

## Supported wording

> Flaxon ranked in the top three of six tested Python frameworks for plaintext and small JSON in our single-worker Uvicorn benchmark. Results vary by workload and deployment.

## Reproducibility

See PYTHON_FRAMEWORK_METHOD.md for commands, controls and limitations; python-framework-results.json contains all raw samples, package versions, environment information, and benchmark source checksums. The recorded Git revision precedes the added adapters; checksums identify the actual benchmark files. Framework source is unchanged from merged PR #10.

An initial partial run was discarded after finding that the load client did not support chunked responses. The client was fixed, Sanic large responses passed preflight validation, and all 72 samples were restarted. Only the corrected complete run is included.
