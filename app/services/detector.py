import asyncio
import logging
import sys
import subprocess
from typing import List, Dict, Set, Tuple
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright
from app.models.response import DetectedVideo
from app.core.config import settings

logger = logging.getLogger(__name__)

TIKTOK_DOMAINS = {"tiktok.com", "www.tiktok.com", "m.tiktok.com", "vm.tiktok.com"}

def _is_tiktok_url(url: str) -> bool:
    try:
        domain = urlparse(url).netloc.lower()
        return any(d in domain for d in TIKTOK_DOMAINS)
    except Exception:
        return False

def get_stream_type_from_url_or_content_type(url: str, content_type: str = "") -> str:
    url_lower = url.lower()
    ct_lower = content_type.lower()
    
    if ".m3u8" in url_lower or "m3u8" in url_lower or "mpegurl" in ct_lower:
        return "hls"
    elif ".mpd" in url_lower or "dash+xml" in ct_lower:
        return "dash"
    elif ".mp4" in url_lower or "video/mp4" in ct_lower:
        return "mp4"
    elif ".webm" in url_lower or "video/webm" in ct_lower:
        return "webm"
    elif ".ts" in url_lower or "video/mp2t" in ct_lower:
        return "ts"
    elif ".m4s" in url_lower:
        return "m4s"
    elif "video/" in ct_lower:
        return "video"
    else:
        return "unknown"

