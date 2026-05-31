import os
import subprocess
import sys
import asyncio
import uvicorn

# Fix for Playwright NotImplementedError on Windows with Uvicorn (local dev only)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

def install_playwright_dependencies():
    print("[*] Checking and installing Playwright Chromium browser binary...")
    try:
        import playwright
    except ImportError:
        print("[!] Playwright is not installed. Please run 'pip install -r requirements.txt' first.")
        return

    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("[+] Playwright Chromium installed successfully.")
        else:
            print(f"[!] Playwright installation returned exit code {result.returncode}")
            print(f"Detail: {result.stderr or result.stdout}")
    except Exception as e:
        print(f"[-] Could not auto-install Playwright browsers: {str(e)}")

if __name__ == "__main__":
    # Only auto-install on local dev (Docker installs during build)
    if sys.platform == 'win32':
        install_playwright_dependencies()

    # Support PORT env var for cloud deployments (Fly.io, Render, Railway)
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")

    print(f"[*] Starting FastAPI Web Server at http://{host}:{port} ...")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False
    )

