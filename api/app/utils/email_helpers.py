import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

def send_email_notification(to_email: str, subject: str, body_html: str):
    """Mengirim email pemberitahuan menggunakan protokol SMTP"""
    if settings.SMTP_USERNAME == "email_anda@gmail.com" or settings.SMTP_PASSWORD == "app_password_gmail_anda":
        print(f"PERINGATAN: Kredensial email default terdeteksi! Lewati pengiriman email ke {to_email}.")
        return
    try:
        # 1. Konfigurasi Konten
        msg = MIMEMultipart()
        msg['From'] = settings.SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body_html, 'html'))
        
        # 2. Setup Koneksi dengan TLS
        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        
        # 3. Kirim Email
        server.sendmail(settings.SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
        print(f"Notifikasi email berhasil dikirim ke {to_email}")
    except Exception as e:
        print(f"Gagal mengirim email ke {to_email}: {e}")
