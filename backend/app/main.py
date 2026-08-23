from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, chat, dashboard

app = FastAPI(
    title="ParcelPilot Support AI",
    description="AI-powered support system for ParcelPilot",
    version="1.0.0",
    redirect_slashes=False,  # Prevent 307 redirects that strip Authorization header
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_origin_regex=r"https://.*\.onrender\.com|http://localhost:\d+|http://127\.0\.0\.1:\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth")
app.include_router(chat.router, prefix="/api/chat")
app.include_router(dashboard.router, prefix="/api/dashboard")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "ParcelPilot Support AI"}
