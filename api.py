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


class AuthConfig(BaseModel):
    method: str  # "entra" or "apikey"
    entra_type: str | None = None  # "managed-identity" or "service-principal"
    api_key: str | None = None
    tenant_id: str | None = None
    client_id: str | None = None
    client_secret: str | None = None


class SummariseRequest(BaseModel):
    urls: list[HttpUrl]
    foundry_endpoint: str
    foundry_deployment: str
    auth: AuthConfig
    system_prompt: str | None = None


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

    system_prompt = request.system_prompt or load_system_prompt()
    auth = request.auth
    client = get_client(
        endpoint=request.foundry_endpoint,
        auth_method=auth.method,
        api_key=auth.api_key,
        tenant_id=auth.tenant_id,
        client_id=auth.client_id,
        client_secret=auth.client_secret,
    )
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
            deployment=request.foundry_deployment,
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
