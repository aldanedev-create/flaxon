import http from 'node:http';
const server = http.createServer((req, res) => {
  if (req.url === '/plaintext') {
    const body = 'Hello, World!';
    res.writeHead(200, {'Content-Type': 'text/plain; charset=utf-8', 'Content-Length': Buffer.byteLength(body)});
    res.end(body);
  } else if (req.url === '/json') {
    const body = JSON.stringify({message: 'Hello, World!'});
    res.writeHead(200, {'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body)});
    res.end(body);
  } else { res.writeHead(404); res.end(); }
});
server.listen(Number(process.env.PORT), '127.0.0.1');
