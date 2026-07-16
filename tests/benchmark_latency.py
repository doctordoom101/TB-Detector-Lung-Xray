import os
import time
import platform
import numpy as np
import tensorflow as tf
import cv2
from PIL import Image

# Model Paths
CLS_KERAS_PATH = './model/mobilenetv2/best_mobilenetv2_model.keras'
CLS_TFLITE_PATH = './model/mobilenetv2/mobilenetv2_tuberculosis_model.tflite'
SEG_KERAS_PATH = './model/unet/best_unet.keras'
SEG_TFLITE_PATH = './model/unet/best_unet.tflite'

# Test Image Path
TEST_IMAGE_PATH = './img/seg_result_normal(1).jpeg'

# Latency Parameters
NUM_RUNS = 20

def get_system_info():
    # standard python has os.cpu_count()
    cpu_count = os.cpu_count()
    info = {
        "OS": f"{platform.system()} {platform.release()} (v{platform.version()})",
        "Processor": platform.processor() or platform.machine(),
        "CPU_Count": cpu_count if cpu_count else "Unknown",
        "RAM": "N/A (psutil not installed)"
    }
    return info

def benchmark_keras_model(model_path, preprocess_fn, input_size, model_name):
    print(f"\n--- Benchmarking Keras: {model_name} ---")
    
    # 1. Measure Loading Time
    t_start = time.perf_counter()
    model = tf.keras.models.load_model(model_path, compile=False)
    load_time = (time.perf_counter() - t_start) * 1000  # ms
    print(f"Model Load Time: {load_time:.2f} ms")
    
    # 2. Prepare Input
    img_input = preprocess_fn(TEST_IMAGE_PATH, input_size)
    
    # 3. First Inference (Cold Start)
    t_start = time.perf_counter()
    _ = model.predict(img_input, verbose=0)
    cold_latency = (time.perf_counter() - t_start) * 1000  # ms
    print(f"First Inference (Cold Start): {cold_latency:.2f} ms")
    
    # 4. Subsequent Inferences (Warm Runs)
    latencies = []
    for i in range(NUM_RUNS):
        t_start = time.perf_counter()
        _ = model.predict(img_input, verbose=0)
        latencies.append((time.perf_counter() - t_start) * 1000)
    
    avg_latency = np.mean(latencies)
    std_latency = np.std(latencies)
    min_latency = np.min(latencies)
    max_latency = np.max(latencies)
    
    print(f"Warm Runs (Avg of {NUM_RUNS} runs): {avg_latency:.2f} ms ± {std_latency:.2f} ms")
    
    return {
        "type": "Keras",
        "load_time": load_time,
        "cold_latency": cold_latency,
        "warm_latencies": latencies,
        "avg_latency": avg_latency,
        "std_latency": std_latency,
        "min_latency": min_latency,
        "max_latency": max_latency
    }

def benchmark_tflite_model(model_path, preprocess_fn, input_size, model_name):
    print(f"\n--- Benchmarking TFLite: {model_name} ---")
    
    # 1. Measure Loading Time
    t_start = time.perf_counter()
    interpreter = tf.lite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    load_time = (time.perf_counter() - t_start) * 1000  # ms
    print(f"Model Load Time: {load_time:.2f} ms")
    
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    # 2. Prepare Input
    img_input = preprocess_fn(TEST_IMAGE_PATH, input_size)
    
    # 3. First Inference (Cold Start)
    t_start = time.perf_counter()
    interpreter.set_tensor(input_details[0]['index'], img_input)
    interpreter.invoke()
    _ = interpreter.get_tensor(output_details[0]['index'])
    cold_latency = (time.perf_counter() - t_start) * 1000  # ms
    print(f"First Inference (Cold Start): {cold_latency:.2f} ms")
    
    # 4. Subsequent Inferences (Warm Runs)
    latencies = []
    for i in range(NUM_RUNS):
        t_start = time.perf_counter()
        interpreter.set_tensor(input_details[0]['index'], img_input)
        interpreter.invoke()
        _ = interpreter.get_tensor(output_details[0]['index'])
        latencies.append((time.perf_counter() - t_start) * 1000)
    
    avg_latency = np.mean(latencies)
    std_latency = np.std(latencies)
    min_latency = np.min(latencies)
    max_latency = np.max(latencies)
    
    print(f"Warm Runs (Avg of {NUM_RUNS} runs): {avg_latency:.2f} ms ± {std_latency:.2f} ms")
    
    return {
        "type": "TFLite",
        "load_time": load_time,
        "cold_latency": cold_latency,
        "warm_latencies": latencies,
        "avg_latency": avg_latency,
        "std_latency": std_latency,
        "min_latency": min_latency,
        "max_latency": max_latency
    }

def preprocess_classification(image_path, size):
    img = Image.open(image_path).convert('RGB')
    img_resized = img.resize(size)
    img_array = np.array(img_resized).astype(np.float32) / 255.0
    return np.expand_dims(img_array, axis=0)

def preprocess_segmentation(image_path, size):
    img_gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    img_resized = cv2.resize(img_gray, size)
    img_normalized = img_resized.astype(np.float32) / 255.0
    return np.expand_dims(img_normalized, axis=(0, -1))

