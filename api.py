"""
api.py - FastAPI HTTP wrapper for the Web Page Summary Agent.

Exposes the extract and summarise pipeline as a REST API so the
GitHub Spark frontend can call it.  The /summarise endpoint streams
Server-Sent Events (SSE) so the frontend can show real-time progress.
"""

import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl

from extractor import AsyncBrowserExtractor, ExtractedPage
from summariser import get_client, summarise_content, load_system_prompt

# --------------------------------------------------------------------------- #
#  Lifespan: keep one browser instance alive across requests                   #
# --------------------------------------------------------------------------- #

_browser: AsyncBrowserExtractor | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _browser
    _browser = AsyncBrowserExtractor()
    await _browser.__aenter__()
    yield
    await _browser.__aexit__(None, None, None)
    _browser = None


app = FastAPI(
    title="Web Page Summary Agent",
    version="1.0.0",
    lifespan=lifespan,
)

# --------------------------------------------------------------------------- #
#  CORS — allow the Spark frontend origin                                      #
# --------------------------------------------------------------------------- #

allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
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


@app.post("/summarise")
async def summarise(request: SummariseRequest):
    if not _browser:
        raise HTTPException(status_code=503, detail="Browser not initialised.")

    def _sse(event: str, data: dict | str) -> str:
        payload = json.dumps(data) if isinstance(data, dict) else data
        return f"event: {event}\ndata: {payload}\n\n"

    async def generate():
        system_prompt = request.system_prompt or load_system_prompt()
        auth = request.auth
        total = len(request.urls)

        yield _sse("status", {"message": f"Starting — {total} URL(s) to process"})

        try:
            client = get_client(
                endpoint=request.foundry_endpoint,
                auth_method=auth.method,
                api_key=auth.api_key,
                tenant_id=auth.tenant_id,
                client_id=auth.client_id,
                client_secret=auth.client_secret,
            )
        except Exception as e:
            yield _sse("error", {"message": f"Foundry auth failed: {e}"})
            yield _sse("done", {"total": total, "succeeded": 0, "failed": total})
            return

        yield _sse("status", {"message": "Connected to Microsoft Foundry"})

        succeeded = 0
        failed = 0

        for i, url_obj in enumerate(request.urls, 1):
            url = str(url_obj)

            # --- Extract ---
            yield _sse("status", {"message": f"[{i}/{total}] Extracting content from {url}"})
            page: ExtractedPage = await _browser.extract(url)

            if not page.success:
                failed += 1
                yield _sse("result", {
                    "url": url, "title": "", "summary": "",
                    "success": False, "error": page.error,
                })
                continue

            yield _sse("status", {"message": f"[{i}/{total}] Extracted: {page.title}"})

            # --- Summarise ---
            yield _sse("status", {"message": f"[{i}/{total}] Summarising with Foundry..."})
            summary = summarise_content(
                client, page.url, page.title, page.content,
                deployment=request.foundry_deployment,
                system_prompt=system_prompt,
            )

            if summary.success:
                succeeded += 1
            else:
                failed += 1

            yield _sse("result", {
                "url": summary.url,
                "title": summary.title,
                "summary": summary.summary,
                "success": summary.success,
                "error": summary.error,
            })

        yield _sse("done", {"total": total, "succeeded": succeeded, "failed": failed})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
