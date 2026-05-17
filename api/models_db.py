from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, index=True)
    prediction_label = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=False)
    image_path = Column(String, nullable=False)      # Path ke gambar asli
    vis_path = Column(String)        # Path ke hasil masking/Grad-CAM
    created_at = Column(DateTime, default=datetime.datetime.utcnow)