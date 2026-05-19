from fastapi import FastAPI, File, UploadFile, Depends
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import tensorflow as tf
import uuid
import os

# Import komponen lokal kamu
import models_db
import utils
from database import SessionLocal

app = FastAPI(title="Tuberculosis Detection API")

# Pastikan folder uploads tersedia untuk menyimpan gambar
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Daftarkan folder uploads agar gambarnya bisa diakses lewat URL browser
app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")

# Load model .keras utama kamu (Muat 1 kali di awal startup biar kencang)
MODEL_PATH = "../model/mobilenetv2/best_mobilenetv2_model.keras" 
model = tf.keras.models.load_model(MODEL_PATH)

# Fungsi pembantu untuk memanggil session database (Dependency Injection)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/predict")
async def predict_xray(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # 1. Generate nama file unik menggunakan UUID agar tidak bentrok
    file_id = str(uuid.uuid4())
    file_ext = file.filename.split(".")[-1]
    
    orig_filename = f"{file_id}_orig.{file_ext}"
    vis_filename = f"{file_id}_vis.png"
    
    orig_path = os.path.join(UPLOAD_DIR, orig_filename)
    vis_path = os.path.join(UPLOAD_DIR, vis_filename)

    # 2. Simpan gambar asli dari user
    with open(orig_path, "wb") as buffer:
        buffer.write(await file.read())

    # 3. Jalankan Preprocessing & Prediksi Model
    img_tensor = utils.preprocess_image(orig_path)
    predictions = model.predict(img_tensor)
    confidence = float(predictions[0][0])
    
    label = "Tuberculosis" if confidence > 0.5 else "Normal"
    # Siasat confidence score agar selalu mencerminkan kelas terpilih
    display_confidence = confidence if label == "Tuberculosis" else (1.0 - confidence)

    # 4. Jalankan Grad-CAM Masking
    utils.generate_and_save_gradcam(model, img_tensor, orig_path, vis_path)

    # 5. Simpan catatan ke SQLite Database
    db_record = models_db.Prediction(
        prediction_label=label,
        confidence_score=display_confidence,
        image_path=orig_path,
        vis_path=vis_path
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    # 6. Kembalikan respon ke Client (Mobile/Frontend)
    return {
        "id": db_record.id,
        "prediction": label,
        "confidence": f"{display_confidence * 100:.2f}%",
        "original_image_url": f"/static/{orig_filename}",
        "masking_image_url": f"/static/{vis_filename}",
        "created_at": db_record.created_at
    }

@app.get("/history")
async def get_all_history(db: Session = Depends(get_db)):
    """Mengambil seluruh riwayat data deteksi untuk halaman history"""
    records = db.query(models_db.Prediction).order_by(models_db.Prediction.created_at.desc()).all()
    return records