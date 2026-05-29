import tensorflow as tf
import numpy as np
import cv2
from PIL import Image

# Classification constants
CLS_HEIGHT = 224
CLS_WIDTH = 224

# Segmentation constants
SEG_HEIGHT = 512
SEG_WIDTH = 512

def preprocess_classification(image_path: str) -> np.ndarray:
    """Preprocessing untuk model MobileNetV2 (Classification)"""
    img = Image.open(image_path).convert('RGB')
    img_resized = img.resize((CLS_WIDTH, CLS_HEIGHT))
    img_array = np.array(img_resized).astype(np.float32) / 255.0
    return np.expand_dims(img_array, axis=0)

def preprocess_segmentation(image_path: str) -> np.ndarray:
    """Preprocessing untuk model U-Net (Segmentation)"""
    # Baca sebagai grayscale
    img_gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    img_resized = cv2.resize(img_gray, (SEG_WIDTH, SEG_HEIGHT))
    img_normalized = img_resized.astype(np.float32) / 255.0
    # Tambahkan dimensi batch dan channel (1, 512, 512, 1)
    return np.expand_dims(img_normalized, axis=(0, -1))

def save_segmentation_overlay(seg_model, seg_input: np.ndarray, original_img_path: str, output_path: str):
    """Menjalankan segmentasi dan menyimpan hasil overlay (original + green mask)"""
    try:
        # 1. Prediksi Masker
        preds = seg_model.predict(seg_input, verbose=0)
        mask = np.squeeze(preds)
        binary_mask = (mask > 0.5).astype(np.uint8) * 255

        # 2. Baca Gambar Asli (Bisa ukuran apapun)
        original_img = cv2.imread(original_img_path)
        h, w = original_img.shape[:2]

        # 3. Resize Masker ke ukuran gambar asli
        mask_resized = cv2.resize(binary_mask, (w, h))

        # 4. Buat Overlay Hijau
        colored_mask = np.zeros_like(original_img)
        colored_mask[:, :, 1] = mask_resized  # Channel Hijau

        # 5. Gabungkan Overlay (0.7 asli, 0.3 masker hijau)
        overlay_img = cv2.addWeighted(original_img, 0.7, colored_mask, 0.3, 0)
        
        # Simpan hasil
        cv2.imwrite(output_path, overlay_img)
        
    except Exception as e:
        print(f"Gagal generate Segmentation Overlay: {e}")
        # Jika gagal, simpan copy gambar asli saja
        img_ori = cv2.imread(original_img_path)
        cv2.imwrite(output_path, img_ori)