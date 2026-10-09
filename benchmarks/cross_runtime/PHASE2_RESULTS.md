# Request and JSON performance results

Compared with the previous request/security implementation, using one Uvicorn worker, 32 keepalive clients, three randomized three-second samples per endpoint, pinned server/client CPUs on a shared host. These are narrow benchmark results, not a production throughput guarantee.

| Endpoint | Previous req/s | Updated req/s | Change |
| --- | ---: | ---: | ---: |
| /plaintext | 26,781 | 31,402 | +17.3% |
| /json | 25,375 | 26,858 | +5.8% |

Validated 990,461 HTTP responses with 0 errors.

## Same-code modern versus legacy response modes

Five alternating repeats through the complete in-process ASGI dispatch path. This isolates the serializer choice with identical application code; it excludes network transport.

| Payload | Legacy req/s | Modern req/s | Ratio |
| --- | ---: | ---: | ---: |
| small | 109,662 | 125,168 | 1.14× |
| 1000 rows | 3,753 | 13,626 | 3.63× |

Raw samples and environment details are in `phase2-results.json` and `response-modes-results.json`. The network comparison includes lazy request parsing, routing, dependency, and JSON changes together; it cannot assign gains to each individual change. CPU usage includes startup and warmup and is diagnostic only.

Validation: full suite 889 passed / 29 skipped, including both Admin/CMS browser tests; two additional contract cases passed afterward (18 contract cases total). Critical Ruff checks and targeted mypy passed.

No speculative response/header allocation rewrite or automatic database indexes were added. Database tuning guidance is documented; actual application query plans determine which indexes help.
