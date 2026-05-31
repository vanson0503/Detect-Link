import requests
import urllib3
urllib3.disable_warnings()

url = "https://fullcliphot.us/lehaydoi-chubby-mac-bikini-sexy-anh-mat-moi-goi-day-dam-dang-p2/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
try:
    resp = requests.get(url, headers=headers, verify=False)
    print(f"Status Code: {resp.status_code}")
    print(f"Text sample: {resp.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
