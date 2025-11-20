import requests
import os

BASE_URL = "http://localhost:8000/api"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"

def test_upload():
    # 1. Login
    print("Logging in...")
    resp = requests.post(f"{BASE_URL}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        return
    token = resp.json()["access_token"]
    print("Login successful.")

    # 2. Create dummy file
    with open("test_doc.txt", "w") as f:
        f.write("This is a test document for NyaySaathi ingestion.")

    # 3. Upload
    print("Uploading document...")
    with open("test_doc.txt", "rb") as f:
        files = {"file": ("test_doc.txt", f, "text/plain")}
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.post(f"{BASE_URL}/admin/documents", files=files, headers=headers)
    
    if resp.status_code == 200:
        print("Upload successful:", resp.json())
    else:
        print(f"Upload failed: {resp.status_code} - {resp.text}")

    # Cleanup
    os.remove("test_doc.txt")

if __name__ == "__main__":
    test_upload()
