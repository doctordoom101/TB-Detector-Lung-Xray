from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.database import engine, Base
from app.models.user import User
from app.models.prediction import Prediction
from app.core.config import settings
from app.routers import auth, prediction

# Membuat tabel database SQLite di awal startup jika belum ada
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tuberculosis Detection API with Modular Architecture")

# Konfigurasi CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pastikan folder uploads tersedia untuk menyimpan gambar
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Mount folder static agar gambarnya bisa diakses lewat URL
app.mount("/static", StaticFiles(directory=settings.UPLOAD_DIR), name="static")

# Daftarkan Router modul-modul API
app.include_router(auth.router)
app.include_router(prediction.router)
