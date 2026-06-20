from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import tensorflow as tf
import uuid
import os
import json
from fastapi.responses import StreamingResponse

# Import komponen lokal kamu
import models_db
import utils
import auth_utils
import firebase_config 
from database import SessionLocal

app = FastAPI(title="Tuberculosis Detection API with Local Auth & FCM")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pastikan folder uploads tersedia untuk menyimpan gambar
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Daftarkan folder uploads agar gambarnya bisa diakses lewat URL browser
app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")

# Load model .keras utama kamu (Muat di awal startup biar kencang)
MODEL_CLS_PATH = "../model/mobilenetv2/best_mobilenetv2_model.keras" 
MODEL_SEG_PATH = "../model/unet/best_unet.keras"

print("Loading Models...")
model_cls = tf.keras.models.load_model(MODEL_CLS_PATH)
model_seg = tf.keras.models.load_model(MODEL_SEG_PATH, compile=False)

# Fungsi pembantu untuk memanggil session database (Dependency Injection)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic Schemas untuk Registrasi & Login
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Keamanan Bearer Token JWT
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Dependency injection untuk mengecek validitas token JWT user lokal"""
    token = credentials.credentials
    payload = auth_utils.decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid atau telah kedaluwarsa.",
        )
    email = payload.get("sub")
    user = db.query(models_db.User).filter(models_db.User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User tidak ditemukan.",
        )
    return user


# --- AUTH ENDPOINTS ---

@app.post("/auth/register")
async def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    """Endpoint untuk mendaftarkan akun baru secara lokal"""
    # Cek apakah email sudah terdaftar
    existing_user = db.query(models_db.User).filter(models_db.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email ini sudah terdaftar."
        )
    
    # Hash password dan simpan ke database
    hashed_password = auth_utils.get_password_hash(user_data.password)
    new_user = models_db.User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"status": "success", "message": "Registrasi akun berhasil!"}

@app.post("/auth/login")
async def login_user(login_data: UserLogin, db: Session = Depends(get_db)):
    """Endpoint Login untuk mendapatkan Access Token JWT"""
    user = db.query(models_db.User).filter(models_db.User.email == login_data.email).first()
    if not user or not auth_utils.verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah."
        )
    
    # Generate Token JWT
    access_token = auth_utils.create_access_token(data={"sub": user.email})
    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": user.email,
            "full_name": user.full_name
        }
    }


# --- PREDICTION & HISTORY ENDPOINTS ---

@app.post("/predict")
async def predict_xray(
    file: UploadFile = File(...), 
    fcm_token: str = None, 
    db: Session = Depends(get_db),
    current_user: models_db.User = Depends(get_current_user)
):
    """Endpoint Prediksi yang diproteksi JWT Token"""
    # 1. Generate nama file unik menggunakan UUID agar tidak bentrok
    file_id = str(uuid.uuid4())
    file_ext = file.filename.split(".")[-1]
    
    orig_filename = f"{file_id}_orig.{file_ext}"
    vis_filename = f"{file_id}_vis.png"
    
    orig_path = os.path.join(UPLOAD_DIR, orig_filename)
    vis_path = os.path.join(UPLOAD_DIR, vis_filename)

    # 2. Simpan gambar asli dari user ke server lokal
    with open(orig_path, "wb") as buffer:
        buffer.write(await file.read())

    async def generate_steps():
        # 3. Jalankan Preprocessing & Prediksi Klasifikasi (MobileNetV2)
        img_cls_tensor = utils.preprocess_classification(orig_path)
        cls_predictions = model_cls.predict(img_cls_tensor)
        confidence = float(cls_predictions[0][0])
        
        label = "Tuberculosis" if confidence > 0.5 else "Normal"
        display_confidence = confidence if label == "Tuberculosis" else (1.0 - confidence)

        # 4. Simpan catatan AWAL ke SQLite Database (terikat dengan ID user yang login)
        db_record = models_db.Prediction(
            prediction_label=label,
            confidence_score=display_confidence,
            image_path=orig_path,
            vis_path=None,
            user_id=current_user.id
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)

        # 5. Kirim respon KLASIFIKASI dulu
        first_output = {
            "id": db_record.id,
            "prediction": label,
            "confidence": f"{display_confidence * 100:.2f}%",
            "original_image_url": f"/static/{orig_filename}",
            "segmentation_image_url": None, 
            "created_at": db_record.created_at.isoformat() if db_record.created_at else None
        }
        yield json.dumps(first_output) + "\n"

        # 6. Jalankan Lung Segmentation (U-Net) & Save Overlay
        img_seg_tensor = utils.preprocess_segmentation(orig_path)
        utils.save_segmentation_overlay(model_seg, img_seg_tensor, orig_path, vis_path)

        # 7. Update catatan dengan vis_path
        db_record.vis_path = vis_path
        db.commit()

        # 8. Kirim respon LENGKAP
        final_output = first_output.copy()
        final_output["segmentation_image_url"] = f"/static/{vis_filename}"
        yield json.dumps(final_output) + "\n"

        # 9. KIRIM PUSH NOTIFICATION VIA FCM jika token disediakan dari Flutter
        if fcm_token:
            firebase_config.send_fcm_notification(
                token=fcm_token,
                title="Hasil Deteksi Tuberkulosis Selesai",
                body=f"Halo {current_user.full_name or 'User'}, pemeriksaan menunjukkan status: {label} dengan akurasi {display_confidence * 100:.2f}%."
            )

    return StreamingResponse(generate_steps(), media_type="application/x-ndjson")

@app.get("/history")
async def get_user_history(
    db: Session = Depends(get_db),
    current_user: models_db.User = Depends(get_current_user)
):
    """Mengambil riwayat data deteksi spesifik milik user yang sedang login saja"""
    records = db.query(models_db.Prediction)\
        .filter(models_db.Prediction.user_id == current_user.id)\
        .order_by(models_db.Prediction.created_at.desc())\
        .all()
    return records

@app.get("/history/{prediction_id}")
async def get_history_by_id(
    prediction_id: int, 
    db: Session = Depends(get_db),
    current_user: models_db.User = Depends(get_current_user)
):
    """Mengambil satu riwayat spesifik berdasarkan ID (Hanya jika milik user terkait)"""
    record = db.query(models_db.Prediction)\
        .filter(models_db.Prediction.id == prediction_id, models_db.Prediction.user_id == current_user.id)\
        .first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Riwayat pemeriksaan tidak ditemukan atau Anda tidak memiliki hak akses."
        )
    return record

@app.delete("/history/{prediction_id}")
async def delete_history_by_id(
    prediction_id: int, 
    db: Session = Depends(get_db),
    current_user: models_db.User = Depends(get_current_user)
):
    """Menghapus data riwayat milik user terkait di DB sekaligus file gambarnya"""
    record = db.query(models_db.Prediction)\
        .filter(models_db.Prediction.id == prediction_id, models_db.Prediction.user_id == current_user.id)\
        .first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Gagal menghapus. Riwayat tidak ditemukan atau Anda tidak memiliki akses."
        )
    
    orig_path = record.image_path
    vis_path = record.vis_path

    db.delete(record)
    db.commit()

    if orig_path and os.path.exists(orig_path):
        os.remove(orig_path)
    if vis_path and os.path.exists(vis_path):
        os.remove(vis_path)

    return {
        "status": "success",
        "message": f"Riwayat dengan ID {prediction_id} berhasil dihapus dari sistem lokal."
    }