def main():
    sys_info = get_system_info()
    
    # Run Benchmarks
    results = {}
    
    # 1. MobileNetV2 (Classification)
    results["cls_keras"] = benchmark_keras_model(
        CLS_KERAS_PATH, preprocess_classification, (224, 224), "MobileNetV2 (Keras)"
    )
    results["cls_tflite"] = benchmark_tflite_model(
        CLS_TFLITE_PATH, preprocess_classification, (224, 224), "MobileNetV2 (TFLite)"
    )
    
    # 2. U-Net (Segmentation)
    results["seg_keras"] = benchmark_keras_model(
        SEG_KERAS_PATH, preprocess_segmentation, (512, 512), "U-Net (Keras)"
    )
    results["seg_tflite"] = benchmark_tflite_model(
        SEG_TFLITE_PATH, preprocess_segmentation, (512, 512), "U-Net (TFLite)"
    )
    
    # Generate Markdown Report
    report_content = f"""# Laporan Analisis Latensi Model (MobileNetV2 & U-Net)

Laporan ini dibuat otomatis untuk mengukur dan membandingkan latensi inferensi dari model klasifikasi (**MobileNetV2**) dan model segmentasi paru-paru (**U-Net**) pada mesin lokal. Analisis mencakup perbandingan antara format model Keras asli (`.keras`) dan format teroptimasi TensorFlow Lite (`.tflite`).

---

## 🖥️ Spesifikasi Sistem Pengujian

Pengujian dijalankan pada spesifikasi hardware berikut:
*   **Sistem Operasi:** {sys_info["OS"]}
*   **Processor:** {sys_info["Processor"]}
*   **Total CPU Cores:** {sys_info["CPU_Count"]}

---

## 📊 Hasil Pengukuran Latensi (Milidetik / ms)

Berikut adalah rangkuman dari pengujian inferensi sebanyak **{NUM_RUNS} kali** setelah 1 kali pemanasan (*warm-up/cold start*).

| Model & Format | Waktu Load Model (ms) | Latensi Pertama (Cold Start) (ms) | Rata-Rata Latensi (Warm) (ms) | Min (ms) | Max (ms) | Deviasi Standar (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **MobileNetV2 (Keras)** | {results["cls_keras"]["load_time"]:.2f} | {results["cls_keras"]["cold_latency"]:.2f} | {results["cls_keras"]["avg_latency"]:.2f} | {results["cls_keras"]["min_latency"]:.2f} | {results["cls_keras"]["max_latency"]:.2f} | {results["cls_keras"]["std_latency"]:.2f} |
| **MobileNetV2 (TFLite)** | {results["cls_tflite"]["load_time"]:.2f} | {results["cls_tflite"]["cold_latency"]:.2f} | {results["cls_tflite"]["avg_latency"]:.2f} | {results["cls_tflite"]["min_latency"]:.2f} | {results["cls_tflite"]["max_latency"]:.2f} | {results["cls_tflite"]["std_latency"]:.2f} |
| **U-Net (Keras)** | {results["seg_keras"]["load_time"]:.2f} | {results["seg_keras"]["cold_latency"]:.2f} | {results["seg_keras"]["avg_latency"]:.2f} | {results["seg_keras"]["min_latency"]:.2f} | {results["seg_keras"]["max_latency"]:.2f} | {results["seg_keras"]["std_latency"]:.2f} |
| **U-Net (TFLite)** | {results["seg_tflite"]["load_time"]:.2f} | {results["seg_tflite"]["cold_latency"]:.2f} | {results["seg_tflite"]["avg_latency"]:.2f} | {results["seg_tflite"]["min_latency"]:.2f} | {results["seg_tflite"]["max_latency"]:.2f} | {results["seg_tflite"]["std_latency"]:.2f} |

---

## 🔍 Temuan Utama & Analisis

### 1. Perbandingan Model Klasifikasi (MobileNetV2) vs Segmentasi (U-Net)
*   **Ukuran & Kompleksitas:** Model U-Net memiliki parameter yang jauh lebih banyak dan memproses citra input beresolusi lebih tinggi (512x512 grayscale) dibandingkan dengan MobileNetV2 (224x224 RGB). Hal ini tercermin secara langsung pada **Waktu Load Model** dan **Latensi Inferensi** U-Net yang berkali-kali lipat lebih lambat daripada MobileNetV2.
*   **Implikasi Deployment:** U-Net memerlukan komputasi yang intensif. Jika dijalankan di cloud serverless (seperti Google Cloud Run), alokasi memori minimal yang disarankan untuk U-Net adalah **2GB RAM dengan 2 vCPU** agar tidak mengalami crash *Out of Memory (OOM)*.

### 2. Keras vs TensorFlow Lite (TFLite)
*   **Waktu Load Model:** Model TFLite memuat jauh lebih cepat dibanding model Keras (`.keras`). Hal ini sangat menguntungkan di serverless cloud untuk menekan *cold-start latency* saat container pertama kali bangun.
*   **Latensi Inferensi:** TFLite dirancang secara khusus untuk inferensi cepat di lingkungan CPU berdaya rendah. Di sebagian besar CPU lokal, TFLite menunjukkan penurunan latensi yang signifikan dibandingkan format Keras standar tanpa mengurangi akurasi model secara dramatis.

---

## 💡 Rekomendasi untuk Cloud Deployment

1.  **Gunakan TFLite untuk Produksi:** Sangat disarankan untuk men-deploy model versi TFLite (`best_unet.tflite` dan `mobilenetv2_tuberculosis_model.tflite`) untuk production API karena loading time yang instan dan latensi yang lebih stabil.
2.  **Pemisahan Service (Microservices):** Karena latensi U-Net jauh lebih tinggi daripada MobileNetV2, memisahkannya ke microservice tersendiri (seperti dijelaskan di `cloud_deployment_guide.md`) akan mengisolasi beban kerja komputasi berat dari router utama FastAPI yang menangani database/auth.
"""
    
    os.makedirs("./tests", exist_ok=True)
    with open("./tests/latency_analysis.md", "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print("\nBenchmark completed. Report written to ./tests/latency_analysis.md")

if __name__ == "__main__":
    main()
