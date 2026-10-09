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
 let buffer=Buffer.alloc(0), sent, cookie='';
 const socket=net.createConnection({host:'127.0.0.1',port:Number(port)});
 sockets.push(socket);
 const send=()=>{sent=performance.now();socket.write(cookie ? request.toString().replace('Connection:', `Cookie: ${cookie}\r\nConnection:`) : request);};
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
  if(!match){errors++;finish();return;}
  const size=Number(match[1]);if(buffer.length<split+4+size)return;
  const body=buffer.subarray(split+4,split+4+size).toString();
  let valid = body === expected;
  if(path === '/json') { try { const value=JSON.parse(body); valid=value.message === 'Hello, World!' && Object.keys(value).length === 1; } catch { valid=false; } }
  if(path.startsWith('/validate')) { try { valid=JSON.parse(body).n === 123; } catch { valid=false; } }
  if(path === '/session' || path === '/db') { try { const value=JSON.parse(body).count; valid=Number.isInteger(value) && value>0 && (path !== '/db' || value === 25); } catch { valid=false; } }
  const sessionCookie=/set-cookie:\s*([^;\r\n]+)/i.exec(header);
  if(path === '/session' && sessionCookie) cookie=sessionCookie[1];
  if(!header.startsWith('HTTP/1.1 200') || !valid)errors++;
  completed++;latencies.push(performance.now()-sent);
  buffer=buffer.subarray(split+4+size);
  if(performance.now()<end)send();
 });
 socket.on('error',()=>{errors++;if(start)finish();else process.exit(1);});
}
