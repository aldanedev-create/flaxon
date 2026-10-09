"""Profile framework dispatch independently of network/client overhead."""
import asyncio,cProfile,json,pathlib,pstats
from flaxon import Flaxon
app=Flaxon('profile',debug=False)
@app.get('/json')
async def endpoint():
    return {'message':'Hello, World!'}
async def exercise():
    async def receive():
        return {'type':'http.request','body':b''}
    async def send(message):
        pass
    for _ in range(5000):
        await app({'type':'http','method':'GET','path':'/json','headers':[], 'query_string':b''},receive,send)
profiler=cProfile.Profile()
profiler.enable();asyncio.run(exercise());profiler.disable()
rows=[]
for (filename,line,function),(primitive,calls,self_time,total_time,callers) in pstats.Stats(profiler).stats.items():
    if '/flaxon/' in filename or function in {'signature','get_type_hints'}:
        rows.append({'file':filename,'line':line,'function':function,'calls':calls,'self_seconds':self_time,'cumulative_seconds':total_time})
print(json.dumps(sorted(rows,key=lambda r:r['cumulative_seconds'],reverse=True),indent=2))
