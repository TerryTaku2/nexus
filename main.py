"""
main.py — NeXus Platform combined API entry point.
Merges Login, Toolkit, Government, Community, and Search APIs into one app
so they share a single SQLite database and deploy as one service on Render.
"""
import os
import sys
import importlib.util

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.routing import Mount

app = FastAPI(title="NeXus Platform API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helper: load a sub-module by file path ─────────────────────────────────
def _load(rel_path: str):
    abs_path = os.path.join(BASE_DIR, rel_path)
    mod_dir  = os.path.dirname(abs_path)
    if mod_dir not in sys.path:
        sys.path.insert(0, mod_dir)
    spec = importlib.util.spec_from_file_location(
        rel_path.replace(os.sep, "_").replace(" ", "_"), abs_path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Paths that belong to the main app — skip when copying sub-app routes ───
_SKIP_PATHS = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc", "/"}


def _merge(sub_app):
    """Copy HTTP and WebSocket routes from a sub-app into the main app."""
    for route in sub_app.routes:
        if isinstance(route, Mount):
            continue  # skip StaticFiles mounts — frontend is hosted separately
        if getattr(route, "path", "") in _SKIP_PATHS:
            continue
        app.routes.append(route)


# ── Load every sub-module and merge its routes ─────────────────────────────
login_mod     = _load("login/login_api.py")
toolkit_mod   = _load("Toolkit/Toolkit_API.py")
govt_mod      = _load("Pillar 2- Government/government_api.py")
search_mod    = _load("Search/Search_API.py")
community_mod = _load("Pillar 1- Networking/Community.py")

for mod in [login_mod, toolkit_mod, govt_mod, search_mod, community_mod]:
    _merge(mod.app)


# ── Startup: create DB if missing, run migrations, load SMTP, scheduler ────
@app.on_event("startup")
async def on_startup():
    db_path = os.path.join(BASE_DIR, "Database", "Nexus.db")

    # Auto-create the database if it doesn't exist (first deploy on Render)
    if not os.path.exists(db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        db_spec = importlib.util.spec_from_file_location(
            "nexus_db", os.path.join(BASE_DIR, "Database", "Nexus Database.py")
        )
        db_mod = importlib.util.module_from_spec(db_spec)
        db_spec.loader.exec_module(db_mod)
        db_mod.create_database(db_path)
        print(f"[startup] Database created at {db_path}")
    else:
        print(f"[startup] Database found at {db_path}")

    toolkit_mod._run_db_migrations()
    toolkit_mod._load_smtp_from_db()

    if toolkit_mod.SCHEDULER_AVAILABLE:
        toolkit_mod._scheduler.add_job(
            toolkit_mod.run_daily_notifications, "cron", hour=8, minute=0
        )
        toolkit_mod._scheduler.start()


@app.on_event("shutdown")
async def on_shutdown():
    if toolkit_mod.SCHEDULER_AVAILABLE:
        toolkit_mod._scheduler.shutdown()


# ── Local dev entry point ──────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=True,
    )
