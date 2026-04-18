import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from routers import chat, ingest

app = FastAPI(
    title="AI Urbanistica API",
    description="RAG System per la normativa urbanistica italiana (Nazionale, Regionale, Provinciale, Comunale)",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(ingest.router, prefix="/api", tags=["Ingestion"])

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

# Integrazione del frontend React (serve the frontend/dist folder)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
frontend_dist = os.path.join(os.path.dirname(BASE_DIR), "frontend", "dist")

if os.path.exists(frontend_dist):
    # Serve i file statici (CSS, JS, immagini)
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    
    # Catch-all route per servire l'index.html di React e per tutto quello che non inizia per /api/
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Ignora l'URL se la richiesta dovesse comunque finire sull'API (anche se dovrebbe essere intercettata prima)
        if full_path.startswith("api/"):
            return {"error": "Endpoint not found"}
        
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"error": "Frontend non trovato o non compilato."}
