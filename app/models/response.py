from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class DetectedVideo(BaseModel):
    url: str = Field(..., description="Direct link to the video stream/file.")
    type: str = Field(..., description="Format type of the stream, e.g., hls, dash, mp4, ts, unknown.")
    headers: Dict[str, str] = Field(
        default_factory=dict,
        description="HTTP Headers extracted from the intercepted request, necessary for downloading via FFmpeg (e.g., Referer, User-Agent, Cookie, etc.)."
    )
    thumbnail: Optional[str] = Field(None, description="URL of the video thumbnail/preview image if available.")
    has_audio: Optional[bool] = Field(None, description="True if the video stream has audio, False if it is mute, None if undetermined.")
    quality: Optional[str] = Field(None, description="Quality/resolution of the video stream (e.g., '1080p', '720p').")

class DetectResponse(BaseModel):
    success: bool = Field(..., description="True if stream extraction succeeded or checked without fatal crash.")
    url: str = Field(..., description="Original URL that was checked.")
    title: Optional[str] = Field(None, description="Title of the target webpage.")
    videos: List[DetectedVideo] = Field(default_factory=list, description="List of detected video streams.")
    error: Optional[str] = Field(None, description="Detailed error description if success is False.")
