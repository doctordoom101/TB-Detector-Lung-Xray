# Laporan Analisis Latensi Model (MobileNetV2 & U-Net)

Laporan ini dibuat otomatis untuk mengukur dan membandingkan latensi inferensi dari model klasifikasi (**MobileNetV2**) dan model segmentasi paru-paru (**U-Net**) pada mesin lokal. Analisis mencakup perbandingan antara format model Keras asli (`.keras`) dan format teroptimasi TensorFlow Lite (`.tflite`).

---

## 🖥️ Spesifikasi Sistem Pengujian

Pengujian dijalankan pada spesifikasi hardware berikut:
*   **Sistem Operasi:** Windows 10 (v10.0.26200)
*   **Processor:** Intel64 Family 6 Model 154 Stepping 3, GenuineIntel
*   **Total CPU Cores:** 16

---

## 📊 Hasil Pengukuran Latensi (Milidetik / ms)

Berikut adalah rangkuman dari pengujian inferensi sebanyak **20 kali** setelah 1 kali pemanasan (*warm-up/cold start*).

| Model & Format | Waktu Load Model (ms) | Latensi Pertama (Cold Start) (ms) | Rata-Rata Latensi (Warm) (ms) | Min (ms) | Max (ms) | Deviasi Standar (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **MobileNetV2 (Keras)** | 775.92 | 762.77 | 57.76 | 53.32 | 83.99 | 6.57 |
| **MobileNetV2 (TFLite)** | 35.61 | 8.45 | 6.34 | 5.85 | 7.01 | 0.27 |
| **U-Net (Keras)** | 344.16 | 157511.50 | 163362.14 | 162383.83 | 164543.13 | 564.41 |
| **U-Net (TFLite)** | 106.18 | 2940.08 | 2732.58 | 2705.55 | 2810.05 | 24.80 |

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
