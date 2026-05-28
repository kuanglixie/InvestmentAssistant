from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

from stock_research.sources.http import fetch_bytes, write_bytes, write_json


PDD_IR_HOME = "https://investor.pddholdings.com/"


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._current_href: str | None = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            attrs_dict = dict(attrs)
            self._current_href = attrs_dict.get("href")
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._current_href:
            text = " ".join("".join(self._text_parts).split())
            self.links.append({"href": self._current_href, "text": text})
            self._current_href = None
            self._text_parts = []


class PddIrClient:
    def __init__(self, *, cache_dir: str | Path = "data/raw/pdd_ir") -> None:
        self.cache_dir = Path(cache_dir)

    def fetch_home(self) -> dict[str, object]:
        data = fetch_bytes(PDD_IR_HOME, headers={"User-Agent": "stock-research-system/0.1"})
        digest = hashlib.sha256(data).hexdigest()
        path = self.cache_dir / "home.html"
        write_bytes(path, data)
        links = self.extract_links(data.decode("utf-8", errors="replace"), PDD_IR_HOME)
        metadata = {
            "url": PDD_IR_HOME,
            "local_path": str(path),
            "sha256": digest,
            "byte_length": len(data),
            "links": links,
            "annual_report_links": self.filter_report_links(links),
        }
        write_json(self.cache_dir / "home.metadata.json", metadata)
        return metadata

    @staticmethod
    def extract_links(html: str, base_url: str) -> list[dict[str, str]]:
        parser = LinkParser()
        parser.feed(html)
        normalized = []
        for link in parser.links:
            href = link.get("href")
            if not href:
                continue
            normalized.append(
                {
                    "url": urljoin(base_url, href),
                    "text": link.get("text", ""),
                }
            )
        return normalized

    @staticmethod
    def filter_report_links(links: list[dict[str, str]]) -> list[dict[str, str]]:
        candidates = []
        for link in links:
            haystack = f"{link.get('text', '')} {link.get('url', '')}".lower()
            if re.search(r"annual|20-f|financial|results|quarter|earnings|report", haystack):
                candidates.append(link)
        return candidates

