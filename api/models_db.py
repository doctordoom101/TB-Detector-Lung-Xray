from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relasi ke riwayat prediksi
    predictions = relationship("Prediction", back_populates="owner")

class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, index=True)
    prediction_label = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=False)
    image_path = Column(String, nullable=False)
    vis_path = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Foreign Key ke User
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="predictions")
