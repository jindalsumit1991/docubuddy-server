import uuid

from sqlalchemy.orm import Session
from .models import OpdRecord

def get_file(db: Session, record_id: uuid):
    return db.query(OpdRecord).filter(OpdRecord.id == record_id).first()

def create_file(db: Session, name: str):
    db_file = OpdRecord(name=name)
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file
