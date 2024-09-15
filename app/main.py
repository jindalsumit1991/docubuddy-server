from fastapi import FastAPI, UploadFile, File, HTTPException
from google.cloud import storage
import os
import zipfile
from io import BytesIO

app = FastAPI()

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
async def upload_images(files: list[UploadFile] = File(...)):
    """Endpoint to upload multiple image files to Google Cloud Storage."""
    uploaded_files = []
    for file in files:
        #if file.content_type not in ["image/jpeg", "image/png", "application/zip"]:
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
        else:
            # Handle individual images
            file_buffer = BytesIO(await file.read())
            gcs_path = upload_to_gcs(file_buffer, file.filename)
            uploaded_files.append(gcs_path)

    return {"uploaded_files": uploaded_files}

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
