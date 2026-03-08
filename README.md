# Web Page Summary Agent

A Python CLI tool that extracts content from any web page, including JavaScript rendered SPAs and dynamically loaded content, and generates structured summaries using Microsoft Foundry.

## Features

- **Dynamic content support** Uses a headless Chromium browser (Playwright) to render JavaScript heavy pages before extracting content
- **Batch processing** Pass a text file with multiple URLs or list them as arguments
- **AI powered summaries** Uses a Microsoft Foundry model deployment to produce structured summaries
- **Customisable prompts** Edit `prompt.txt` or pass a custom prompt file with `-p`
- **Markdown output** Results can be saved to a `.md` file or printed to the console

## Prerequisites

- Python 3.11+
- A Microsoft Foundry resource with a deployed model (e.g. `gpt-4o`)

## Setup

1. **Clone the repo and install dependencies:**

   ```bash
   cd web-page-summary-agent
   pip install -r requirements.txt
   python -m playwright install chromium
   ```

2. **Configure environment variables:**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and fill in your Microsoft Foundry values:

   | Variable | Description |
   |---|---|
   | `FOUNDRY_ENDPOINT` | Your Microsoft Foundry resource endpoint |
   | `FOUNDRY_API_KEY` | Your API key |
   | `FOUNDRY_DEPLOYMENT` | Model deployment name (default: `gpt-4o`) |
   | `FOUNDRY_API_VERSION` | API version (default: `2024-12-01-preview`) |

## Usage

### Summarise URLs from a file

Add URLs to `urls.txt` (one per line), then run:

```bash
python main.py urls.txt
```

### Save output to a markdown file

```bash
python main.py urls.txt -o summaries.md
```

### Pass URLs directly as arguments

```bash
python main.py https://example.com/page-one https://example.com/page-two
```

### Use a custom system prompt

```bash
python main.py urls.txt -p my-prompt.txt
```

## Project Structure

```
web-page-summary-agent/
├── main.py            # CLI entry point and pipeline orchestration
├── extractor.py       # Headless browser extraction for JS rendered pages
├── summariser.py      # Microsoft Foundry integration and summarisation
├── prompt.txt         # Default system prompt (customisable)
├── urls.txt           # Sample input file with URLs
├── requirements.txt   # Python dependencies
├── .env.example       # Environment variable template
└── .gitignore
```

## Output Format

Each summary includes a concise bullet point overview with a link back to the source page. Customise the output format by editing `prompt.txt` or providing your own prompt file.