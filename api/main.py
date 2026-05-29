from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status
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

    # 3. Jalankan Preprocessing & Prediksi Klasifikasi (MobileNetV2)
    img_cls_tensor = utils.preprocess_classification(orig_path)
    cls_predictions = model_cls.predict(img_cls_tensor)
    confidence = float(cls_predictions[0][0])
    
    label = "Tuberculosis" if confidence > 0.5 else "Normal"
    # Siasat confidence score agar selalu mencerminkan kelas terpilih
    display_confidence = confidence if label == "Tuberculosis" else (1.0 - confidence)

    # 4. Jalankan Lung Segmentation (U-Net) & Save Overlay
    img_seg_tensor = utils.preprocess_segmentation(orig_path)
    utils.save_segmentation_overlay(model_seg, img_seg_tensor, orig_path, vis_path)

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
        "segmentation_image_url": f"/static/{vis_filename}",
        "created_at": db_record.created_at
    }

@app.get("/history")
async def get_all_history(db: Session = Depends(get_db)):
    """Mengambil seluruh riwayat data deteksi untuk halaman history"""
    records = db.query(models_db.Prediction).order_by(models_db.Prediction.created_at.desc()).all()
    return records

# --- ENDPOINT BARU: GET BY ID ---
@app.get("/history/{prediction_id}")
async def get_history_by_id(prediction_id: int, db: Session = Depends(get_db)):
    """Mengambil satu riwayat spesifik berdasarkan ID"""
    record = db.query(models_db.Prediction).filter(models_db.Prediction.id == prediction_id).first()
    
    # Validasi jika ID tidak ditemukan di database
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Riwayat pemeriksaan dengan ID {prediction_id} tidak ditemukan."
        )
    return record

# --- ENDPOINT BARU: DELETE BY ID ---
@app.delete("/history/{prediction_id}")
async def delete_history_by_id(prediction_id: int, db: Session = Depends(get_db)):
    """Menghapus data riwayat di DB sekaligus menghapus file gambar fisiknya di storage"""
    record = db.query(models_db.Prediction).filter(models_db.Prediction.id == prediction_id).first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Gagal menghapus. Riwayat dengan ID {prediction_id} tidak ditemukan."
        )
    
    # Ambil path gambar sebelum datanya dihapus dari DB
    orig_path = record.image_path
    vis_path = record.vis_path

    # 1. Hapus record dari database
    db.delete(record)
    db.commit()

    # 2. Hapus file fisik gambar asli jika ada di local storage
    if orig_path and os.path.exists(orig_path):
        os.remove(orig_path)
        
    # 3. Hapus file fisik gambar masking Grad-CAM jika ada di local storage
    if vis_path and os.path.exists(vis_path):
        os.remove(vis_path)

    return {
        "status": "success",
        "message": f"Riwayat dengan ID {prediction_id} dan file gambar terkait berhasil dihapus dari sistem."
    }