class VideoDetector:
    @staticmethod
    async def _detect_yt_dlp(url: str, ua: str, custom_headers: Dict[str, str] = None) -> Tuple[str, List[DetectedVideo]]:
        import os
        import yt_dlp
        
        base_opts = {
            'quiet': True,
            'skip_download': True,
            'user_agent': ua,
            'noplaylist': True,
        }
        
        if custom_headers:
            base_opts['http_headers'] = custom_headers
        
        # Support YouTube cookies file to bypass bot detection on server/VPS
        # Set YOUTUBE_COOKIES_FILE=/path/to/cookies.txt on the server
        cookies_file = os.environ.get("YOUTUBE_COOKIES_FILE", "")
        if not cookies_file:
            # Auto-detect cookies.txt at project root (two levels up from app/services/)
            default_cookies = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "cookies.txt")
            if os.path.isfile(default_cookies):
                cookies_file = os.path.normpath(default_cookies)
        if cookies_file:
            base_opts['cookiefile'] = cookies_file
            logger.info(f"Using YouTube cookies file: {cookies_file}")
        
        # Auto-detect Node.js for yt-dlp JS runtime (needed by web client for n-challenge)
        # yt-dlp expects js_runtimes as a dict: {"node": {"path": "/path/to/node"}}
        js_runtimes_env = os.environ.get("YT_DLP_JS_RUNTIMES", "")
        js_runtimes = None
        if not js_runtimes_env:
            import shutil
            node_path = shutil.which("node")
            if node_path:
                js_runtimes = {"node": {"path": node_path}}
                logger.info(f"Auto-detected Node.js at: {node_path}")
        if js_runtimes:
            base_opts['js_runtimes'] = js_runtimes
        
        loop = asyncio.get_event_loop()
        info = None
        
        parsed = urlparse(url)
        is_youtube = 'youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc
        
        if is_youtube:
            # Strategy:
            # - With cookies + node.js: use 'web' client (full quality, authenticated)
            # - Without cookies: use 'android_vr' (no PO Token, no JS runtime needed)
            # NOTE: android_vr and ios clients do NOT support cookies (yt-dlp skips them)
            if cookies_file and js_runtimes:
                youtube_player_clients = ["web", "android_vr"]
                logger.info("YouTube cookies + Node.js available, using web client")
            elif cookies_file:
                # cookies but no JS runtime - web won't solve n-challenge well, try anyway
                youtube_player_clients = ["web", "android_vr"]
                logger.info("YouTube cookies available (no JS runtime), trying web client")
            else:
                youtube_player_clients = ["android_vr", "android"]
                logger.info("No YouTube cookies, using android_vr client (no PO Token needed)")
            
            for client in youtube_player_clients:
                ydl_opts = dict(base_opts)
                ydl_opts['extractor_args'] = {
                    'youtube': {
                        'player_client': [client],
                    },
                }
                try:
                    info = await loop.run_in_executor(
                        None,
                        lambda opts=ydl_opts: yt_dlp.YoutubeDL(opts).extract_info(url, download=False)
                    )
                    if info:
                        _formats = info.get("formats", [])
                        if not _formats and info.get("url"):
                            _formats = [info]
                        # Filter out mhtml (storyboard) formats - only count real video/audio
                        real_formats = [f for f in _formats if f.get("ext") not in ("mhtml",) and f.get("url")]
                        if real_formats:
                            logger.info(f"yt-dlp succeeded with player_client={client}, {len(real_formats)} formats")
                            break
                        else:
                            logger.info(f"yt-dlp client={client} returned no real formats, trying next...")
                            info = None
                except Exception as e:
                    logger.info(f"yt-dlp extraction failed with client={client}: {str(e)}")
                    info = None
        else:
            # Non-YouTube: use generic with impersonation
            ydl_opts = dict(base_opts)
            ydl_opts['extractor_args'] = {'generic': {'impersonate': ['chrome']}}
            try:
                info = await loop.run_in_executor(
                    None,
                    lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(url, download=False)
                )
            except Exception as e:
                logger.info(f"yt-dlp extraction failed or unsupported: {str(e)}")
            
        if not info:
            return "", []
            
        if info.get("_type") == "playlist" or "entries" in info:
            entries = info.get("entries") or []
            if entries and entries[0]:
                info = entries[0]
                if info.get("_type") == "url" and info.get("url") and info.get("url") != url:
                    try:
                        info = await loop.run_in_executor(
                            None,
                            lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(info["url"], download=False)
                        )
                    except Exception:
                        pass
                
        page_title = info.get("title", "")
        thumbnail_url = info.get("thumbnail") or None
        detected_videos = []
        
        formats = info.get("formats", [])
        if not formats and info.get("url"):
            formats = [info]
            
        for f in formats:
            video_url = f.get("url")
            if not video_url:
                continue
            
            ext = f.get("ext") or ""
            protocol = f.get("protocol") or ""
            
            stream_type = "unknown"
            if "m3u8" in protocol or ext == "m3u8":
                stream_type = "hls"
            elif "mpd" in protocol or ext == "mpd":
                stream_type = "dash"
            elif ext in ["mp4", "webm", "ts", "m4a", "3gp", "mp3"]:
                stream_type = ext
            else:
                stream_type = get_stream_type_from_url_or_content_type(video_url)
                
            if stream_type == "unknown":
                continue
                
            f_headers = f.get("http_headers") or {}
            clean_headers = {}
            for k, v in f_headers.items():
                k_lower = k.lower()
                if k_lower in ["referer", "user-agent", "cookie", "origin", "authorization"]:
                    clean_headers[k] = v
                    
            if "Referer" not in clean_headers and "referer" not in clean_headers:
                clean_headers["Referer"] = url
            if "User-Agent" not in clean_headers and "user-agent" not in clean_headers:
                clean_headers["User-Agent"] = ua
                
            acodec = f.get("acodec")
            vcodec = f.get("vcodec")
            if acodec is None and vcodec is None:
                has_audio = True
            else:
                has_audio = acodec not in (None, "none")
                
            # Extract quality
            quality = None
            if f.get("height"):
                quality = f"{f.get('height')}p"
            elif f.get("format_note"):
                quality = f.get("format_note")
            elif f.get("resolution"):
                quality = f.get("resolution")
                
            detected_videos.append(
                DetectedVideo(
                    url=video_url,
                    type=stream_type,
                    headers=clean_headers,
                    thumbnail=thumbnail_url,
                    has_audio=has_audio,
                    quality=quality
                )
            )
            
        has_playlists = any(v.type in ["hls", "dash"] for v in detected_videos)
        if has_playlists:
            detected_videos = [v for v in detected_videos if v.type not in ["ts", "m4s", "unknown"]]
            
        return page_title, detected_videos

    @staticmethod
    async def _detect_gallery_dl(url: str, ua: str) -> Tuple[str, List[DetectedVideo]]:
        loop = asyncio.get_event_loop()
        def run_gallery_dl():
            try:
                cmd = [
                    sys.executable, "-m", "gallery_dl",
                    "-g",
                    "-o", f"downloader.http.headers={{'User-Agent': '{ua}', 'Referer': '{url}'}}",
                    url
                ]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                return result.returncode, result.stdout, result.stderr
            except Exception as e:
                logger.info(f"gallery-dl execution failed: {str(e)}")
                return -1, "", str(e)
                
        returncode, stdout, stderr = await loop.run_in_executor(None, run_gallery_dl)
        
        detected_videos = []
        if returncode == 0 and stdout:
            lines = [line.strip() for line in stdout.splitlines() if line.strip()]
            for video_url in lines:
                stream_type = get_stream_type_from_url_or_content_type(video_url)
                
                url_lower = video_url.lower()
                is_video = False
                for ext in [".mp4", ".webm", ".mkv", ".mov", ".avi", ".m3u8", ".mpd", ".ts", "/videoplayback"]:
                    if ext in url_lower:
                        is_video = True
                        break
                
                if is_video or stream_type in ["hls", "dash", "mp4", "ts", "video"]:
                    if stream_type == "unknown":
                        stream_type = "video"
                        
                    detected_videos.append(
                        DetectedVideo(
                            url=video_url,
                            type=stream_type,
                            headers={
                                "User-Agent": ua,
                                "Referer": url
                            },
                            thumbnail=None,
                            has_audio=None,
                            quality=None
                        )
                    )
        return "", detected_videos

    @staticmethod
    async def _capture_cookies(url: str, ua: str, timeout_ms: int, custom_headers: Dict[str, str] = None) -> str:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                    ]
                )
                context_args = {
                    "user_agent": ua,
                    "viewport": {"width": 1280, "height": 720},
                    "ignore_https_errors": True
                }
                if custom_headers:
                    context_args["extra_http_headers"] = custom_headers
                context = await browser.new_context(**context_args)
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                await asyncio.sleep(3)
                cookies = await context.cookies()
                await browser.close()
                if cookies:
                    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
                    logger.info(f"Captured {len(cookies)} cookies from browser session.")
                    return cookie_str
                return ""
        except Exception as e:
            logger.warning(f"Failed to capture cookies via Playwright: {str(e)}")
            return ""

    @staticmethod
    def _inject_cookies(videos: List[DetectedVideo], cookie_string: str):
        if not cookie_string:
            return
        for v in videos:
            has_cookie = any(k.lower() == "cookie" for k in v.headers)
            if not has_cookie:
                v.headers["Cookie"] = cookie_string

    @staticmethod
    async def detect(
        url: str,
        timeout_ms: int = 15000,
        wait_time_ms: int = 3000,
        custom_headers: Dict[str, str] = None,
        custom_user_agent: str = None
    ) -> Tuple[str, List[DetectedVideo]]:
        
        ua = custom_user_agent or settings.DEFAULT_USER_AGENT
        needs_cookies = _is_tiktok_url(url)
        
        # 1. Try yt-dlp
        logger.info(f"Trying yt-dlp for URL: {url}")
        title, videos = await VideoDetector._detect_yt_dlp(url, ua, custom_headers)
        if videos:
            logger.info(f"yt-dlp successfully detected {len(videos)} video stream(s).")
            if needs_cookies:
                logger.info("Capturing browser cookies for CDN access...")
                cookies = await VideoDetector._capture_cookies(url, ua, timeout_ms, custom_headers)
                if cookies:
                    VideoDetector._inject_cookies(videos, cookies)
                    logger.info("Injected cookies into video headers for CDN access.")
            return title, videos
            
        # 2. Try gallery-dl
        logger.info(f"Trying gallery-dl for URL: {url}")
        title, videos = await VideoDetector._detect_gallery_dl(url, ua)
        if videos:
            logger.info(f"gallery-dl successfully detected {len(videos)} video stream(s).")
            if needs_cookies:
                cookies = await VideoDetector._capture_cookies(url, ua, timeout_ms, custom_headers)
                if cookies:
                    VideoDetector._inject_cookies(videos, cookies)
            return title, videos
            
        # 3. Fallback to Playwright browser sniffing (naturally captures cookies via browser context)
        logger.info(f"Falling back to Playwright browser sniffing for URL: {url}")
        return await VideoDetector._detect_playwright(
            url=url,
            timeout_ms=timeout_ms,
            wait_time_ms=wait_time_ms,
            custom_headers=custom_headers,
            custom_user_agent=custom_user_agent
        )

    @staticmethod
    async def _detect_playwright(
        url: str,
        timeout_ms: int = 15000,
        wait_time_ms: int = 3000,
        custom_headers: Dict[str, str] = None,
        custom_user_agent: str = None
    ) -> Tuple[str, List[DetectedVideo]]:
        
        detected_videos: List[DetectedVideo] = []
        seen_urls: Set[str] = set()
        page_title = ""
        ua = custom_user_agent or settings.DEFAULT_USER_AGENT

        async with async_playwright() as p:
            # Launch Chromium browser with optimizations for scraping
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ]
            )
            
            context_args = {
                "user_agent": ua,
                "viewport": {"width": 1280, "height": 720},
                "ignore_https_errors": True
            }
            if custom_headers:
                context_args["extra_http_headers"] = custom_headers
                
            context = await browser.new_context(**context_args)
            page = await context.new_page()

            def add_video(video_url: str, stream_type: str, request_headers: Dict[str, str], poster: str = None, has_audio: bool = None):
                if video_url in seen_urls:
                    return
                if not video_url.startswith(("http://", "https://")):
                    return
                    
                seen_urls.add(video_url)
                
                # Extract headers that are relevant for downloading the stream (Referer, Cookies, User-Agent, Origin)
                clean_headers = {}
                for k, v in request_headers.items():
                    k_lower = k.lower()
                    if k_lower in ["referer", "user-agent", "cookie", "origin", "authorization"]:
                        clean_headers[k] = v
                
                # Set a Referer fallback to ensure target domain bypass is sent
                if "referer" not in [k.lower() for k in clean_headers.keys()]:
                    clean_headers["Referer"] = url
                    
                # Also propagate User-Agent if not caught explicitly
                if "user-agent" not in [k.lower() for k in clean_headers.keys()]:
                    clean_headers["User-Agent"] = ua

                detected_videos.append(
                    DetectedVideo(
                        url=video_url,
                        type=stream_type,
                        headers=clean_headers,
                        thumbnail=poster,
                        has_audio=has_audio,
                        quality=None
                    )
                )

            # Listen to requests (fast response)
            async def handle_request(request):
                try:
                    req_url = request.url
                    stream_type = get_stream_type_from_url_or_content_type(req_url)
                    if stream_type in ["hls", "dash", "mp4", "ts"]:
                        add_video(req_url, stream_type, request.headers)
                except Exception as e:
                    logger.debug(f"Error handling request intercept: {str(e)}")

            # Listen to responses (checks Content-Type header)
            async def handle_response(response):
                try:
                    req = response.request
                    req_url = req.url
                    headers = response.headers
                    content_type = headers.get("content-type", "")
                    
                    stream_type = get_stream_type_from_url_or_content_type(req_url, content_type)
                    if stream_type in ["hls", "dash", "mp4", "ts", "video"]:
                        actual_type = stream_type
                        if stream_type == "video":
                            if "mpegurl" in content_type.lower():
                                actual_type = "hls"
                            elif "dash+xml" in content_type.lower():
                                actual_type = "dash"
                            else:
                                actual_type = "mp4"
                                
                        add_video(req_url, actual_type, req.headers)
                except Exception as e:
                    logger.debug(f"Error handling response intercept: {str(e)}")

            page.on("request", lambda r: asyncio.ensure_future(handle_request(r)))
            page.on("response", lambda r: asyncio.ensure_future(handle_response(r)))

            try:
                # Go to page
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                
                # Fetch page title
                page_title = await page.title()
                
                # Try to trigger auto-play or source discovery on video elements
                video_elements = await page.query_selector_all("video")
                for element in video_elements:
                    poster = None
                    try:
                        poster_attr = await element.get_attribute("poster")
                        if poster_attr:
                            poster = urljoin(url, poster_attr)
                    except Exception:
                        pass

                    try:
                        # Attempt to click or play the video element programmatically
                        await page.evaluate("(elem) => { elem.play().catch(err => {}); }", element)
                    except Exception:
                        pass
                    
                    try:
                        src = await element.get_attribute("src")
                        if src and not src.startswith("blob:"):
                            absolute_src = urljoin(url, src)
                            t = get_stream_type_from_url_or_content_type(absolute_src)
                            if t != "unknown":
                                add_video(absolute_src, t, {"User-Agent": ua, "Referer": url}, poster=poster, has_audio=True)
                    except Exception:
                        pass

                    try:
                        sources = await element.query_selector_all("source")
                        for source in sources:
                            src_val = await source.get_attribute("src")
                            if src_val and not src_val.startswith("blob:"):
                                absolute_src = urljoin(url, src_val)
                                t = get_stream_type_from_url_or_content_type(absolute_src)
                                if t != "unknown":
                                    add_video(absolute_src, t, {"User-Agent": ua, "Referer": url}, poster=poster, has_audio=True)
                    except Exception:
                        pass
                
                # Wait for any lazy network requests
                if wait_time_ms > 0:
                    await asyncio.sleep(wait_time_ms / 1000.0)
                    
                # Capture cookies from the browser context and inject into detected videos
                try:
                    browser_cookies = await context.cookies()
                    if browser_cookies:
                        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in browser_cookies)
                        VideoDetector._inject_cookies(detected_videos, cookie_str)
                        logger.info(f"Injected {len(browser_cookies)} browser cookies into detected videos.")
                except Exception as e:
                    logger.debug(f"Could not capture cookies: {str(e)}")

            except Exception as e:
                logger.warning(f"Browser navigation warning or timeout: {str(e)}")
            finally:
                await browser.close()
                
        # Post-processing: If we found master/playlist files (hls, dash, mp4), 
        # filter out individual TS/M4S segments to avoid cluttering the response.
        has_playlists = any(v.type in ["hls", "dash"] for v in detected_videos)
        if has_playlists:
            detected_videos = [v for v in detected_videos if v.type not in ["ts", "m4s", "unknown"]]
            
        return page_title, detected_videos
