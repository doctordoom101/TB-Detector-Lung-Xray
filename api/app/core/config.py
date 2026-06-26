import os

class Settings:
    SECRET_KEY: str = "SUPER_SECRET_KEY_UNTUK_TBC_DETECTION_APP_PROJECT"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 Jam

    # SMTP Configuration (Notifikasi Email)
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = "zhero200021@gmail.com"
    SMTP_PASSWORD: str = "zslw wpcu qczi dysd"
    SENDER_EMAIL: str = "zhero200021@gmail.com"

    # Paths
    UPLOAD_DIR: str = "./uploads"
    MODEL_CLS_PATH: str = "../model/mobilenetv2/best_mobilenetv2_model.keras"
    MODEL_SEG_PATH: str = "../model/unet/best_unet.keras"

settings = Settings()
