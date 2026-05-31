import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.DEBUG)

async def main():
    url = "https://fullcliphot.us/lehaydoi-chubby-mac-bikini-sexy-anh-mat-moi-goi-day-dam-dang-p2/"
    print(f"Navigating to: {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            ignore_https_errors=True
        )
        page = await context.new_page()
        
        # intercept and print all URLs to see if it even tries to load m3u8
        page.on("request", lambda r: print(f"REQ: {r.url}") if "m3u8" in r.url or "video" in r.url else None)
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.screenshot(path="test.png")
            print(f"Title: {await page.title()}")
        except Exception as e:
            print(f"Error: {e}")
            await page.screenshot(path="test_error.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
