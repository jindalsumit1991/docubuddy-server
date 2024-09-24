import os
import subprocess

# Define the requirements file and the wheels output directory
requirements_file = "requirements.txt"
wheels_dir = "wheels"

# Create the wheels directory if it doesn't exist
if not os.path.exists(wheels_dir):
    os.makedirs(wheels_dir)

# Use pip to download wheels from piwheels.org
def download_wheels():
    try:
        subprocess.check_call([
            "pip", "download", 
            "--only-binary=:all:",  # Force pip to only download binary wheels, not source
            "--find-links", "https://www.piwheels.org/simple",  # Use piwheels as the source
            "--dest", wheels_dir,  # Destination directory for wheels
            "-r", requirements_file  # Read requirements from the requirements.txt file
        ])
        print(f"All wheels have been downloaded to {wheels_dir}.")
    except subprocess.CalledProcessError as e:
        print(f"Error downloading wheels: {e}")

if __name__ == "__main__":
    download_wheels()
