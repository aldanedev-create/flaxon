# Request performance and security upgrade results

## Repeated HTTP samples

One worker per server, separate server/client CPU affinity, 32 keep-alive connections, one-second warmup and three three-second samples in randomized order. Same Uvicorn/uvloop/httptools configuration for all Python servers. No database or optional middleware in this first comparison. Flaxon keeps default request ID and security headers. Stateless clients do not retain cookies. Baseline Flaxon therefore allocates a session on every request; optimized Flaxon does not.

| Server | Plaintext median requests/s | JSON median requests/s |
|---|---:|---:|
| Flaxon baseline | 13,765 | 13,675 |
| Flaxon | 24,730 | 22,637 |
| FastAPI | 16,579 | 13,350 |
| Starlette | 32,759 | 30,349 |
| Node.js | 62,049 | 65,175 |
| Go | 90,274 | 86,657 |

/plaintext: 79.7% higher throughput than unchanged Flaxon in the same run (1.80×).

/json: 65.5% higher throughput than unchanged Flaxon in the same run (1.66×).

All 4237972 measured responses passed validation. These percentages describe HTTP throughput, not developer productivity or defects. Short samples on shared hardware have meaningful variation; raw ranges and p95 latency are in optimized-results.json. Node and Go remain faster here. Do not generalize the FastAPI/Flaxon ordering to other endpoints or configurations.

## Separate Flaxon workloads

| Workload | Median requests/s | Median run p95 ms | Invalid responses |
|---|---:|---:|---:|
| /session | 16,751 | 3.023 | 0 |
| /validate?n=123 | 19,400 | 2.488 | 0 |
| /db | 12,482 | 3.277 | 0 |

The session workload retains a cookie per connection and mutates its counter. The validation workload converts an integer query parameter. Database work is a parameterized count query against asynchronous in-memory SQLite; this is not a production ORM or disk-backed database benchmark. These workloads are diagnostics for optimized Flaxon only.

## Profiling

In 5,000 direct ASGI requests, the baseline called inspect.signature 10,000 times and get_type_hints 10,000 times, created 5,000 sessions and invoked backend save 10,000 times. The optimized profile contains no endpoint inspection, session creation or backend save calls for this stateless workload. Dependency values still resolve on every request; route matching remains active. Profiles include diagnostic cProfile overhead and are not throughput benchmarks.

## JSON serialization

- small: orjson serializer alone was 16.4× faster in the recorded microbenchmark.
- list: orjson serializer alone was 8.4× faster in the recorded microbenchmark.

The default JSONResponse remains stdlib-based: direct substitution changes datetime formatting, large integer handling, non-string keys and non-finite numbers. Whitespace differences are not semantic differences. A faster serializer is not an equal multiplier for end-to-end HTTP speed. See serializer-results.json.

## Security and quality

JWTs now use PyJWT with a fixed algorithm, required expiry and configurable issuer/audience and trusted key IDs. New password hashes use Argon2id; Admin upgrades legacy hashes on successful password verification. Existing insecure-format JWTs are rejected and require sign-in again. Cookies default to Secure in explicitly constructed session helpers. Unexpected authentication/authorization failures propagate; isolated optional plugin failures produce warnings.

Repository-wide style and typing debt remains. Critical undefined-name/syntax lint checks pass across src/flaxon; new execution-plan and JWT modules pass targeted strict mypy checks. The corrected full mypy run exposed existing errors instead of stopping at invalid configuration. See QUALITY_AUDIT.md.

## Reproduction and scope

- python: 3.12.14 (main, Aug 25 2026, 14:00:49) [Clang 22.1.3 ]
- node: v24.19.0
- go: go version go1.27.2 linux/amd64
- flaxon: 0.2.7
- flaxon_distribution_metadata: 0.2.6
- flaxon_source: /workspace/scratch/67da7b153f3e/flaxon-orm/src/flaxon/__init__.py
- fastapi: 0.143.0
- starlette: 1.7.0
- uvicorn: 0.54.0
- uvloop: 0.23.0
- httptools: 0.8.0
- os: Linux-6.18.44-x86_64-with-glibc2.39
- cpu_model: AMD EPYC 9V74 80-Core Processor
- cpu_quota: 800000 100000
- affinity: [0, 1]
- git_revision: ac4ec523010f1d625e0ca78ece7c63b0423167cf

Framework revision is the pre-change parent; security/performance source changes are supplied in the accompanying commit. Unchanged source was selected through PYTHONPATH from a detached worktree at that revision. Raw input hashes record the benchmark files at measurement time; the stateless load script is retained as load-stateless.mjs. Server CPU includes startup/warmup and is a diagnostic estimate.

No development-time or developer-defect study was conducted. Those percentages remain unmeasured.
