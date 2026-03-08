"""
api.py - FastAPI HTTP wrapper for the Web Page Summary Agent.

Exposes the extract and summarise pipeline as a REST API so the
GitHub Spark frontend can call it.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from extractor import BrowserExtractor, ExtractedPage
from summariser import get_client, summarise_content, load_system_prompt

# --------------------------------------------------------------------------- #
#  Lifespan: keep one browser instance alive across requests                   #
# --------------------------------------------------------------------------- #

_browser: BrowserExtractor | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _browser
    _browser = BrowserExtractor()
    _browser.__enter__()
    yield
    _browser.__exit__(None, None, None)
    _browser = None


app = FastAPI(
    title="Web Page Summary Agent",
    version="1.0.0",
    lifespan=lifespan,
)

# --------------------------------------------------------------------------- #
#  CORS — allow the Spark frontend origin                                      #
# --------------------------------------------------------------------------- #

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------- #
#  Request / response models                                                   #
# --------------------------------------------------------------------------- #


class SummariseRequest(BaseModel):
    urls: list[HttpUrl]


class PageSummary(BaseModel):
    url: str
    title: str
    summary: str
    success: bool
    error: str | None = None


class SummariseResponse(BaseModel):
    results: list[PageSummary]


# --------------------------------------------------------------------------- #
#  Endpoints                                                                   #
# --------------------------------------------------------------------------- #


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/summarise", response_model=SummariseResponse)
async def summarise(request: SummariseRequest):
    if not _browser:
        raise HTTPException(status_code=503, detail="Browser not initialised.")

    system_prompt = load_system_prompt()
    client = get_client()
    results: list[PageSummary] = []

    for url_obj in request.urls:
        url = str(url_obj)

        # Extract
        page: ExtractedPage = _browser.extract(url)
        if not page.success:
            results.append(PageSummary(
                url=url, title="", summary="", success=False, error=page.error,
            ))
            continue

        # Summarise
        summary = summarise_content(
            client, page.url, page.title, page.content,
            system_prompt=system_prompt,
        )
        results.append(PageSummary(
            url=summary.url,
            title=summary.title,
            summary=summary.summary,
            success=summary.success,
            error=summary.error,
        ))

    return SummariseResponse(results=results)
