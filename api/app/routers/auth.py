from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
import datetime

from app.database import get_db
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, GoogleLoginRequest
from app.core import security
from app.core.firebase import auth as firebase_auth
from app.utils.email_helpers import send_email_notification

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register")
async def register_user(user_data: UserRegister, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Endpoint untuk mendaftarkan akun baru secara lokal"""
    # Cek apakah email sudah terdaftar
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email ini sudah terdaftar."
        )
    
    # Hash password dan simpan ke database
    hashed_password = security.get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Kirim email selamat datang via Background Tasks
    email_subject = "Selamat Datang di TB Detector - Registrasi Berhasil!"
    email_body = f"""
    <html>
        <body>
            <h3>Halo, {user_data.full_name or 'User'}!</h3>
            <p>Terima kasih telah mendaftar di aplikasi <strong>Tuberculosis Detection App</strong>.</p>
            <p>Akun Anda dengan email <code>{user_data.email}</code> telah berhasil didaftarkan.</p>
            <br>
            <p>Salam hangat,<br>Tim Developer TB Detector</p>
        </body>
    </html>
    """
    background_tasks.add_task(send_email_notification, user_data.email, email_subject, email_body)

    return {"status": "success", "message": "Registrasi akun berhasil!"}

@router.post("/login")
async def login_user(login_data: UserLogin, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Endpoint Login untuk mendapatkan Access Token JWT"""
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not security.verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah."
        )
    
    # Generate Token JWT
    access_token = security.create_access_token(data={"sub": user.email})

    # Kirim email pemberitahuan login baru via Background Tasks
    email_subject = "Notifikasi Login Baru - Akun TB Detector Anda"
    email_body = f"""
    <html>
        <body>
            <h3>Halo, {user.full_name or 'User'}!</h3>
            <p>Kami mendeteksi adanya aktivitas login baru pada akun Anda dengan detail berikut:</p>
            <ul>
                <li><strong>Email:</strong> {user.email}</li>
                <li><strong>Waktu:</strong> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
            </ul>
            <p>Jika ini bukan aktivitas Anda, harap segera amankan akun Anda atau ganti kata sandi.</p>
            <br>
            <p>Salam hangat,<br>Tim Developer TB Detector</p>
        </body>
    </html>
    """
    background_tasks.add_task(send_email_notification, user.email, email_subject, email_body)

    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": user.email,
            "full_name": user.full_name
        }
    }

@router.post("/google")
async def google_login(payload: GoogleLoginRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Endpoint untuk autentikasi menggunakan Google ID Token melalui Firebase"""
    try:
        # Verifikasi ID Token Firebase/Google menggunakan Firebase Admin SDK
        decoded_token = firebase_auth.verify_id_token(payload.id_token)
        email = decoded_token.get("email")
        full_name = decoded_token.get("name", "Google User")
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email tidak ditemukan di dalam token Google."
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token Google tidak valid atau kedaluwarsa: {str(e)}"
        )

    # Cek apakah user sudah terdaftar di database SQLite lokal
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # Jika user baru pertama kali login dengan Google, daftarkan secara otomatis
        import secrets
        random_password = secrets.token_urlsafe(32)
        hashed_password = security.get_password_hash(random_password)
        
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Kirim email selamat datang untuk pendaftaran baru
        email_subject = "Selamat Datang di TB Detector!"
        email_body = f"""
        <html>
            <body>
                <h3>Halo, {full_name}!</h3>
                <p>Akun Anda berhasil didaftarkan secara otomatis melalui login Google dengan email <code>{email}</code>.</p>
                <br>
                <p>Salam hangat,<br>Tim Developer TB Detector</p>
            </body>
        </html>
        """
        background_tasks.add_task(send_email_notification, email, email_subject, email_body)
    
    # Buat JWT Access Token lokal
    access_token = security.create_access_token(data={"sub": user.email})
    
    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": user.email,
            "full_name": user.full_name
        }
    }
