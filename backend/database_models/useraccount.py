# backend/database_models/useraccount.py


from sqlalchemy import Column, Integer, String, DateTime, Text
from database import Base


class UserAccount(Base):
    __tablename__ = "UserAccount"
    char_id = Column(Integer, primary_key=True)
    char_hash = Column(String(100))
    char_name = Column(String(100), index=True)

    access_token = Column(Text)
    refresh_token = Column(Text)
    expires_at = Column(DateTime)

    scopes = Column(Text)

    session_key = Column(String(64), unique=True)