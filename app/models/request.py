from typing import Optional, Dict
from pydantic import BaseModel, Field, HttpUrl

class DetectRequest(BaseModel):
    url: str = Field(
        ..., 
        description="URL of the webpage containing the video stream.",
        examples=["https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"]
    )
    timeout: Optional[int] = Field(
        default=15000,
        description="Maximum time in milliseconds to wait for the page to load.",
        ge=1000,
        le=60000
    )
    wait_time: Optional[int] = Field(
        default=3000,
        description="Time in milliseconds to wait after the page load to intercept delayed API requests.",
        ge=0,
        le=15000
    )
    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional custom HTTP headers to pass along when launching the browser (e.g. Cookies)."
    )
    user_agent: Optional[str] = Field(
        default=None,
        description="Optional User-Agent string to override the default browser User-Agent."
    )
