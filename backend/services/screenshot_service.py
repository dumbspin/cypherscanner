"""
Screenshot Service — generates a URL to load a website screenshot via ScreenshotOne API.

ScreenshotOne is used as a replacement for Puppeteer (which requires a
headless browser process). The screenshot URL is returned to the frontend,
which loads the image directly — no server-side image fetching or storage.

This avoids memory, CPU, and bandwidth overhead on the free-tier backend.
"""

import os
from typing import Optional
from urllib.parse import quote_plus


def get_screenshot_url(normalised_url: str) -> Optional[str]:
    """
    Build a ScreenshotOne API URL that the frontend can use to display a
    live screenshot of the scanned page.

    The image is NOT fetched server-side. The frontend's <img> tag loads
    it directly from screenshotone.com, keeping backend usage minimal.

    Args:
        normalised_url: The final URL to capture a screenshot of.

    Returns:
        A fully-formed ScreenshotOne API request URL string, or None if
        the SCREENSHOTONE_API_KEY environment variable is not set.
    """
    api_key = os.getenv("SCREENSHOTONE_API_KEY", "").strip()

    if not api_key:
        # Return None gracefully when the API key is missing.
        # The frontend will display a placeholder instead of an image.
        return None

    # URL-encode the target URL so it is safely embedded as a query parameter.
    encoded_url = quote_plus(normalised_url)

    # Build the ScreenshotOne API request URL with desired capture settings:
    #   format=jpg         — compressed JPEG is suitable for preview thumbnails
    #   viewport_width=1280, viewport_height=720 — standard HD viewport
    #   delay=2            — wait 2 seconds for JavaScript-heavy pages to render
    screenshot_url = (
        f"https://api.screenshotone.com/take"
        f"?access_key={api_key}"
        f"&url={encoded_url}"
        f"&format=jpg"
        f"&viewport_width=1280"
        f"&viewport_height=720"
        f"&delay=2"
    )

    return screenshot_url
