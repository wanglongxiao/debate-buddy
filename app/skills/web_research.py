import asyncio
import ipaddress
import re
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, unquote, urlencode, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

try:
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    from playwright.async_api import async_playwright
except ImportError:
    PlaywrightTimeoutError = TimeoutError
    async_playwright = None

from app.config import Settings
from app.models import GenerateRequest, SearchResult


TRUSTED_DOMAINS = {
    "gov": "Government",
    "edu": "University or school",
    "who.int": "International organization",
    "un.org": "International organization",
    "unicef.org": "International organization",
    "oecd.org": "International organization",
    "worldbank.org": "International organization",
    "reuters.com": "Major news",
    "apnews.com": "Major news",
    "bbc.com": "Major news",
    "npr.org": "Major news",
}

DEFAULT_CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
]

BLOCKED_RESEARCH_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "pinterest.com",
    "reddit.com",
    "scribd.com",
    "tiktok.com",
    "x.com",
    "youtube.com",
}


class WebResearchSkill:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def run(
        self, request: GenerateRequest, queries: list[str]
    ) -> tuple[list[SearchResult], list[str]]:
        warnings: list[str] = []
        provider = self._select_provider()
        query_limit = {"Quick Prep": 2, "Standard Prep": 4, "Deep Research": 7}[
            request.research_depth.value
        ]
        selected_queries = queries[:query_limit]
        if not selected_queries:
            selected_queries = [
                f"{request.motion} evidence statistics",
                f"{request.motion} benefits harms research",
            ]

        results: list[SearchResult] = []
        google_succeeded = False
        if provider == "google":
            google_batch, academic_batches = await asyncio.gather(
                self._search_google_browser(selected_queries),
                asyncio.gather(
                    *[self._search_openalex(query) for query in selected_queries],
                    return_exceptions=True,
                ),
                return_exceptions=True,
            )
            if isinstance(google_batch, Exception):
                warnings.append(
                    f"Google browser search was unavailable ({type(google_batch).__name__})."
                )
            else:
                google_succeeded = True
                results.extend(await self._enrich_google_results(request, google_batch))

            if isinstance(academic_batches, Exception):
                warnings.append("OpenAlex academic search was unavailable.")
            else:
                for batch in academic_batches:
                    if isinstance(batch, Exception):
                        warnings.append(
                            f"One OpenAlex search failed: {type(batch).__name__}"
                        )
                    else:
                        results.extend(batch)

            if not results:
                provider = "duckduckgo"

        if provider != "google":
            tasks = [self._search(query, provider) for query in selected_queries]
            batches = await asyncio.gather(*tasks, return_exceptions=True)
            for batch in batches:
                if isinstance(batch, Exception):
                    warnings.append(f"One search failed: {type(batch).__name__}")
                else:
                    results.extend(batch)

        manual_urls = [str(item) for item in request.source_urls]
        manual_urls.extend(
            re.findall(r"https?://[^\s<>()\"']+", request.source_material)
        )
        for source_url in list(dict.fromkeys(manual_urls))[:10]:
            try:
                results.append(await self._fetch_manual_url(source_url.rstrip(".,;")))
            except Exception as exc:
                warnings.append(
                    f"Could not read {urlparse(source_url).netloc}: {type(exc).__name__}"
                )

        manual_text = re.sub(
            r"https?://[^\s<>()\"']+", "", request.source_material
        ).strip()
        if manual_text:
            results.append(
                SearchResult(
                    title="User-provided source material",
                    url="about:blank#user-source-material",
                    snippet=manual_text[:6000],
                    source_type="User-provided material",
                    credibility="Needs verification",
                )
            )

        deduped: dict[str, SearchResult] = {}
        for result in results:
            normalized = result.url.rstrip("/")
            if normalized not in deduped:
                deduped[normalized] = result
        source_limit = {"Quick Prep": 6, "Standard Prep": 8, "Deep Research": 12}[
            request.research_depth.value
        ]
        limited_results = self._limit_results(list(deduped.values()), source_limit)

        if provider == "google":
            if google_succeeded:
                warnings.append(
                    "No search API key was found. Google browser search, direct page "
                    "content extraction, and OpenAlex academic search were used."
                )
            else:
                warnings.append(
                    "Google requested verification or was unavailable. OpenAlex academic "
                    "search was used without an API key."
                )
        elif provider == "duckduckgo":
            warnings.append(
                "No configured search API was found. DuckDuckGo basic search was used."
            )
        elif provider == "openalex":
            warnings.append(
                "No search API key or browser was found. OpenAlex academic search was used."
            )
        if not limited_results:
            warnings.append(
                "No web evidence was found. Evidence claims must be treated as unverified."
            )
        return limited_results, warnings

    async def fetch_user_urls(
        self, source_material: str
    ) -> tuple[list[SearchResult], list[str]]:
        urls = list(
            dict.fromkeys(
                url.rstrip(".,;")
                for url in re.findall(
                    r"https?://[^\s<>()\"']+", source_material
                )
            )
        )[:10]
        if not urls:
            return [], []
        batches = await asyncio.gather(
            *[self._fetch_manual_url(url) for url in urls],
            return_exceptions=True,
        )
        results: list[SearchResult] = []
        warnings: list[str] = []
        for url, item in zip(urls, batches):
            if isinstance(item, Exception):
                warnings.append(
                    f"Could not read {urlparse(url).netloc}: {type(item).__name__}"
                )
            else:
                results.append(item)
        return results, warnings

    def _select_provider(self) -> str:
        requested = self.settings.search_provider
        available = {
            "tavily": bool(self.settings.tavily_api_key),
            "serper": bool(self.settings.serper_api_key),
            "brave": bool(self.settings.brave_search_api_key),
            "google": async_playwright is not None and bool(self._find_chrome_path()),
            "openalex": True,
            "duckduckgo": True,
        }
        if requested != "auto" and available.get(requested):
            return requested
        for provider in (
            "tavily",
            "serper",
            "brave",
            "google",
            "openalex",
            "duckduckgo",
        ):
            if available[provider]:
                return provider
        return "duckduckgo"

    async def _search(self, query: str, provider: str) -> list[SearchResult]:
        if provider == "tavily":
            return await self._search_tavily(query)
        if provider == "serper":
            return await self._search_serper(query)
        if provider == "brave":
            return await self._search_brave(query)
        if provider == "openalex":
            return await self._search_openalex(query)
        return await self._search_duckduckgo(query)

    async def _search_google_browser(
        self, queries: list[str]
    ) -> list[SearchResult]:
        chrome_path = self._find_chrome_path()
        if async_playwright is None or not chrome_path:
            raise RuntimeError("Playwright or Chrome is unavailable")

        raw_results: list[tuple[str, str, str, Optional[str]]] = []
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                executable_path=chrome_path,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                locale="en-US",
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()
            try:
                for query in queries:
                    site_match = re.search(
                        r"\bsite:([^\s]+)", query, flags=re.IGNORECASE
                    )
                    required_domain = (
                        site_match.group(1).lower().lstrip(".")
                        if site_match
                        else None
                    )
                    url = "https://www.google.com/search?" + urlencode(
                        {
                            "q": query,
                            "hl": "en",
                            "num": self.settings.search_results_per_query,
                            "filter": "1",
                        }
                    )
                    await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=int(self.settings.search_timeout_seconds * 1000),
                    )
                    blocked = await page.evaluate(
                        """
                        () => /captcha|unusual traffic|not a robot/i.test(
                          document.title + " " + document.body.innerText.slice(0, 2000)
                        )
                        """
                    )
                    if blocked:
                        raise RuntimeError("Google requested human verification")
                    page_results = await page.locator("a:has(h3)").evaluate_all(
                        """
                        (links, limit) => links.slice(0, limit).map((link) => {
                          const block = link.parentElement?.parentElement?.parentElement;
                          return {
                            title: link.querySelector("h3")?.innerText?.trim() || "",
                            url: link.href,
                            snippet: (block?.innerText || "").replace(/\\s+/g, " ").trim()
                          };
                        })
                        """,
                        self.settings.search_results_per_query,
                    )
                    for item in page_results:
                        if item.get("title") and item.get("url"):
                            raw_results.append(
                                (
                                    item["title"],
                                    item["url"],
                                    item.get("snippet", "")[:1000],
                                    required_domain,
                                )
                            )
            except PlaywrightTimeoutError as exc:
                raise RuntimeError("Google search timed out") from exc
            finally:
                await browser.close()

        resolved = await asyncio.gather(
            *[self._resolve_google_url(url) for _, url, _, _ in raw_results],
            return_exceptions=True,
        )
        results: list[SearchResult] = []
        for (title, _, snippet, required_domain), final_url in zip(
            raw_results, resolved
        ):
            if isinstance(final_url, Exception) or not final_url:
                continue
            host = urlparse(final_url).netloc.lower().removeprefix("www.")
            if (
                host.endswith("google.com")
                or self._is_blocked_research_domain(host)
                or (
                    required_domain
                    and host != required_domain
                    and not host.endswith(f".{required_domain}")
                )
            ):
                continue
            results.append(self._result(title, final_url, snippet))
        return results

    async def _search_tavily(self, query: str) -> list[SearchResult]:
        payload = {
            "api_key": self.settings.tavily_api_key,
            "query": query,
            "max_results": self.settings.search_results_per_query,
            "search_depth": "advanced",
        }
        data = await self._json_request(
            "POST", "https://api.tavily.com/search", json=payload
        )
        return [
            self._result(item.get("title"), item.get("url"), item.get("content", ""))
            for item in data.get("results", [])
            if item.get("url")
        ]

    async def _search_serper(self, query: str) -> list[SearchResult]:
        data = await self._json_request(
            "POST",
            "https://google.serper.dev/search",
            headers={"X-API-KEY": self.settings.serper_api_key or ""},
            json={"q": query, "num": self.settings.search_results_per_query},
        )
        return [
            self._result(
                item.get("title"),
                item.get("link"),
                item.get("snippet", ""),
                item.get("date"),
            )
            for item in data.get("organic", [])
            if item.get("link")
        ]

    async def _search_brave(self, query: str) -> list[SearchResult]:
        data = await self._json_request(
            "GET",
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": self.settings.brave_search_api_key or "",
            },
            params={"q": query, "count": self.settings.search_results_per_query},
        )
        return [
            self._result(
                item.get("title"),
                item.get("url"),
                item.get("description", ""),
                item.get("age"),
            )
            for item in data.get("web", {}).get("results", [])
            if item.get("url")
        ]

    async def _search_openalex(self, query: str) -> list[SearchResult]:
        cleaned_query = re.sub(r"\bsite:\S+", "", query, flags=re.IGNORECASE).strip()
        data = await self._json_request(
            "GET",
            "https://api.openalex.org/works",
            params={
                "search": cleaned_query,
                "per-page": self.settings.search_results_per_query,
                "select": (
                    "id,title,doi,publication_date,primary_location,"
                    "abstract_inverted_index"
                ),
            },
            headers={"User-Agent": "DebateBuddy/1.0 (educational research)"},
        )
        results: list[SearchResult] = []
        terms = self._meaningful_query_terms(cleaned_query)
        for item in data.get("results", []):
            primary = item.get("primary_location") or {}
            url = item.get("doi") or primary.get("landing_page_url") or item.get("id")
            if not url:
                continue
            abstract = self._restore_openalex_abstract(
                item.get("abstract_inverted_index")
            )
            searchable = f"{item.get('title', '')} {abstract}".lower()
            minimum_matches = min(3, len(terms))
            if minimum_matches and sum(term in searchable for term in terms) < minimum_matches:
                continue
            results.append(
                SearchResult(
                    title=item.get("title") or "Untitled academic work",
                    url=url,
                    snippet=abstract[:6000],
                    published_date=item.get("publication_date"),
                    accessed_at=datetime.now(timezone.utc),
                    source_type="Academic publication",
                    credibility="High",
                )
            )
        return results

    async def _search_duckduckgo(self, query: str) -> list[SearchResult]:
        async with httpx.AsyncClient(
            timeout=self.settings.search_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 DebateBuddy/1.0"},
        ) as client:
            response = await client.get("https://html.duckduckgo.com/html/", params={"q": query})
            response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        results: list[SearchResult] = []
        for item in soup.select(".result")[: self.settings.search_results_per_query]:
            link = item.select_one(".result__a")
            snippet = item.select_one(".result__snippet")
            if not link or not link.get("href"):
                continue
            url = self._unwrap_duckduckgo_url(str(link["href"]))
            results.append(
                self._result(
                    link.get_text(" ", strip=True),
                    url,
                    snippet.get_text(" ", strip=True) if snippet else "",
                )
            )
        return results

    async def _fetch_manual_url(self, url: str) -> SearchResult:
        return await self._fetch_page(url)

    async def _enrich_google_results(
        self, request: GenerateRequest, results: list[SearchResult]
    ) -> list[SearchResult]:
        limit = {"Quick Prep": 6, "Standard Prep": 10, "Deep Research": 16}[
            request.research_depth.value
        ]
        semaphore = asyncio.Semaphore(4)

        async def enrich(result: SearchResult) -> SearchResult:
            async with semaphore:
                try:
                    page = await self._fetch_page(result.url, result.title)
                    if page.snippet:
                        return page
                except Exception:
                    pass
                return result

        return await asyncio.gather(*[enrich(item) for item in results[:limit]])

    async def _fetch_page(
        self, url: str, fallback_title: Optional[str] = None
    ) -> SearchResult:
        await self._assert_public_url(url)
        async with httpx.AsyncClient(
            timeout=self.settings.search_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "DebateBuddy/1.0 educational research tool"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            await self._assert_public_url(str(response.url))
            if len(response.content) > 2_000_000:
                raise ValueError("Page is too large")
            content_type = response.headers.get("content-type", "").lower()
            if "html" not in content_type and "text/" not in content_type:
                raise ValueError("Unsupported page content type")
        soup = BeautifulSoup(response.text, "html.parser")
        title = (
            soup.title.get_text(" ", strip=True)
            if soup.title
            else fallback_title or urlparse(url).netloc
        )
        published_date = self._extract_published_date(soup)
        for node in soup(["script", "style", "nav", "footer"]):
            node.decompose()
        main = soup.select_one("main, article, [role='main']")
        text = " ".join((main or soup).get_text(" ", strip=True).split())[:6000]
        return self._result(title, str(response.url), text, published_date)

    async def _resolve_google_url(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.netloc.lower().removeprefix("www.") != "google.com":
            await self._assert_public_url(url)
            return url

        direct = parse_qs(parsed.query).get("q")
        if parsed.path == "/url" and direct:
            target = direct[0]
            await self._assert_public_url(target)
            return target

        async with httpx.AsyncClient(
            timeout=self.settings.search_timeout_seconds,
            follow_redirects=False,
            headers={"User-Agent": "Mozilla/5.0 DebateBuddy/1.0"},
        ) as client:
            response = await client.get(url)
            if response.is_redirect:
                target = urljoin(url, response.headers["location"])
                await self._assert_public_url(target)
                return target
            response.raise_for_status()
            final_url = str(response.url)
            await self._assert_public_url(final_url)
            return final_url

    async def _json_request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.settings.search_timeout_seconds) as client:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()

    def _result(
        self,
        title: Optional[str],
        url: Optional[str],
        snippet: str,
        published_date: Optional[str] = None,
    ) -> SearchResult:
        final_url = url or ""
        source_type, credibility = self._classify_source(final_url)
        return SearchResult(
            title=title or urlparse(final_url).netloc or "Untitled source",
            url=final_url,
            snippet=" ".join(snippet.split())[:2500],
            published_date=published_date,
            accessed_at=datetime.now(timezone.utc),
            source_type=source_type,
            credibility=credibility,
        )

    @staticmethod
    def _classify_source(url: str) -> tuple[str, str]:
        host = urlparse(url).netloc.lower().removeprefix("www.")
        for domain, source_type in TRUSTED_DOMAINS.items():
            is_trusted_tld = domain in {"gov", "edu"} and host.endswith(f".{domain}")
            is_named_domain = host == domain or host.endswith(f".{domain}")
            if is_trusted_tld or is_named_domain:
                return source_type, "High"
        return "Web source", "Needs verification"

    def _find_chrome_path(self) -> Optional[str]:
        if self.settings.google_chrome_path:
            configured = Path(self.settings.google_chrome_path).expanduser()
            if configured.is_file():
                return str(configured)
        for candidate in DEFAULT_CHROME_PATHS:
            if Path(candidate).is_file():
                return candidate
        return None

    @staticmethod
    def _is_blocked_research_domain(host: str) -> bool:
        return any(
            host == domain or host.endswith(f".{domain}")
            for domain in BLOCKED_RESEARCH_DOMAINS
        )

    @staticmethod
    def _meaningful_query_terms(query: str) -> set[str]:
        ignored = {
            "about",
            "against",
            "benefits",
            "evidence",
            "harms",
            "research",
            "statistics",
            "study",
            "with",
        }
        return {
            word
            for word in re.findall(r"[a-z]{4,}", query.lower())
            if word not in ignored
        }

    @staticmethod
    def _limit_results(
        results: list[SearchResult], limit: int
    ) -> list[SearchResult]:
        academic = [
            item for item in results if item.source_type == "Academic publication"
        ]
        web = [item for item in results if item.source_type != "Academic publication"]
        academic_limit = limit // 2
        selected = [*web[: limit - academic_limit], *academic[:academic_limit]]
        if len(selected) < limit:
            selected_urls = {item.url for item in selected}
            selected.extend(
                item
                for item in results
                if item.url not in selected_urls
            )
        return selected[:limit]

    @staticmethod
    def _extract_published_date(soup: BeautifulSoup) -> Optional[str]:
        selectors = [
            ('meta[property="article:published_time"]', "content"),
            ('meta[name="date"]', "content"),
            ('meta[name="pubdate"]', "content"),
            ('meta[itemprop="datePublished"]', "content"),
            ("time[datetime]", "datetime"),
        ]
        for selector, attribute in selectors:
            node = soup.select_one(selector)
            if node and node.get(attribute):
                return str(node[attribute])[:100]
        return None

    @staticmethod
    def _restore_openalex_abstract(
        inverted_index: Optional[dict[str, list[int]]]
    ) -> str:
        if not inverted_index:
            return ""
        positioned_words = [
            (position, word)
            for word, positions in inverted_index.items()
            for position in positions
        ]
        positioned_words.sort(key=lambda item: item[0])
        return " ".join(word for _, word in positioned_words)

    @staticmethod
    def _unwrap_duckduckgo_url(url: str) -> str:
        if url.startswith("//"):
            url = f"https:{url}"
        parsed = urlparse(url)
        target = parse_qs(parsed.query).get("uddg")
        return unquote(target[0]) if target else url

    @staticmethod
    async def _assert_public_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Only public HTTP(S) URLs are allowed")
        addresses = await asyncio.to_thread(
            socket.getaddrinfo, parsed.hostname, parsed.port or 443
        )
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                raise ValueError("Private network URLs are not allowed")
