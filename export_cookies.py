#!/usr/bin/env python3
"""
Hướng dẫn xuất YouTube cookies.txt để upload lên VPS

CÁCH 1 (Khuyên dùng): Dùng extension trình duyệt
================================================
1. Cài extension "Get cookies.txt LOCALLY" trên Chrome/Firefox:
   - Chrome: https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc
   - Firefox: https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/

2. Mở YouTube.com và đăng nhập tài khoản Google

3. Click vào icon extension → chọn "Export" → lưu file cookies.txt

4. Upload lên VPS:
   scp cookies.txt user@your-vps-ip:/path/to/Detect-Link/

   Hoặc copy nội dung và tạo file tay:
   nano /path/to/Detect-Link/cookies.txt
   (paste nội dung rồi Ctrl+X, Y, Enter)

CÁCH 2: Dùng yt-dlp export từ máy local (cần Chrome/Firefox đang đăng nhập YT)
=================================================================================
Chạy lệnh này trên máy Windows local của bạn:

  yt-dlp --cookies-from-browser chrome --cookies cookies.txt --skip-download https://www.youtube.com/watch?v=Pm_wbkDtI3k

Hoặc Firefox:
  yt-dlp --cookies-from-browser firefox --cookies cookies.txt --skip-download https://www.youtube.com/watch?v=Pm_wbkDtI3k

Sau đó upload cookies.txt lên VPS.


SAU KHI UPLOAD COOKIES.TXT LÊN VPS
=====================================
File cookies.txt cần đặt tại: /path/to/Detect-Link/cookies.txt
(code tự động detect)

Hoặc set environment variable:
  export YOUTUBE_COOKIES_FILE=/path/to/cookies.txt

Sau đó restart server:
  systemctl restart your-service
  # hoặc
  python run.py


LƯU Ý QUAN TRỌNG
==================
- Cookies YouTube có thời hạn ~1-2 tuần, cần renew định kỳ
- Dùng tài khoản phụ, không dùng tài khoản Google chính
- Không chia sẻ file cookies.txt với ai
- Thêm cookies.txt vào .gitignore để không upload lên GitHub

Thêm vào .gitignore:
  cookies.txt
  *.cookies
"""

import subprocess
import sys
import os

def export_cookies_from_browser(browser="chrome", output="cookies.txt"):
    """Export YouTube cookies từ browser đang chạy"""
    print(f"[*] Đang xuất cookies từ {browser}...")
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "yt_dlp",
                f"--cookies-from-browser", browser,
                "--cookies", output,
                "--skip-download",
                "--quiet",
                "https://www.youtube.com/watch?v=Pm_wbkDtI3k"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        if os.path.isfile(output) and os.path.getsize(output) > 100:
            print(f"[+] Đã xuất cookies thành công: {output}")
            print(f"    Kích thước: {os.path.getsize(output)} bytes")
            return True
        else:
            print(f"[!] Không xuất được cookies: {result.stderr}")
            return False
    except Exception as e:
        print(f"[-] Lỗi: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("YouTube Cookies Exporter cho Detect-Link VPS")
    print("=" * 60)
    
    output_file = "cookies.txt"
    
    # Thử Chrome trước, rồi Firefox
    for browser in ["chrome", "firefox", "edge"]:
        if export_cookies_from_browser(browser, output_file):
            print(f"\n[*] Bước tiếp theo:")
            print(f"    Upload {output_file} lên VPS:")
            print(f"    scp {output_file} user@your-vps-ip:/path/to/Detect-Link/")
            break
    else:
        print("\n[!] Không thể tự động export cookies.")
        print("    Vui lòng dùng extension trình duyệt theo hướng dẫn ở trên.")
