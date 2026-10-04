import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.config import Settings
from app.models import RulesStatus


RULES_SOURCES = [
    (
        "Introduction to World Schools Debate",
        "https://docs.google.com/document/d/1MmbIZP0YkLiER6aABtOEWEMyHi-OFAOFQ3T8HFmKF_k/export?format=txt",
    ),
    (
        "WSD Starter Pack",
        "https://docs.google.com/document/d/1_L3qp5AQuTb9V_AknNcZ7Ooj_CMYZyvf3PAOWULebIU/export?format=txt",
    ),
    (
        "Tournament reference",
        "https://www.tabroom.com/index/tourn/main.mhtml?tourn_id=40334",
    ),
]


class DebateRulesSkill:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._content = ""
        self._status = RulesStatus(
            loaded=False,
            source="Not loaded",
            character_count=0,
        )
        self._load_lock = asyncio.Lock()

    @property
    def content(self) -> str:
        return self._content

    @property
    def status(self) -> RulesStatus:
        return self._status

    async def load(self, force_refresh: bool = False) -> RulesStatus:
        async with self._load_lock:
            return await self._load(force_refresh)

    async def _load(self, force_refresh: bool) -> RulesStatus:
        local = self._read_local_notes()
        if local:
            self._set_content(local, "Local rules_notes.md")
            return self._status

        if not force_refresh:
            cached = self._read_cache()
            if cached:
                self._set_content(cached, "Online source cache")
                return self._status

        warnings: list[str] = []
        sections: list[str] = []
        async with httpx.AsyncClient(
            timeout=self.settings.search_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "DebateBuddy/1.0 educational research tool"},
        ) as client:
            for title, url in RULES_SOURCES:
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    text = self._extract_text(response.text, response.headers.get("content-type", ""))
                    if text:
                        sections.append(f"# {title}\n\n{text[:30000]}")
                except httpx.HTTPError as exc:
                    warnings.append(f"Could not load {title}: {type(exc).__name__}")

        if sections:
            content = "\n\n".join(sections)
            self._write_cache(content)
            self._set_content(content, "Online reference materials", warnings)
        else:
            self._set_content(self._built_in_guidance(), "Built-in WSD guidance", warnings)
        return self._status

    def context_excerpt(self, max_chars: int = 12000) -> str:
        return self._content[:max_chars]

    def _read_local_notes(self) -> str:
        path = self.settings.rules_notes_path
        if not path.exists():
            return ""
        text = path.read_text(encoding="utf-8").strip()
        meaningful = [
            line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("<!--")
        ]
        if not meaningful or all(line.rstrip().endswith("-->") for line in meaningful):
            return ""
        return text

    def _read_cache(self) -> Optional[str]:
        path = self.settings.rules_cache_path
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            fetched_at = datetime.fromisoformat(data["fetched_at"])
            if datetime.now(timezone.utc) - fetched_at > timedelta(
                hours=self.settings.rules_cache_hours
            ):
                return None
            return str(data["content"])
        except (ValueError, KeyError, TypeError):
            return None

    def _write_cache(self, content: str) -> None:
        path = self.settings.rules_cache_path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "content": content,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def _set_content(
        self, content: str, source: str, warnings: Optional[list[str]] = None
    ) -> None:
        self._content = content
        self._status = RulesStatus(
            loaded=bool(content),
            source=source,
            character_count=len(content),
            last_loaded_at=datetime.utcnow(),
            warnings=warnings or [],
        )

    @staticmethod
    def _extract_text(body: str, content_type: str) -> str:
        if "html" not in content_type.lower() and "<html" not in body[:200].lower():
            return body.strip()
        soup = BeautifulSoup(body, "html.parser")
        for node in soup(["script", "style", "nav", "footer"]):
            node.decompose()
        return " ".join(soup.get_text(" ", strip=True).split())

    @staticmethod
    def _built_in_guidance() -> str:
        return """
World Schools Debate uses teams with distinct speaker roles. The first speaker defines the
motion, states the team position, gives the team split, and presents the opening arguments.
The second speaker answers the other side and develops the case. The third speaker focuses
on rebuttal and the main clashes, with little or no new substantive material. A reply or
summary speech compares both teams and explains why one side wins; local tournament rules
decide who may give it and its exact timing. Students should follow the tournament's stated
rules when they differ.

Good preparation asks what each side must prove, builds two or three clear arguments, checks
credible evidence, and predicts rebuttal. POIs and cross-examination questions should be
short, relevant, and designed to reveal an assumption or contradiction. Students can learn
from recorded rounds by lowering playback speed, turning on captions, pausing to take notes,
and keeping a vocabulary list.
""".strip()
