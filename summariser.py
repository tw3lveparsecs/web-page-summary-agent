"""
summariser.py - Uses Microsoft Foundry to summarise extracted web page content.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv

load_dotenv()

_DEFAULT_PROMPT_FILE = Path(__file__).parent / "prompt.txt"


@dataclass
class Summary:
    """Holds the summary result for a single URL."""
    url: str
    title: str
    summary: str
    success: bool
    error: str | None = None


def load_system_prompt(prompt_path: str | Path | None = None) -> str:
    """
    Load the system prompt from a text file.

    Resolution order:
      1. Explicit *prompt_path* argument (from --prompt CLI flag)
      2. Default ``prompt.txt`` in the project root

    If neither file exists, a minimal built-in fallback is used.
    """
    paths_to_try = []
    if prompt_path:
        paths_to_try.append(Path(prompt_path))
    paths_to_try.append(_DEFAULT_PROMPT_FILE)

    for p in paths_to_try:
        if p.is_file():
            return p.read_text(encoding="utf-8").strip()

    # Minimal fallback if no file found at all
    return (
        "You are an expert content analyst. "
        "Summarise web page content clearly and concisely."
    )


def get_client(
    endpoint: str | None = None,
    auth_method: str | None = None,
    api_key: str | None = None,
    tenant_id: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
    api_version: str | None = None,
) -> AzureOpenAI:
    """
    Create and return a Microsoft Foundry client.

    When called with explicit parameters (from the API), those values are
    used directly.  When any parameter is ``None`` it falls back to the
    corresponding environment variable so the CLI still works.

    Authentication:
      - ``key``   uses *api_key* / ``FOUNDRY_API_KEY``
      - ``entra`` uses Entra ID via ``DefaultAzureCredential``
    """
    endpoint = endpoint or os.getenv("FOUNDRY_ENDPOINT")
    api_version = api_version or os.getenv("FOUNDRY_API_VERSION", "2024-12-01-preview")
    auth_method = (auth_method or os.getenv("FOUNDRY_AUTH", "key")).lower().strip()
    tenant_id = tenant_id or os.getenv("AZURE_TENANT_ID")
    client_id = client_id or os.getenv("AZURE_CLIENT_ID")
    client_secret = client_secret or os.getenv("AZURE_CLIENT_SECRET")

    if not endpoint:
        raise EnvironmentError(
            "Missing required Foundry endpoint. "
            "Provide it in the request or set FOUNDRY_ENDPOINT."
        )

    if auth_method == "entra":
        if tenant_id and client_id and client_secret:
            # Service principal
            from azure.identity import ClientSecretCredential
            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
            )
        else:
            kwargs: dict = {}
            if client_id and not client_secret:
                # User-assigned managed identity — pass the client ID
                kwargs["managed_identity_client_id"] = client_id
            credential = DefaultAzureCredential(**kwargs)
        token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )
        return AzureOpenAI(
            azure_endpoint=endpoint,
            azure_ad_token_provider=token_provider,
            api_version=api_version,
        )

    # Default: API key authentication
    api_key = api_key or os.getenv("FOUNDRY_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "Missing Foundry API key. "
            "Provide it in the request or set FOUNDRY_API_KEY."
        )

    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    )


def summarise_content(
    client: AzureOpenAI,
    url: str,
    title: str,
    content: str,
    deployment: str | None = None,
    system_prompt: str | None = None,
) -> Summary:
    """Send extracted content to Microsoft Foundry and return a structured summary."""
    deployment = deployment or os.getenv("FOUNDRY_DEPLOYMENT", "gpt-4o")
    prompt = system_prompt or load_system_prompt()

    user_message = (
        f"Summarise this web page.\n\n"
        f"URL: {url}\n"
        f"Page Title: {title}\n\n"
        f"--- Page Content ---\n{content}"
    )

    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_completion_tokens=1024,
        )
        summary_text = response.choices[0].message.content.strip()
        return Summary(url=url, title=title, summary=summary_text, success=True)

    except Exception as e:
        return Summary(
            url=url, title=title, summary="", success=False,
            error=f"Microsoft Foundry error: {e}"
        )
