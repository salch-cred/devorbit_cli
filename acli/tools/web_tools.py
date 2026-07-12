"""API-key-free DuckDuckGo web search and page-text extraction."""
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup
from acli.tools.policy import ensure_network_allowed


class ToolError(Exception):
    pass


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 DevOrbit/0.2"
}


def _clean_ddg_url(url: str) -> str:
    if "duckduckgo.com/l/" in url:
        encoded = parse_qs(urlparse(url).query).get("uddg", [url])[0]
        return unquote(encoded)
    return url


def web_search(query: str, max_results: int = 8, settings=None) -> str:
    """Search DuckDuckGo HTML without an API key."""
    if settings is not None:
        ensure_network_allowed("https://html.duckduckgo.com", settings)
    max_results = max(1, min(int(max_results), 15))
    try:
        response = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=HEADERS,
            timeout=25,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ToolError("DuckDuckGo search failed: " + str(exc)) from exc

    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    for result in soup.select(".result"):
        link = result.select_one(".result__a")
        if not link:
            continue
        snippet = result.select_one(".result__snippet")
        results.append(
            {
                "title": link.get_text(" ", strip=True),
                "url": _clean_ddg_url(link.get("href", "")),
                "snippet": snippet.get_text(" ", strip=True) if snippet else "",
            }
        )
        if len(results) >= max_results:
            break

    if not results:
        return "No results found. DuckDuckGo may have temporarily blocked automated requests."
    return "\n\n".join(
        str(i + 1) + ". " + item["title"] + "\n" + item["url"] + "\n" + item["snippet"]
        for i, item in enumerate(results)
    )


def fetch_web_page(url: str, max_chars: int = 12000, settings=None) -> str:
    """Fetch a public web page and return readable text."""
    if not url.startswith(("http://", "https://")):
        raise ToolError("Only http:// and https:// URLs are allowed")
    if settings is not None:
        ensure_network_allowed(url, settings)
    try:
        response = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ToolError("Page fetch failed: " + str(exc)) from exc

    content_type = response.headers.get("content-type", "")
    if "text" not in content_type and "json" not in content_type and "xml" not in content_type:
        raise ToolError("Unsupported content type: " + content_type)

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else response.url
    text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
    output = "Title: " + title + "\nURL: " + response.url + "\n\n" + text
    return output[:max_chars] + ("\n...[truncated]" if len(output) > max_chars else "")
