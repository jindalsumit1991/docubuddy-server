from sqlalchemy import Column, String, Integer, Boolean, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .db import Base

class OpdRecord(Base):
    __tablename__ = 'opd_record'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    institution_id = Column(Integer, nullable=False)
    username = Column(String)
    authorized = Column(Boolean, default=False)
    file_path = Column(String, nullable=False)
    auth_file_path = Column(String)
    value_ai = Column(String)
    value_actual = Column(String)
    authorized_by = Column(String)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), server_default=func.now())
