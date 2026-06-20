# Dokumentasi API Tuberculosis Detection & Lung Segmentation

Dokumentasi ini berisi daftar lengkap *endpoint* API yang tersedia untuk aplikasi deteksi tuberkulosis menggunakan model MobileNetV2 untuk klasifikasi dan U-Net untuk segmentasi citra paru-paru.

**Base URL:** `http://localhost:8000`

---

## 1. Sistem Autentikasi (Auth)

API ini menggunakan pengamanan berbasis token **JWT (JSON Web Token)**. Endpoint selain registrasi dan login memerlukan header otorisasi berikut:
*   **Header:** `Authorization: Bearer <your_jwt_token>`

### A. Registrasi Pengguna Baru
Mendaftarkan akun baru secara lokal ke sistem database.

*   **URL:** `/auth/register`
*   **Method:** `POST`
*   **Content-Type:** `application/json`
*   **Payload (JSON Body):**
    ```json
    {
      "email": "user@example.com",
      "password": "password123",
      "full_name": "Nama Lengkap"
    }
    ```
*   **Respon Sukses (200 OK):**
    ```json
    {
      "status": "success",
      "message": "Registrasi akun berhasil!"
    }
    ```
*   **Respon Gagal (400 Bad Request):**
    ```json
    {
      "detail": "Email ini sudah terdaftar."
    }
    ```

### B. Login Pengguna
Melakukan login menggunakan email dan password untuk mendapatkan Access Token JWT.

*   **URL:** `/auth/login`
*   **Method:** `POST`
*   **Content-Type:** `application/json`
*   **Payload (JSON Body):**
    ```json
    {
      "email": "user@example.com",
      "password": "password123"
    }
    ```
*   **Respon Sukses (200 OK):**
    ```json
    {
      "status": "success",
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer",
      "user": {
        "email": "user@example.com",
        "full_name": "Nama Lengkap"
      }
    }
    ```
*   **Respon Gagal (401 Unauthorized):**
    ```json
    {
      "detail": "Email atau password salah."
    }
    ```

---

## 2. Fitur Utama (Prediksi & Riwayat)

> [!IMPORTANT]
> Seluruh endpoint di bawah ini mewajibkan pengiriman JWT Token pada header **`Authorization: Bearer <token>`**.

### A. Prediksi X-Ray (Terproteksi JWT)
Mengunggah citra X-ray dada untuk mendeteksi tuberkulosis serta mensegmentasi paru-paru. 

Endpoint ini mengembalikan respon bertipe **Streaming Response** (`media_type="application/x-ndjson"`) dengan format JSON per baris (NDJSON) untuk menyajikan klasifikasi secara instan sembari memproses segmentasi di latar belakang.

*   **URL:** `/predict`
*   **Method:** `POST`
*   **Content-Type:** `multipart/form-data`
*   **Payload (Form Data):**
    *   `file` (Required): Berkas gambar X-ray dada (PNG, JPG, atau JPEG).
    *   `fcm_token` (Optional): Token Firebase Cloud Messaging (FCM) jika ingin menerima notifikasi dorong di aplikasi Flutter/Mobile.
*   **Format Respon Aliran (NDJSON - 200 OK):**
    
    *   **Aliran Pertama (Hasil Klasifikasi Instan):**
        ```json
        {
          "id": 1,
          "prediction": "Tuberculosis",
          "confidence": "98.50%",
          "original_image_url": "/static/uuid_orig.jpg",
          "segmentation_image_url": null,
          "created_at": "2026-06-20T22:00:00"
        }
        ```
    *   **Aliran Kedua (Hasil Lengkap dengan Segmentasi U-Net):**
        ```json
        {
          "id": 1,
          "prediction": "Tuberculosis",
          "confidence": "98.50%",
          "original_image_url": "/static/uuid_orig.jpg",
          "segmentation_image_url": "/static/uuid_vis.png",
          "created_at": "2026-06-20T22:00:00"
        }
        ```

---

### B. Ambil Semua Riwayat Pemeriksaan (Terproteksi JWT)
Mengambil daftar riwayat pemeriksaan tuberkulosis khusus milik user yang sedang aktif login (diurutkan dari yang terbaru).

*   **URL:** `/history`
*   **Method:** `GET`
*   **Respon Sukses (200 OK):**
    ```json
    [
      {
        "id": 1,
        "prediction_label": "Tuberculosis",
        "confidence_score": 0.985,
        "image_path": "./uploads/uuid_orig.jpg",
        "vis_path": "./uploads/uuid_vis.png",
        "created_at": "2026-06-20T22:00:00",
        "user_id": 1
      }
    ]
    ```

---

### C. Ambil Riwayat Berdasarkan ID (Terproteksi JWT)
Mengambil data riwayat pemeriksaan spesifik milik pengguna berdasarkan ID riwayat.

*   **URL:** `/history/{prediction_id}`
*   **Method:** `GET`
*   **Parameter Jalur (Path Parameter):**
    *   `prediction_id` (integer): ID unik dari record riwayat.
*   **Respon Sukses (200 OK):** Objek tunggal riwayat (sama dengan item di dalam daftar `/history`).
*   **Respon Gagal (404 Not Found):**
    ```json
    {
      "detail": "Riwayat pemeriksaan tidak ditemukan atau Anda tidak memiliki hak akses."
    }
    ```

---

### D. Hapus Riwayat Berdasarkan ID (Terproteksi JWT)
Menghapus record riwayat terkait milik pengguna di database sekaligus menghapus file gambar fisik dari penyimpanan lokal server.

*   **URL:** `/history/{prediction_id}`
*   **Method:** `DELETE`
*   **Parameter Jalur (Path Parameter):**
    *   `prediction_id` (integer): ID unik dari record riwayat yang akan didelete.
*   **Respon Sukses (200 OK):**
    ```json
    {
      "status": "success",
      "message": "Riwayat dengan ID 1 berhasil dihapus dari sistem lokal."
    }
    ```
*   **Respon Gagal (404 Not Found):**
    ```json
    {
      "detail": "Gagal menghapus. Riwayat tidak ditemukan atau Anda tidak memiliki akses."
    }
    ```

---

### E. Akses Berkas Gambar Statis
Mengakses file citra asli maupun hasil segmentasi visualisasi overlay secara langsung melalui browser.

*   **URL:** `/static/{filename}`
*   **Method:** `GET`
*   **Contoh URL:** `http://localhost:8000/static/uuid_vis.png`
*   **Respon Sukses (200 OK):** Berkas gambar biner asli dengan tipe konten `image/png` atau `image/jpeg`.
