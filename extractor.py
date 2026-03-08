"""
extractor.py - Fetches and extracts main content from Azure update URLs.

Uses Playwright (headless Chromium) to render JavaScript-heavy pages like
the Azure Updates portal before extracting content with BeautifulSoup.
"""

from __future__ import annotations

import time

from bs4 import BeautifulSoup
from dataclasses import dataclass
from playwright.sync_api import sync_playwright, Browser, Playwright

# Phrases that indicate the page returned a bot-detection / challenge
# page rather than the real content.
_BOT_DETECTION_PHRASES = [
    "please refresh your browser",
    "access denied",
    "enable javascript and cookies to continue",
    "checking your browser",
    "just a moment",
    "verify you are human",
    "please verify you are a human",
    "attention required",
    "pardon our interruption",
]


@dataclass
class ExtractedPage:
    """Holds the extracted content from a single URL."""
    url: str
    title: str
    content: str
    success: bool
    error: str | None = None


class BrowserExtractor:
    """
    Manages a reusable headless browser instance for extracting content
    from JavaScript-rendered pages. Use as a context manager.

    Usage:
        with BrowserExtractor() as extractor:
            page = extractor.extract("https://...")
    """

    def __init__(self) -> None:
        self._pw: Playwright | None = None
        self._browser: Browser | None = None

    def __enter__(self) -> "BrowserExtractor":
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        return self

    def __exit__(self, *exc) -> None:
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()

    # ------------------------------------------------------------------ #
    #  Public API                                                         #
    # ------------------------------------------------------------------ #

    def extract(self, url: str, wait_seconds: int = 10, max_retries: int = 3) -> ExtractedPage:
        """Navigate to *url*, wait for dynamic content, then extract text.

        Retries up to *max_retries* times when bot-detection pages are
        returned instead of the real content.
        """
        if not self._browser:
            raise RuntimeError("BrowserExtractor must be used as a context manager.")

        last_error: str | None = None

        for attempt in range(1, max_retries + 1):
            result = self._try_extract(url, wait_seconds)

            if not result.success:
                return result  # genuine failure — no point retrying

            if not _is_bot_detection(result.title, result.content):
                return result  # real content — done

            # Bot detection page — retry after a short delay
            last_error = (
                f"Bot-detection page received (attempt {attempt}/{max_retries})."
            )
            if attempt < max_retries:
                time.sleep(2 * attempt)  # back off a little between retries

        return ExtractedPage(
            url=url, title="", content="", success=False,
            error=(
                "Page returned a bot-detection challenge after "
                f"{max_retries} attempts. Try again later."
            ),
        )

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                   #
    # ------------------------------------------------------------------ #

    def _try_extract(self, url: str, wait_seconds: int) -> ExtractedPage:
        """Single extraction attempt."""

        try:
            context = self._browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="en-US",
                viewport={"width": 1280, "height": 720},
            )
            # Remove navigator.webdriver flag to avoid bot detection
            context.add_init_script(
                'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            )
            page = context.new_page()

            # Navigate and wait for network to fully settle
            page.goto(url, wait_until="networkidle", timeout=30_000)

            # Wait for dynamic content to appear after JS hydration.
            try:
                page.wait_for_selector(
                    "h2, h3, article, main p, [role='main']",
                    timeout=wait_seconds * 1000,
                )
            except Exception:
                # Timeout is acceptable — page may already be loaded
                pass

            # Give any remaining XHR/fetch calls a moment to complete
            page.wait_for_timeout(2000)

            html = page.content()
            context.close()

            title, content = _extract_content(html)

            if not content.strip():
                return ExtractedPage(
                    url=url, title=title, content="", success=False,
                    error="No meaningful content could be extracted from the page.",
                )
            return ExtractedPage(url=url, title=title, content=content, success=True)

        except Exception as e:
            return ExtractedPage(
                url=url, title="", content="", success=False,
                error=f"Browser extraction error: {e}",
            )


# ---------------------------------------------------------------------- #
#  Bot-detection heuristic                                                #
# ---------------------------------------------------------------------- #

def _is_bot_detection(title: str, content: str) -> bool:
    """Return True if the title or content looks like a bot-challenge page."""
    combined = f"{title}\n{content}".lower()
    if any(phrase in combined for phrase in _BOT_DETECTION_PHRASES):
        return True
    # Very short content with no real substance is suspicious
    if len(content.strip()) < 200 and "refresh" in combined:
        return True
    return False


# ---------------------------------------------------------------------- #
#  HTML → text helpers                                                    #
# ---------------------------------------------------------------------- #

def _extract_content(html: str) -> tuple[str, str]:
    """
    Parse the fully-rendered HTML and extract the page title and main
    textual content from any web page.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove noise
    for tag in soup.find_all(
        ["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]
    ):
        tag.decompose()

    # Title — find the most descriptive heading on the page.
    # Strategy: collect candidates from <title>, first h1, and first h2,
    # then pick the most specific (longest) one.
    title = ""
    _GENERIC_HEADINGS = {
        "home", "menu", "navigation", "search", "global",
        "additional resources", "related resources", "footer",
        "skip to main content", "skip to content",
    }

    candidates: list[str] = []

    # 1. <title> tag — split on common separators and take the longest part
    if soup.title:
        raw_title = soup.title.get_text(strip=True)
        for sep in [" | ", " — ", " – ", " - ", " · "]:
            if sep in raw_title:
                parts = [p.strip() for p in raw_title.split(sep) if p.strip()]
                # Take the longest segment (usually the article title)
                if parts:
                    candidates.append(max(parts, key=len))
                break
        else:
            candidates.append(raw_title)

    # 2. First non-generic h1 and first non-generic h2 (separately)
    for tag_name in ["h1", "h2"]:
        for heading in soup.find_all(tag_name):
            text = heading.get_text(strip=True)
            if text and text.lower() not in _GENERIC_HEADINGS:
                candidates.append(text)
                break

    # Pick the longest candidate — more descriptive titles tend to be longer
    candidates = [c for c in candidates if c]
    title = max(candidates, key=len) if candidates else ""

    # Try targeted content containers
    main_content = (
        soup.find("main")
        or soup.find("article")
        or soup.find("div", {"role": "main"})
        or soup.find("div", id="main")
        or soup.body
        or soup
    )

    # Extract meaningful text elements
    lines: list[str] = []
    for element in main_content.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th",
         "blockquote", "pre", "code", "span", "div"]
    ):
        # Skip containers that have many child block-level elements
        # (to avoid duplicating text that will be captured from children)
        if element.name in ("div", "span"):
            block_children = element.find_all(
                ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th"],
                recursive=False,
            )
            if block_children:
                continue

        text = element.get_text(separator=" ", strip=True)
        if not text or len(text) < 3:
            continue

        # Skip duplicated lines
        if text in lines:
            continue

        prefix = ""
        if element.name and element.name.startswith("h"):
            level = element.name[1]
            prefix = "#" * int(level) + " "
        elif element.name == "li":
            prefix = "- "

        lines.append(f"{prefix}{text}")

    content = "\n".join(lines)

    # Truncate very long pages to stay within token limits
    max_chars = 12_000
    if len(content) > max_chars:
        content = content[:max_chars] + "\n\n[Content truncated...]"

    return title, content
