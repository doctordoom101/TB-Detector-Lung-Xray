# Dokumentasi API Tuberculosis Detection

Dokumentasi ini berisi daftar endpoint API yang tersedia untuk aplikasi deteksi tuberkulosis menggunakan model MobileNetV2 untuk klasifikasi dan U-Net untuk segmentasi paru-paru.

**Base URL:** `http://localhost:8000` (Default)

---

## 1. Prediksi X-Ray
Melakukan klasifikasi tuberkulosis dan segmentasi paru-paru pada gambar X-ray yang diunggah.

*   **URL:** `/predict`
*   **Method:** `POST`
*   **Content-Type:** `multipart/form-data`
*   **Payload:**
    *   `file`: Berkas gambar (PNG, JPG, atau JPEG).

*   **Respon Sukses (200 OK):**
    ```json
    {
      "id": 1,
      "prediction": "Tuberculosis",
      "confidence": "98.50%",
      "original_image_url": "/static/uuid_orig.jpg",
      "segmentation_image_url": "/static/uuid_vis.png",
      "created_at": "2023-10-27T10:00:00"
    }
    ```

---

## 2. Ambil Semua Riwayat
Mengambil seluruh daftar riwayat pemeriksaan dari database, diurutkan berdasarkan waktu terbaru.

*   **URL:** `/history`
*   **Method:** `GET`

*   **Respon Sukses (200 OK):**
    ```json
    [
      {
        "id": 2,
        "prediction_label": "Normal",
        "confidence_score": 0.992,
        "image_path": "./uploads/uuid2_orig.jpg",
        "vis_path": "./uploads/uuid2_vis.png",
        "created_at": "2023-10-27T11:00:00"
      },
      {
        "id": 1,
        "prediction_label": "Tuberculosis",
        "confidence_score": 0.985,
        "image_path": "./uploads/uuid1_orig.jpg",
        "vis_path": "./uploads/uuid1_vis.png",
        "created_at": "2023-10-27T10:00:00"
      }
    ]
    ```

---

## 3. Ambil Riwayat Berdasarkan ID
Mengambil data riwayat pemeriksaan spesifik berdasarkan ID.

*   **URL:** `/history/{prediction_id}`
*   **Method:** `GET`
*   **Parameter Jalur:**
    *   `prediction_id` (integer): ID unik dari record riwayat.

*   **Respon Sukses (200 OK):** Sama dengan objek tunggal dalam daftar riwayat.
*   **Respon Gagal (404 Not Found):**
    ```json
    {
      "detail": "Riwayat pemeriksaan dengan ID 99 tidak ditemukan."
    }
    ```

---

## 4. Hapus Riwayat Berdasarkan ID
Menghapus record riwayat dari database dan menghapus file gambar fisik dari penyimpanan server.

*   **URL:** `/history/{prediction_id}`
*   **Method:** `DELETE`
*   **Parameter Jalur:**
    *   `prediction_id` (integer): ID unik dari record riwayat yang akan dihapus.

*   **Respon Sukses (200 OK):**
    ```json
    {
      "status": "success",
      "message": "Riwayat dengan ID 1 dan file gambar terkait berhasil dihapus dari sistem."
    }
    ```

*   **Respon Gagal (404 Not Found):**
    ```json
    {
      "detail": "Gagal menghapus. Riwayat dengan ID 99 tidak ditemukan."
    }
    ```

---

## 5. Akses File Gambar
Mengakses gambar asli atau gambar hasil segmentasi melalui URL.

*   **URL:** `/static/{filename}`
*   **Method:** `GET`
*   **Contoh:** `http://localhost:8000/static/550e8400-e29b-41d4-a716-446655440000_vis.png`
