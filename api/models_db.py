from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class PredictionHistory(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, index=True)
    patient_name = Column(String)
    prediction = Column(String)
    confidence = Column(Float)
    image_path = Column(String)      # Path ke gambar asli
    vis_path = Column(String)        # Path ke hasil masking/Grad-CAM
    created_at = Column(DateTime, default=datetime.datetime.utcnow)