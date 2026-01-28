from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import sqlite3
from datetime import datetime

app = FastAPI()
templates = Jinja2Templates(directory="templates")

ALLOWED_USERS = {"jatin", "rajesh", "kartik"}
connections = {}

# ---------------- DB SETUP ----------------
def get_db():
    return sqlite3.connect("chat.db", check_same_thread=False)

def init_db():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            text TEXT,
            timestamp TEXT
        )
    """)
    db.commit()
    db.close()

init_db()
# ------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@app.websocket("/ws/{username}")
async def websocket_chat(websocket: WebSocket, username: str):
    if username not in ALLOWED_USERS:
        await websocket.close()
        return

    await websocket.accept()
    connections[username] = websocket

    # 🔹 Send old messages to newly connected user
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT sender, text FROM messages ORDER BY id")
    old_messages = cursor.fetchall()
    db.close()

    for sender, text in old_messages:
        await websocket.send_json({
            "sender": sender,
            "text": text
        })

    try:
        while True:
            message = await websocket.receive_text()

            # 🔹 Save message to DB
            db = get_db()
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO messages (sender, text, timestamp) VALUES (?, ?, ?)",
                (username, message, datetime.now().isoformat())
            )
            db.commit()
            db.close()

            # 🔹 Broadcast message (SAME LOGIC)
            for conn in connections.values():
                await conn.send_json({
                    "sender": username,
                    "text": message
                })

    except WebSocketDisconnect:
        del connections[username]
