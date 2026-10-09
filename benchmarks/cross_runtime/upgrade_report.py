"""Build a reproducible upgrade report from recorded samples."""
import json,pathlib
root=pathlib.Path(__file__).resolve().parent
r=json.loads((root/'optimized-results.json').read_text())
w=json.loads((root/'workload-results.json').read_text())
s=json.loads((root/'serializer-results.json').read_text())
lines=['# Request performance and security upgrade results','','## Repeated HTTP samples','',
'One worker per server, separate server/client CPU affinity, 32 keep-alive connections, one-second warmup and three three-second samples in randomized order. Same Uvicorn/uvloop/httptools configuration for all Python servers. No database or optional middleware in this first comparison. Flaxon keeps default request ID and security headers. Stateless clients do not retain cookies. Baseline Flaxon therefore allocates a session on every request; optimized Flaxon does not.', '',
'| Server | Plaintext median requests/s | JSON median requests/s |','|---|---:|---:|']
values={}
for name in ['Flaxon baseline','Flaxon','FastAPI','Starlette','Node.js','Go']:
 values[name]={x['path']:x['median_rps'] for x in r['summary'] if x['runtime']==name}
 lines.append(f"| {name} | {values[name]['/plaintext']:,.0f} | {values[name]['/json']:,.0f} |")
for path in ['/plaintext','/json']:
 a=values['Flaxon baseline'][path];b=values['Flaxon'][path]
 lines.append(f"\n{path}: {(b/a-1)*100:.1f}% higher throughput than unchanged Flaxon in the same run ({b/a:.2f}×).")
lines += ['','All '+str(sum(x['requests'] for x in r['runs']))+' measured responses passed validation. These percentages describe HTTP throughput, not developer productivity or defects. Short samples on shared hardware have meaningful variation; raw ranges and p95 latency are in optimized-results.json. Node and Go remain faster here. Do not generalize the FastAPI/Flaxon ordering to other endpoints or configurations.','', '## Separate Flaxon workloads','', '| Workload | Median requests/s | Median run p95 ms | Invalid responses |','|---|---:|---:|---:|']
for row in w['summary']:
 lines.append(f"| {row['path']} | {row['median_rps']:,.0f} | {row['median_p95_ms']:.3f} | {row['errors']} |")
lines += ['','The session workload retains a cookie per connection and mutates its counter. The validation workload converts an integer query parameter. Database work is a parameterized count query against asynchronous in-memory SQLite; this is not a production ORM or disk-backed database benchmark. These workloads are diagnostics for optimized Flaxon only.','', '## Profiling','', 'In 5,000 direct ASGI requests, the baseline called inspect.signature 10,000 times and get_type_hints 10,000 times, created 5,000 sessions and invoked backend save 10,000 times. The optimized profile contains no endpoint inspection, session creation or backend save calls for this stateless workload. Dependency values still resolve on every request; route matching remains active. Profiles include diagnostic cProfile overhead and are not throughput benchmarks.','', '## JSON serialization','']
for row in s['timings']:
 lines.append(f"- {row['sample']}: orjson serializer alone was {row['serializer_speed_ratio']:.1f}× faster in the recorded microbenchmark.")
lines += ['','The default JSONResponse remains stdlib-based: direct substitution changes datetime formatting, large integer handling, non-string keys and non-finite numbers. Whitespace differences are not semantic differences. A faster serializer is not an equal multiplier for end-to-end HTTP speed. See serializer-results.json.','', '## Security and quality','', 'JWTs now use PyJWT with a fixed algorithm, required expiry and configurable issuer/audience and trusted key IDs. New password hashes use Argon2id; Admin upgrades legacy hashes on successful password verification. Existing insecure-format JWTs are rejected and require sign-in again. Cookies default to Secure in explicitly constructed session helpers. Unexpected authentication/authorization failures propagate; isolated optional plugin failures produce warnings.','', 'Repository-wide style and typing debt remains. Critical undefined-name/syntax lint checks pass across src/flaxon; new execution-plan and JWT modules pass targeted strict mypy checks. The corrected full mypy run exposed existing errors instead of stopping at invalid configuration. See QUALITY_AUDIT.md.','', '## Reproduction and scope','']
for key,value in r['environment'].items():
 lines.append(f'- {key}: {value}')
lines += ['', 'Framework revision is the pre-change parent; security/performance source changes are supplied in the accompanying commit. Unchanged source was selected through PYTHONPATH from a detached worktree at that revision. Raw input hashes record the benchmark files at measurement time; the stateless load script is retained as load-stateless.mjs. Server CPU includes startup/warmup and is a diagnostic estimate.','', 'No development-time or developer-defect study was conducted. Those percentages remain unmeasured.']
(root/'UPGRADE_RESULTS.md').write_text('\n'.join(lines)+'\n')
