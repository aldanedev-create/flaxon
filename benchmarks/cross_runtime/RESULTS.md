# HTTP benchmark results

Measured on 2026-10-09 UTC. These are local HTTP microbenchmarks, not a developer-productivity study.

## Environment

- **python**: 3.12.14 (main, Aug 25 2026, 14:00:49) [Clang 22.1.3 ]
- **node**: v24.19.0
- **go**: go version go1.27.2 linux/amd64
- **flaxon**: 0.2.7
- **uvicorn**: 0.54.0
- **uvloop**: 0.23.0
- **httptools**: 0.8.0
- **os**: Linux-6.18.44-x86_64-with-glibc2.39
- **cpu_model**: AMD EPYC 9V74 80-Core Processor
- **cpu_quota**: 800000 100000
- **affinity**: [0, 1]
- **git_revision**: ac4ec523010f1d625e0ca78ece7c63b0423167cf
- **flaxon_distribution_metadata**: 0.2.6
- **flaxon_source**: /workspace/scratch/67da7b153f3e/flaxon-orm/src/flaxon/__init__.py

## Method

One server worker pinned to one CPU; client pinned to another. 32 persistent connections, no pipelining. One-second warmup, three five-second samples per endpoint/runtime, randomized order. Plaintext bytes and JSON values were checked on every response. Flaxon uses Uvicorn with uvloop and httptools. Node uses core HTTP; Go uses net/http with GOMAXPROCS=1. No database, TLS, authentication, Admin, CMS, or optional middleware.

| Endpoint | Server | Median requests/s | Sample range | Median run p95 (ms) | Invalid responses |
|---|---|---:|---:|---:|---:|
| /plaintext | Flaxon | 14,291 | 11,828–15,210 | 3.319 | 0 |
| /plaintext | Node.js | 65,768 | 65,001–67,357 | 0.881 | 0 |
| /plaintext | Go | 90,614 | 87,406–92,102 | 0.797 | 0 |
| /json | Flaxon | 12,548 | 11,913–13,947 | 3.689 | 0 |
| /json | Node.js | 60,786 | 56,856–60,836 | 0.935 | 0 |
| /json | Go | 78,974 | 78,632–95,499 | 0.864 | 0 |

## Throughput differences

- /plaintext: Flaxon processed 21.7% of Node.js's request rate (78.3% lower throughput); Node.js was 4.60× as fast by this measure.
- /plaintext: Flaxon processed 15.8% of Go's request rate (84.2% lower throughput); Go was 6.34× as fast by this measure.
- /json: Flaxon processed 20.6% of Node.js's request rate (79.4% lower throughput); Node.js was 4.84× as fast by this measure.
- /json: Flaxon processed 15.9% of Go's request rate (84.1% lower throughput); Go was 6.29× as fast by this measure.

## CPU and limitations

- Flaxon: client CPU 23.4–27.3% of one core; server CPU including startup/warmup 100.4–101.7% of one core.
- Node.js: client CPU 61.8–68.1% of one core; server CPU including startup/warmup 98.4–99.6% of one core.
- Go: client CPU 77.0–80.5% of one core; server CPU including startup/warmup 95.7–96.6% of one core.

Server CPU includes startup and warmup, so it can exceed 100% when normalized only over warmup plus measured duration. Client CPU is measured during the sample, with small startup overhead. This is a shared virtual machine; repeats are short. Closed-loop latency does not represent behavior under a fixed overloaded arrival rate. The client shares the host and faster servers may approach its capacity. Results should be repeated on dedicated hardware, with longer runs and a separate load machine, before making public performance claims.

The measured endpoints do not justify claiming Flaxon is on par with Node.js or Go. Application-level results may differ when databases and other I/O dominate.

## Development improvement and fewer bugs

**Development time reduction: unmeasured. Developer defect reduction: unmeasured.** No human development study was conducted, and neither percentage can be inferred from HTTP throughput, generated code, or passing tests.

Observed HTTP response failure rate is 0% if all samples have zero errors; this describes these benchmark requests only. It is not evidence of a 0% developer defect rate or of fewer bugs than another framework.

See README.md for a controlled study design and separate time-reduction, throughput-improvement, and defect-reduction formulas.

Raw per-run data: results.json. Reproduce with run.py.
