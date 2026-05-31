import requests
import json
import time
import sys

# Ensure console supports utf-8 output
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

def test_video_detection():
    url = "http://localhost:8000/api/v1/detect"
    
    # We will test using a public HLS stream URL as a simple case
    test_target_url = "https://vlxx.moi/video/xuat-tinh-vao-lon-em-gai-ngoan-xinh-dam-tong-hop/3150/"
    
    payload = {
        "url": test_target_url,
        "timeout": 15000,
        "wait_time": 5000
    }
    
    print(f"[*] Sending detect request to: {url}")
    print(f"[*] Target URL to inspect: {test_target_url}")
    
    try:
        start_time = time.time()
        response = requests.post(url, json=payload)
        elapsed = time.time() - start_time
        
        print(f"[+] Status Code: {response.status_code}")
        print(f"[+] Time taken: {elapsed:.2f} seconds")
        
        if response.status_code == 200:
            result = response.json()
            print("\n[+] Response JSON (Formatted):")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"[-] Error Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("[-] Connection failed. Is the API server running?")

if __name__ == "__main__":
    test_video_detection()
