"""Isolated Flaxon session, validation and in-memory SQLite workloads."""
import aiosqlite
from flaxon import Flaxon
app=Flaxon('workloads',debug=False)
connection=None
@app.on_startup
async def start():
    global connection
    connection=await aiosqlite.connect(':memory:')
    await connection.execute('CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT)')
    await connection.executemany('INSERT INTO tasks VALUES (?, ?)', [(n,'task') for n in range(50)])
    await connection.commit()
@app.on_shutdown
async def stop():
    await connection.close()
@app.get('/session')
async def session(request):
    request.session['count']=request.session.get('count',0)+1
    return {'count':request.session['count']}
@app.get('/validate')
async def validate(n:int):
    return {'n':n}
@app.get('/db')
async def database():
    async with connection.execute('SELECT COUNT(*) FROM tasks WHERE id >= ?', (25,)) as cursor:
        row=await cursor.fetchone()
    return {'count':row[0]}
