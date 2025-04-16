import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "http://localhost:8000"
API_KEY = os.getenv("MISTRAL_API_KEY")

def test_analyze_paper():
    """Test the paper analysis endpoint with a sample PDF."""
    
    # Check if API key exists
    if not API_KEY:
        print("ERROR: MISTRAL_API_KEY not found in environment variables")
        return
    
    # Path to a test PDF file
    # Update this path to point to a valid PDF file on your system
    test_file_path = "test_document.pdf"
    
    # Check if the file exists
    if not os.path.exists(test_file_path):
        with open(test_file_path, "w") as f:
            f.write("Test document content")
        print(f"Created test file: {test_file_path}")
    
    # Open the file in binary mode
    with open(test_file_path, "rb") as f:
        files = {"file": (os.path.basename(test_file_path), f, "application/pdf")}
        
        # Make the request
        print(f"Sending request to {API_URL}/api/papers/analyze")
        print(f"API Key (first 5 chars): {API_KEY[:5]}...")
        
        headers = {
            "Authorization": f"Bearer {API_KEY}"
        }
        
        response = requests.post(
            f"{API_URL}/api/papers/analyze",
            headers=headers,
            files=files
        )
        
        # Print the status code and response
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            print("Success!")
            print(response.json())
        else:
            print(f"Error: {response.text}")

if __name__ == "__main__":
    test_analyze_paper() 