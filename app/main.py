import zipfile
from io import BytesIO
import logging

from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Depends
from google.cloud import storage
from sqlalchemy.orm import Session
from app.models import OpdRecord  # Assuming the table is defined in app/models.py
from app.db import get_db

app = FastAPI()

logging.basicConfig(level=logging.INFO)

# Replace with your Google Cloud Storage bucket name
BUCKET_NAME = 'mehar-ocr-test'

# Initialize Google Cloud Storage client
storage_client = storage.Client()


def upload_to_gcs(file: BytesIO, filename: str):
    """Upload a file to Google Cloud Storage."""
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_file(file)
        return f"gs://{BUCKET_NAME}/{filename}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload {filename}: {e}")


@app.post("/upload-images/")
async def upload_images(
        files: list[UploadFile] = File(...),
        username: str = Header(None),
        hospital: int = Header(1),
        db: Session = Depends(get_db)  # Inject session
):
    logging.info(">>> upload-images called..\n")
    """Endpoint to upload multiple image files to Google Cloud Storage."""
    username: str = username,  # Optional username from headers
    hospital: int = hospital,  # Hospital header with int type and default value of 1


    uploaded_files = []
    for file in files:
        # if file.content_type not in ["image/jpeg", "image/png", "application/zip"]:
        #    raise HTTPException(status_code=400, detail="Only JPEG, PNG, or ZIP files are allowed.")

        if file.content_type == "application/zip":
            # Handle ZIP file
            zip_buffer = BytesIO(await file.read())
            with zipfile.ZipFile(zip_buffer, "r") as zip_ref:
                for zip_info in zip_ref.infolist():
                    if zip_info.filename.endswith(('.jpg', '.jpeg', '.png')):
                        with zip_ref.open(zip_info.filename) as img_file:
                            img_buffer = BytesIO(img_file.read())
                            # Upload each image in the zip to GCS
                            gcs_path = upload_to_gcs(img_buffer, zip_info.filename)
                            uploaded_files.append(gcs_path)
                            logging.info(f">>> Uploaded {zip_info.filename}, now saving to DB")
                            # Insert record in database for each uploaded image
                            add_file_to_db(db, username, hospital, gcs_path)
        else:
            # Handle individual images
            file_buffer = BytesIO(await file.read())
            gcs_path = upload_to_gcs(file_buffer, file.filename)
            uploaded_files.append(gcs_path)
            logging.info(f">>> Uploaded {gcs_path}, now saving to DB")
            # Insert record in database for each uploaded image
            add_file_to_db(db, username, hospital, gcs_path)

    return {"uploaded_files": uploaded_files}

def add_file_to_db(db: Session, username: str, institution_id: int, file_path: str):
    """Insert the uploaded file info into the database."""
    logging.info(">>> add_file_to_db called...\n")
    new_record = OpdRecord(
        username=username,  # You can add other fields as needed
        institution_id=institution_id,  # hospital value mapped to institution_id
        file_path=file_path
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)

# Run the server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
