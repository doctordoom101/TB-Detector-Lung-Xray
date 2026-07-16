from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import tensorflow as tf
import uuid
import os
import json

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.prediction import Prediction
from app.core.config import settings
from app.core import firebase
from app.utils import image_helpers

router = APIRouter(tags=["Predictions"])

# Load models
print("Loading Models for Prediction...")
model_cls = tf.keras.models.load_model(settings.MODEL_CLS_PATH)

if settings.MODEL_SEG_PATH.endswith(".tflite"):
    print(f"Loading U-Net Segmentation (TFLite) from {settings.MODEL_SEG_PATH}...")
    model_seg = tf.lite.Interpreter(model_path=settings.MODEL_SEG_PATH)
    model_seg.allocate_tensors()
else:
    print(f"Loading U-Net Segmentation (Keras) from {settings.MODEL_SEG_PATH}...")
    model_seg = tf.keras.models.load_model(settings.MODEL_SEG_PATH, compile=False)

@router.post("/predict")
async def predict_xray(
    file: UploadFile = File(...), 
    fcm_token: str = None, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Endpoint Prediksi yang diproteksi JWT Token"""
    # 1. Generate nama file unik menggunakan UUID agar tidak bentrok
    file_id = str(uuid.uuid4())
    file_ext = file.filename.split(".")[-1]
    
    orig_filename = f"{file_id}_orig.{file_ext}"
    vis_filename = f"{file_id}_vis.png"
    
    orig_path = os.path.join(settings.UPLOAD_DIR, orig_filename)
    vis_path = os.path.join(settings.UPLOAD_DIR, vis_filename)

    # 2. Simpan gambar asli dari user ke server lokal
    with open(orig_path, "wb") as buffer:
        buffer.write(await file.read())

    async def generate_steps():
        # 3. Jalankan Preprocessing & Prediksi Klasifikasi (MobileNetV2)
        img_cls_tensor = image_helpers.preprocess_classification(orig_path)
        cls_predictions = model_cls.predict(img_cls_tensor)
        confidence = float(cls_predictions[0][0])
        
        label = "Tuberculosis" if confidence > 0.5 else "Normal"
        display_confidence = confidence if label == "Tuberculosis" else (1.0 - confidence)

        # 4. Simpan catatan AWAL ke SQLite Database (terikat dengan ID user yang login)
        db_record = Prediction(
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
        img_seg_tensor = image_helpers.preprocess_segmentation(orig_path)
        image_helpers.save_segmentation_overlay(model_seg, img_seg_tensor, orig_path, vis_path)

        # 7. Update catatan dengan vis_path
        db_record.vis_path = vis_path
        db.commit()

        # 8. Kirim respon LENGKAP
        final_output = first_output.copy()
        final_output["segmentation_image_url"] = f"/static/{vis_filename}"
        yield json.dumps(final_output) + "\n"

        # 9. KIRIM PUSH NOTIFICATION VIA FCM jika token disediakan dari Flutter
        if fcm_token:
            firebase.send_fcm_notification(
                token=fcm_token,
                title="Hasil Deteksi Tuberkulosis Selesai",
                body=f"Halo {current_user.full_name or 'User'}, pemeriksaan menunjukkan status: {label} dengan akurasi {display_confidence * 100:.2f}%."
            )

    return StreamingResponse(generate_steps(), media_type="application/x-ndjson")

@router.get("/history")
async def get_user_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mengambil riwayat data deteksi spesifik milik user yang sedang login saja"""
    records = db.query(Prediction)\
        .filter(Prediction.user_id == current_user.id)\
        .order_by(Prediction.created_at.desc())\
        .all()
    return records

@router.get("/history/{prediction_id}")
async def get_history_by_id(
    prediction_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mengambil satu riwayat spesifik berdasarkan ID (Hanya jika milik user terkait)"""
    record = db.query(Prediction)\
        .filter(Prediction.id == prediction_id, Prediction.user_id == current_user.id)\
        .first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Riwayat pemeriksaan tidak ditemukan atau Anda tidak memiliki hak akses."
        )
    return record

@router.delete("/history/{prediction_id}")
async def delete_history_by_id(
    prediction_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Menghapus data riwayat milik user terkait di DB sekaligus file gambarnya"""
    record = db.query(Prediction)\
        .filter(Prediction.id == prediction_id, Prediction.user_id == current_user.id)\
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
