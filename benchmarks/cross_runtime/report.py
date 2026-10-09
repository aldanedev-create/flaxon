"""Generate the readable report from the raw samples."""
import json,pathlib,statistics
root=pathlib.Path(__file__).resolve().parent
r=json.loads((root/'results.json').read_text())
lines=['# HTTP benchmark results','', 'Measured on 2026-10-09 UTC. These are local HTTP microbenchmarks, not a developer-productivity study.','', '## Environment','']
for key,value in r['environment'].items():lines.append(f'- **{key}**: {value}')
lines+=['','## Method','', 'One server worker pinned to one CPU; client pinned to another. 32 persistent connections, no pipelining. One-second warmup, three five-second samples per endpoint/runtime, randomized order. Plaintext bytes and JSON values were checked on every response. Flaxon uses Uvicorn with uvloop and httptools. Node uses core HTTP; Go uses net/http with GOMAXPROCS=1. No database, TLS, authentication, Admin, CMS, or optional middleware.','', '| Endpoint | Server | Median requests/s | Sample range | Median run p95 (ms) | Invalid responses |','|---|---|---:|---:|---:|---:|']
for row in r['summary']:
 lines.append(f"| {row['path']} | {row['runtime']} | {row['median_rps']:,.0f} | {row['min_rps']:,.0f}–{row['max_rps']:,.0f} | {row['median_p95_ms']:.3f} | {row['errors']} |")
lines+=['','## Throughput differences','']
for path in ['/plaintext','/json']:
 values={x['runtime']:x['median_rps'] for x in r['summary'] if x['path']==path}
 for baseline in ['Node.js','Go']:
  lines.append(f"- {path}: Flaxon processed {values['Flaxon']/values[baseline]*100:.1f}% of {baseline}'s request rate ({(1-values['Flaxon']/values[baseline])*100:.1f}% lower throughput); {baseline} was {values[baseline]/values['Flaxon']:.2f}× as fast by this measure.")
lines+=['','## CPU and limitations','']
for name in ['Flaxon','Node.js','Go']:
 rows=[x for x in r['runs'] if x['runtime']==name]
 lines.append(f"- {name}: client CPU {min(x['client_cpu_percent'] for x in rows):.1f}–{max(x['client_cpu_percent'] for x in rows):.1f}% of one core; server CPU including startup/warmup {min(x['server_cpu_percent_including_warmup'] for x in rows):.1f}–{max(x['server_cpu_percent_including_warmup'] for x in rows):.1f}% of one core.")
lines+=['', 'Server CPU includes startup and warmup, so it can exceed 100% when normalized only over warmup plus measured duration. Client CPU is measured during the sample, with small startup overhead. This is a shared virtual machine; repeats are short. Closed-loop latency does not represent behavior under a fixed overloaded arrival rate. The client shares the host and faster servers may approach its capacity. Results should be repeated on dedicated hardware, with longer runs and a separate load machine, before making public performance claims.', '', 'The measured endpoints do not justify claiming Flaxon is on par with Node.js or Go. Application-level results may differ when databases and other I/O dominate.', '', '## Development improvement and fewer bugs','', '**Development time reduction: unmeasured. Developer defect reduction: unmeasured.** No human development study was conducted, and neither percentage can be inferred from HTTP throughput, generated code, or passing tests.', '', 'Observed HTTP response failure rate is 0% if all samples have zero errors; this describes these benchmark requests only. It is not evidence of a 0% developer defect rate or of fewer bugs than another framework.', '', 'See README.md for a controlled study design and separate time-reduction, throughput-improvement, and defect-reduction formulas.', '', 'Raw per-run data: results.json. Reproduce with run.py.']
(root/'RESULTS.md').write_text('\n'.join(lines)+'\n')
