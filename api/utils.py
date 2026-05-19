import tensorflow as tf
import numpy as np
import cv2
from PIL import Image

IMG_HEIGHT = 224
IMG_WIDTH = 224

def preprocess_image(image_path: str) -> np.ndarray:
    """Membaca gambar asli dan mengubahnya menjadi format tensor siap prediksi"""
    img = Image.open(image_path).convert('RGB')
    img_resized = img.resize((IMG_WIDTH, IMG_HEIGHT))
    img_array = np.array(img_resized).astype(np.float32) / 255.0
    return np.expand_dims(img_array, axis=0)

def generate_and_save_gradcam(model, img_array: np.ndarray, original_img_path: str, output_path: str, last_conv_layer_name: str = "Conv_1"):
    """Menghitung Grad-CAM dan menyimpan hasil gambar overlay-nya"""
    try:
        # 1. Buat gradien model
        grad_model = tf.keras.models.Model(
            [model.inputs], [model.get_layer(last_conv_layer_name).output, model.output]
        )

        with tf.GradientTape() as tape:
            last_conv_layer_output, preds = grad_model(img_array)
            class_channel = preds[:, 0]

        # 2. Hitung heatmap intensitas
        grads = tape.gradient(class_channel, last_conv_layer_output)
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
        
        last_conv_layer_output = last_conv_layer_output[0]
        heatmap = last_conv_layer_output @ pooled_grads[..., tf.newaxis]
        heatmap = tf.squeeze(heatmap)

        # 3. Normalisasi Heatmap
        heatmap = tf.maximum(heatmap, 0) / (tf.math.reduce_max(heatmap) + 1e-10)
        heatmap = np.uint8(255 * heatmap.numpy())

        # 4. Gabungkan (Overlay) dengan gambar asli menggunakan OpenCV
        original_img = cv2.imread(original_img_path)
        heatmap_resized = cv2.resize(heatmap, (original_img.shape[1], original_img.shape[0]))
        heatmap_color = cv2.applyColorMap(heatmap_resized, cv2.COLORMAP_JET)

        # 0.6 gambar asli, 0.4 warna heatmap
        superimposed_img = cv2.addWeighted(original_img, 0.6, heatmap_color, 0.4, 0)
        
        # Simpan hasil masking ke folder uploads
        cv2.imwrite(output_path, superimposed_img)
        
    except Exception as e:
        print(f"Gagal generate Grad-CAM: {e}. Menggunakan gambar asli sebagai cadangan.")
        img_ori = cv2.imread(original_img_path)
        cv2.imwrite(output_path, img_ori)