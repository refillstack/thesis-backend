from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class Thesis(Base):
    __tablename__ = "theses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)  # This will store the OCR extracted text
    analysis = Column(Text, nullable=True)  # This will store Mistral's analysis
    model_used = Column(String, nullable=True)
    provider = Column(String, nullable=True)
    user_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False) 