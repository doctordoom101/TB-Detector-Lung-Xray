import firebase_admin
from firebase_admin import credentials, messaging, auth
import os

# Path ke service account key (di folder api/root)
cred_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "serviceAccountKey.json")

if not firebase_admin._apps:
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    else:
        print("PERINGATAN: serviceAccountKey.json tidak ditemukan! FCM dan Google Auth tidak dapat digunakan.")

def send_fcm_notification(token: str, title: str, body: str):
    """Mengirim Push Notification ke device tertentu menggunakan FCM Token"""
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=token,
        )
        response = messaging.send(message)
        print('Successfully sent message:', response)
        return response
    except Exception as e:
        print('Error sending FCM message:', e)
        return None
