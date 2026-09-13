import os
import threading
from typing import Optional
from fastapi import FastAPI, Query, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import database
import scraper

app = FastAPI(
    title="Aggregatore Associazioni Pordenone",
    description="Feed bacheca comunicati ed eventi aggregati da Facebook",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Lock per evitare esecuzioni concorrenti dello scraper
sync_lock = threading.Lock()
is_syncing = False

@app.on_event("startup")
def startup_event():
    database.init_db()

@app.get("/")
def serve_home():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({"status": "Frontend not ready yet"}, status_code=200)

@app.get("/api/posts")
def api_get_posts(
    association: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    posts = database.get_posts(association=association, search=search)
    return {"count": len(posts), "posts": posts}

@app.get("/api/events")
def api_get_events(
    association: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    events = database.get_events(association=association, status=status, search=search)
    return {"count": len(events), "events": events}

@app.get("/api/stats")
def api_get_stats():
    stats = database.get_stats()
    stats["is_syncing"] = is_syncing
    return stats

def background_sync_task():
    global is_syncing
    with sync_lock:
        is_syncing = True
        try:
            scraper.run_sync()
        except Exception as e:
            database.log_sync("ERROR", 0, 0, f"Errore sync: {str(e)}")
        finally:
            is_syncing = False

@app.post("/api/sync")
def api_trigger_sync(background_tasks: BackgroundTasks):
    global is_syncing
    if is_syncing:
        return JSONResponse(
            {"success": False, "message": "Una sincronizzazione è già in corso nel browser!"},
            status_code=409
        )
    background_tasks.add_task(background_sync_task)
    return {"success": True, "message": "Sincronizzazione avviata in background con Playwright."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
