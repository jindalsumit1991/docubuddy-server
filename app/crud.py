from sqlalchemy.orm import Session
from .models import File

def get_file(db: Session, file_id: int):
    return db.query(File).filter(File.id == file_id).first()

def create_file(db: Session, name: str):
    db_file = File(name=name)
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file
