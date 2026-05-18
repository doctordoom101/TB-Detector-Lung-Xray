from database import SessionLocal
from models_db import Prediction

db = SessionLocal()

new_prediction = Prediction(
    prediction_label="Positive",
    confidence_score=0.97,
    image_path="uploads/original/test.png",
    vis_path="uploads/gradcam/test_cam.png"
)

db.add(new_prediction)

db.commit()

db.refresh(new_prediction)

print("DATA INSERTED")
print(f"ID: {new_prediction.id}")

db.close()