"""Run: python run.py --go /path/to/go (requires Node and Uvicorn)."""
import argparse, hashlib, json, os, pathlib, platform, random, socket, statistics, subprocess, sys, time
ROOT=pathlib.Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--go',required=True)
parser.add_argument('--runtimes', default=None)
parser.add_argument('--paths', nargs='+', default=['/plaintext','/json'])
parser.add_argument('--flaxon-app', default='flaxon_app:app')
parser.add_argument('--baseline-source', default=None)
parser.add_argument('--output', default='results.json')
parser.add_argument('--seconds',type=float,default=5)
parser.add_argument('--repeats',type=int,default=3)
args=parser.parse_args()
cpus=sorted(os.sched_getaffinity(0)); server_cpu,client_cpu=cpus[:2]
binary=ROOT/'go-server'
subprocess.run([args.go,'build','-o',str(binary),str(ROOT/'go_server.go')],check=True)
commands={
 'Flaxon':[sys.executable,'-m','uvicorn',args.flaxon_app,'--host','127.0.0.1','--port','8765','--workers','1','--loop','uvloop','--http','httptools','--no-access-log','--log-level','error'],
 'Node.js':[ 'node',str(ROOT/'node_server.mjs')],
 'Go':[str(binary)]}
for name, target in [('FastAPI', 'fastapi_app'), ('Starlette', 'starlette_app')]:
 commands[name] = [*commands['Flaxon']]
 commands[name][3] = 'python_servers:' + target
for name in ['Litestar', 'Sanic', 'Falcon']:
 commands[name] = commands['Flaxon'].copy()
 commands[name][3] = 'framework_apps:' + name.lower() + '_app'
if args.flaxon_app == 'framework_apps:flaxon_app':
 for name in ['FastAPI', 'Starlette']:
  commands[name][3] = 'framework_apps:' + name.lower() + '_app'
if args.baseline_source:
 commands['Flaxon baseline'] = commands['Flaxon'].copy()
if args.runtimes:
 commands = {name: command for name, command in commands.items() if name in args.runtimes.split(',')}
from importlib.metadata import version, PackageNotFoundError
import flaxon
result={'environment':{'python':sys.version,'node':subprocess.check_output(['node','--version'],text=True).strip(),'go':subprocess.check_output([args.go,'version'],text=True).strip(),'flaxon':flaxon.__version__,'flaxon_distribution_metadata':version('flaxon'),'flaxon_source':flaxon.__file__,'fastapi':version('fastapi'),'starlette':version('starlette'),'uvicorn':version('uvicorn'),'uvloop':version('uvloop'),'httptools':version('httptools'),'os':platform.platform(),'cpu_model':next((s.split(':',1)[1].strip() for s in pathlib.Path('/proc/cpuinfo').read_text().splitlines() if s.startswith('model name')),''),'cpu_quota':pathlib.Path('/sys/fs/cgroup/cpu.max').read_text().strip(),'affinity':[server_cpu,client_cpu],'git_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()},'method':{'seconds':args.seconds,'repeats':args.repeats,'concurrency':32,'warmup_seconds':1,'workers':1,'seed':42,'client':'Node raw TCP HTTP/1.1 keepalive, no pipelining','caveat':'Shared virtual host; client and server pinned to separate CPUs; core Node and Go servers, not full-stack frameworks.'},'runs':[],'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.iterdir() if p.suffix in {'.py','.mjs','.go'}}}
for package in ['litestar', 'sanic', 'falcon']:
 try:
  result['environment'][package] = version(package)
 except PackageNotFoundError:
  continue
def load(path,seconds):
 row = json.loads(subprocess.check_output(['taskset','-c',str(client_cpu),'node',str(ROOT/('load.mjs' if path in {'/session','/db'} or path.startswith('/validate') else 'load-stateless.mjs')),'8765',path,str(seconds),'32'],text=True))
 if row['errors'] or row['requests'] == 0:
  raise RuntimeError('Invalid benchmark responses: ' + json.dumps(row))
 return row
schedule=[(name,path,rep) for rep in range(args.repeats) for name in commands for path in args.paths]
random.Random(42).shuffle(schedule)
for name,path,rep in schedule:
 with open(ROOT/'server.log','w') as log:
  server=subprocess.Popen(['taskset','-c',str(server_cpu),*commands[name]],cwd=ROOT,env={**os.environ,'PORT':'8765', **({'PYTHONPATH':args.baseline_source} if name == 'Flaxon baseline' else {})},stdout=log,stderr=log)
  try:
   deadline=time.monotonic()+15
   while True:
    if server.poll() is not None: raise RuntimeError((ROOT/'server.log').read_text())
    try:
     with socket.create_connection(('127.0.0.1',8765),.1):break
    except OSError:
     if time.monotonic()>deadline:raise
     time.sleep(.05)
   load(path,1)
   row={'runtime':name,'path':path,'repeat':rep,**load(path,args.seconds)}
  finally:
   server.terminate()
   _, status, usage = os.wait4(server.pid, 0)
   server.returncode = os.waitstatus_to_exitcode(status)
  # Includes startup and one-second warmup; normalize over warmup + sample.
  row['server_cpu_seconds_including_warmup'] = usage.ru_utime + usage.ru_stime
  row['server_cpu_percent_including_warmup'] = 100*(usage.ru_utime + usage.ru_stime)/(row['seconds']+1)
  row['client_cpu_percent'] = 100*row['client_cpu_seconds']/row['seconds']
  result['runs'].append(row)
  (ROOT/args.output).write_text(json.dumps(result,indent=2)+'\n')
  print(json.dumps(row),flush=True)
result['summary']=[]
for path in args.paths:
 for name in commands:
  rows=[r for r in result['runs'] if r['runtime']==name and r['path']==path]
  result['summary'].append({'runtime':name,'path':path,'median_rps':statistics.median(r['rps'] for r in rows),'min_rps':min(r['rps'] for r in rows),'max_rps':max(r['rps'] for r in rows),'median_p95_ms':statistics.median(r['p95_ms'] for r in rows),'errors':sum(r['errors'] for r in rows)})
(ROOT/args.output).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result['summary'],indent=2))
binary.unlink()
