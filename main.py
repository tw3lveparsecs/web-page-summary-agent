"""
main.py - CLI entry point for the Web Page Summary Agent.

Summarises any web page (including JavaScript-rendered SPAs) using a
headless browser for extraction and Microsoft Foundry for AI summarisation.

Usage:
    python main.py urls.txt                  # Read URLs from a file
    python main.py <url1> <url2> ...         # Pass URLs as arguments
    python main.py urls.txt -o output.md     # Save results to a file
"""

import argparse
import sys
import os
from pathlib import Path

from extractor import BrowserExtractor, ExtractedPage
from summariser import get_client, summarise_content, load_system_prompt, Summary


def load_urls(sources: list[str]) -> list[str]:
    """
    Load URLs from arguments. If an argument is a file path, read URLs
    from the file (one per line). Otherwise treat it as a URL.
    """
    urls: list[str] = []
    for source in sources:
        if os.path.isfile(source):
            with open(source, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        urls.append(line)
        else:
            urls.append(source)
    return urls


def format_summary(summary: Summary, index: int) -> str:
    """Format a single summary for output."""
    divider = "=" * 80
    header = f"\n{divider}\n## [{index}] {summary.title or 'Untitled'}\n**URL:** {summary.url}\n{divider}\n"

    if summary.success:
        return f"{header}\n{summary.summary}\n"
    else:
        return f"{header}\n❌ Error: {summary.error}\n"


def format_extraction_error(page: ExtractedPage, index: int) -> str:
    """Format an extraction error for output."""
    divider = "=" * 80
    return (
        f"\n{divider}\n## [{index}] Failed to extract\n"
        f"**URL:** {page.url}\n{divider}\n"
        f"\n❌ Error: {page.error}\n"
    )


def run(urls: list[str], output_path: str | None, prompt_path: str | None = None) -> None:
    """Main pipeline: extract content → summarise → output results."""

    # Load the system prompt once for all summaries
    system_prompt = load_system_prompt(prompt_path)
    prompt_source = prompt_path or "prompt.txt (default)"
    print(f"\n📋 Processing {len(urls)} URL(s)...")
    print(f"📝 System prompt loaded from: {prompt_source}\n")

    # --- Step 1: Extract content using headless browser ---
    print("🔍 Launching headless browser and extracting content...")
    extracted: dict[str, ExtractedPage] = {}
    with BrowserExtractor() as browser:
        for i, url in enumerate(urls, 1):
            print(f"  ⏳ [{i}/{len(urls)}] Loading: {url}")
            page = browser.extract(url)
            extracted[page.url] = page
            status = "✅" if page.success else "❌"
            label = page.title or page.url
            print(f"  {status} {label}")

    # --- Step 2: Summarise with Microsoft Foundry ---
    successful_pages = [p for p in extracted.values() if p.success]
    if not successful_pages:
        print("\n⚠️  No pages were successfully extracted. Nothing to summarise.")
        return

    print(f"\n🤖 Summarising {len(successful_pages)} page(s) with Microsoft Foundry...")
    client = get_client()

    summaries: list[Summary] = []
    for i, page in enumerate(successful_pages, 1):
        label = page.title or page.url
        print(f"  ⏳ [{i}/{len(successful_pages)}] {label}")
        summary = summarise_content(client, page.url, page.title, page.content, system_prompt=system_prompt)
        summaries.append(summary)
        status = "✅" if summary.success else "❌"
        print(f"  {status} {label}")

    # --- Step 3: Format and output results ---
    results: list[str] = ["# Web Page Summaries\n"]
    idx = 1

    # Maintain original URL order
    for url in urls:
        page = extracted.get(url)
        if page is None:
            continue
        if not page.success:
            results.append(format_extraction_error(page, idx))
        else:
            matching = [s for s in summaries if s.url == url]
            if matching:
                results.append(format_summary(matching[0], idx))
        idx += 1

    output_text = "\n".join(results)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_text)
        print(f"\n💾 Results saved to: {output_path}")
    else:
        print(output_text)

    # Print summary stats
    ok = sum(1 for s in summaries if s.success)
    fail_extract = sum(1 for p in extracted.values() if not p.success)
    fail_summary = sum(1 for s in summaries if not s.success)
    print(f"\n📊 Results: {ok} summarised, {fail_extract} extraction failures, {fail_summary} summarisation failures")


def main():
    parser = argparse.ArgumentParser(
        description="Summarise any web page using a headless browser and Microsoft Foundry.",
        epilog="Examples:\n"
               "  python main.py urls.txt\n"
               "  python main.py urls.txt -o summaries.md\n"
               "  python main.py https://example.com/some-page\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "sources",
        nargs="+",
        help="One or more URLs or path(s) to text files containing URLs (one per line).",
    )
    parser.add_argument(
        "-o", "--output",
        help="Path to save the output markdown file. If omitted, prints to stdout.",
    )
    parser.add_argument(
        "-p", "--prompt",
        help="Path to a custom system prompt text file. Defaults to prompt.txt in the project root.",
    )

    args = parser.parse_args()
    urls = load_urls(args.sources)

    if not urls:
        print("❌ No URLs provided. Pass URLs as arguments or in a text file.")
        sys.exit(1)

    run(urls, args.output, args.prompt)


if __name__ == "__main__":
    main()
