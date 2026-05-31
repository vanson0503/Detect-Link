import logging
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.models.request import DetectRequest
from app.models.response import DetectResponse
from app.services.detector import VideoDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "API dùng để phát hiện và bóc tách các luồng stream video (m3u8, mpd, mp4, ts...) "
        "từ một trang web chỉ định. Trả về link video trực tiếp kèm theo các headers gốc "
        "(User-Agent, Referer, Cookie) phục vụ việc download bằng FFmpeg trên mobile."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for convenience
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post(
    f"{settings.API_V1_STR}/detect",
    response_model=DetectResponse,
    status_code=status.HTTP_200_OK,
    summary="Phát hiện link video từ trang web",
    description="Nhận URL trang web, mở trình duyệt ngầm Playwright để bắt các request stream video và trả về link."
)
async def detect_video_links(payload: DetectRequest):
    logger.info(f"Received detection request for URL: {payload.url}")
    try:
        title, videos = await VideoDetector.detect(
            url=payload.url,
            timeout_ms=payload.timeout,
            wait_time_ms=payload.wait_time,
            custom_headers=payload.headers,
            custom_user_agent=payload.user_agent
        )
        
        return DetectResponse(
            success=True,
            url=payload.url,
            title=title or "N/A",
            videos=videos,
            error=None
        )
    except Exception as e:
        logger.error(f"Error during video link detection: {str(e)}", exc_info=True)
        return DetectResponse(
            success=False,
            url=payload.url,
            title=None,
            videos=[],
            error=str(e)
        )

@app.get("/", include_in_schema=False)
async def root_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")
