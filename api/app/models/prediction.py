from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import datetime
from app.database import Base

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
