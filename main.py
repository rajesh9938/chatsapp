from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import sqlite3
from datetime import datetime

app = FastAPI()
templates = Jinja2Templates(directory="templates")

ALLOWED_USERS = {"jatin", "rajesh", "kartik"}

# room_name -> {username: websocket}
rooms = {}

# ---------- DB ----------
def get_db():
    return sqlite3.connect("chat.db", check_same_thread=False)

def init_db():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            room TEXT,
            text TEXT,
            timestamp TEXT
        )
    """)
    db.commit()
    db.close()

init_db()
# ------------------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@app.websocket("/ws/{username}/{room}")
async def websocket_chat(websocket: WebSocket, username: str, room: str):

    if username not in ALLOWED_USERS:
        await websocket.close()
        return

    await websocket.accept()

    if room not in rooms:
        rooms[room] = {}

    rooms[room][username] = websocket

    # 🔹 send room-specific old messages
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT sender, text FROM messages WHERE room=? ORDER BY id",
        (room,)
    )
    history = cursor.fetchall()
    db.close()

    for sender, text in history:
        await websocket.send_json({
            "sender": sender,
            "text": text
        })

    try:
        while True:
            text = await websocket.receive_text()

            # save message
            db = get_db()
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO messages (sender, room, text, timestamp) VALUES (?, ?, ?, ?)",
                (username, room, text, datetime.now().isoformat())
            )
            db.commit()
            db.close()

            # broadcast to same room
            for ws in rooms[room].values():
                await ws.send_json({
                    "sender": username,
                    "text": text
                })

    except WebSocketDisconnect:
        del rooms[room][username]
        if not rooms[room]:
            del rooms[room]
