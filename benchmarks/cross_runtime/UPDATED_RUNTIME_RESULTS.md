# Updated Flaxon versus Node.js, Go and FastAPI

Measured after commit c4dcd93 (default orjson and request dispatch improvements). Three randomized five-second samples for each endpoint/runtime; medians shown. One server worker, 32 keepalive connections, separate pinned server and client CPUs, AMD EPYC 9V74 shared host.

| Runtime | Plaintext req/s | Plaintext p95 ms | JSON req/s | JSON p95 ms |
| --- | ---: | ---: | ---: | ---: |
| Flaxon | 20,366 | 2.426 | 19,657 | 2.068 |
| FastAPI | 13,032 | 3.215 | 13,664 | 3.377 |
| Node.js | 58,314 | 0.996 | 61,532 | 0.996 |
| Go | 60,504 | 1.078 | 67,537 | 1.166 |

Validated 4,783,864 measured responses with 0 errors (warmup excluded).

Flaxon throughput for /plaintext was 56.3% higher than FastAPI in this run.
Flaxon throughput for /json was 43.9% higher than FastAPI in this run.

Node and Go are core HTTP servers rather than equivalent full-stack frameworks. Flaxon and FastAPI run identical Uvicorn/uvloop/httptools settings. Endpoints return a fixed small response with no database, authentication, templates, or application middleware. These results do not establish equivalent performance for real applications or measure development speed or bug rates. p95 values are medians of per-sample p95s, not a pooled percentile.

Versions: Python 3.12.14, Node v24.19.0, go version go1.27.2 linux/amd64, FastAPI 0.143.0. Flaxon source reports 0.2.7 and includes unreleased PR #10; editable distribution metadata still reports 0.2.6. The exact source revision and raw samples are recorded in updated-runtime-results.json.

Reproduce:
```bash
python benchmarks/cross_runtime/run.py --go /path/to/go --runtimes Flaxon,Node.js,Go,FastAPI --seconds 5 --repeats 3 --output updated-runtime-results.json
```
