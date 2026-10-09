"""Evaluate serializer speed and compatibility without changing the default."""
import datetime,json,pathlib,statistics,timeit
from decimal import Decimal
import orjson
from flaxon.http.response import _json_default
samples={'small':{'message':'Hello, World!'},'list':{'items':[{'id':n,'title':'Task café','done':False} for n in range(50)]}}
rows=[]
for name,data in samples.items():
 std=lambda:json.dumps(data,ensure_ascii=False,default=_json_default).encode()
 fast=lambda:orjson.dumps(data,default=_json_default)
 assert json.loads(std())==json.loads(fast())
 a=statistics.median(timeit.repeat(std,number=10000,repeat=3))
 b=statistics.median(timeit.repeat(fast,number=10000,repeat=3))
 rows.append({'sample':name,'iterations':10000,'stdlib_seconds':a,'orjson_seconds':b,'serializer_speed_ratio':a/b})
compatibility=[]
for name,value in [('datetime',datetime.datetime(2026,10,9,12,0)),('date',datetime.date(2026,10,9)),('decimal',Decimal('1.25')),('large_integer',2**80),('nonfinite_float',float('nan')),('integer_key',{1:'value'})]:
 def outcome(serialize):
  try:return serialize({'value':value}).decode()
  except (TypeError,ValueError,OverflowError) as exc:return type(exc).__name__
 a=outcome(lambda data:json.dumps(data,ensure_ascii=False,default=_json_default).encode())
 b=outcome(lambda data:orjson.dumps(data,default=_json_default))
 compatibility.append({'sample':name,'stdlib':a,'orjson':b,'same_output':a==b})
result={'orjson_version':orjson.__version__,'timings':rows,'compatibility':compatibility,'decision':'Retain stdlib JSONResponse. Direct orjson substitution changes datetime, integer key, large integer and nonfinite float behavior. Serializer speed is not HTTP or developer productivity speed.'}
pathlib.Path(__file__).with_name('serializer-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
