// Closed-loop, one outstanding request per connection. No HTTP pipelining.
import net from 'node:net';
import {performance} from 'node:perf_hooks';
const [port, path, duration, concurrency] = process.argv.slice(2);
const request = Buffer.from(`GET ${path} HTTP/1.1\r\nHost: localhost\r\nConnection: keep-alive\r\n\r\n`);
const expected = path === '/json' ? '{"message":"Hello, World!"}' : 'Hello, World!';
const sockets = []; const latencies = [];
let start, end, completed = 0, errors = 0, ready = 0, stopping = false;
const cpuStart = process.cpuUsage();
function finish() {
 if(stopping) return;
 stopping = true;
 const elapsed=(performance.now()-start)/1000;
 for(const s of sockets) s.destroy();
 latencies.sort((a,b)=>a-b);
 const cpu=process.cpuUsage(cpuStart);
 console.log(JSON.stringify({requests:completed,errors,seconds:elapsed,rps:completed/elapsed,p50_ms:latencies[Math.floor(latencies.length*.5)],p95_ms:latencies[Math.floor(latencies.length*.95)],client_cpu_seconds:(cpu.user+cpu.system)/1e6}));
}
for(let i=0;i<Number(concurrency);i++) {
 let buffer=Buffer.alloc(0), sent;
 const socket=net.createConnection({host:'127.0.0.1',port:Number(port)});
 sockets.push(socket);
 const send=()=>{sent=performance.now();socket.write(request);};
 socket.setNoDelay(true);
 socket.on('connect',()=>{
  if(++ready === Number(concurrency)) {
   start=performance.now();end=start+Number(duration)*1000;
   for(const s of sockets) s.emit('begin');
   setTimeout(finish,Number(duration)*1000);
  }
 });
 socket.on('begin',send);
 socket.on('data',data=>{
  buffer=Buffer.concat([buffer,data]);
  const split=buffer.indexOf('\r\n\r\n');if(split<0)return;
  const header=buffer.subarray(0,split).toString();
  const match=/content-length:\s*(\d+)/i.exec(header);
  let body, consumed;
  if(match) {
   const size=Number(match[1]);if(buffer.length<split+4+size)return;
   body=buffer.subarray(split+4,split+4+size).toString(); consumed=split+4+size;
  } else if(/transfer-encoding:\s*chunked/i.test(header)) {
   let offset=split+4; const chunks=[];
   while(true) {
    const lineEnd=buffer.indexOf('\r\n',offset); if(lineEnd<0)return;
    const size=parseInt(buffer.subarray(offset,lineEnd).toString().split(';')[0],16);
    if(!Number.isFinite(size)){errors++;finish();return;}
    offset=lineEnd+2;
    if(size===0) {
     if(buffer.length<offset+2)return;
     if(buffer.subarray(offset,offset+2).toString()!=='\r\n'){errors++;finish();return;}
     consumed=offset+2; body=Buffer.concat(chunks).toString();break;
    }
    if(buffer.length<offset+size+2)return;
    chunks.push(buffer.subarray(offset,offset+size));offset+=size+2;
   }
  } else {errors++;finish();return;}
  let valid = body === expected;
  if(path === '/json') { try { const value=JSON.parse(body); valid=value.message === 'Hello, World!' && Object.keys(value).length === 1; } catch { valid=false; } }
  if(path === '/large-json') { try { const rows=JSON.parse(body); valid=Array.isArray(rows) && rows.length === 1000 && rows.every((v,i)=>v.id===i && v.name===`Task ${i}` && v.done===false && Object.keys(v).length===3); } catch { valid=false; } }
  if(path.startsWith('/routes/')) { try { const v=JSON.parse(body); valid=v.id===42 && v.route===999 && Object.keys(v).length===2; } catch { valid=false; } }
  if(!header.startsWith('HTTP/1.1 200') || !valid)errors++;
  completed++;latencies.push(performance.now()-sent);
  buffer=buffer.subarray(consumed);
  if(performance.now()<end)send();
 });
 socket.on('error',()=>{errors++;if(start)finish();else process.exit(1);});
}
