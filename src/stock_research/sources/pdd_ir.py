from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

from stock_research.sources.http import fetch_bytes, write_bytes, write_json


PDD_IR_HOME = "https://investor.pddholdings.com/"
PDD_IR_NEWS_RELEASES = urljoin(PDD_IR_HOME, "news-releases")


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

    def fetch_news_releases_index(self) -> dict[str, object]:
        data = fetch_bytes(PDD_IR_NEWS_RELEASES, headers={"User-Agent": "stock-research-system/0.1"})
        digest = hashlib.sha256(data).hexdigest()
        path = self.cache_dir / "news_releases" / "index.html"
        write_bytes(path, data)
        links = self.extract_links(data.decode("utf-8", errors="replace"), PDD_IR_NEWS_RELEASES)
        metadata = {
            "url": PDD_IR_NEWS_RELEASES,
            "local_path": str(path),
            "sha256": digest,
            "byte_length": len(data),
            "links": links,
            "financial_results_links": self.filter_financial_results_links(links),
        }
        write_json(path.with_suffix(path.suffix + ".metadata.json"), metadata)
        return metadata

    def fetch_latest_financial_results_release(self) -> dict[str, object] | None:
        index = self.fetch_news_releases_index()
        candidates = index.get("financial_results_links") or []
        if not candidates:
            return None
        return self.fetch_news_release(str(candidates[0]["url"]), link_text=str(candidates[0].get("text") or ""))

    def fetch_news_release(self, url: str, *, link_text: str = "") -> dict[str, object]:
        data = fetch_bytes(url, headers={"User-Agent": "stock-research-system/0.1"})
        digest = hashlib.sha256(data).hexdigest()
        text = data.decode("utf-8", errors="replace")
        slug = self._safe_slug(url)
        path = self.cache_dir / "news_releases" / f"{slug}.html"
        write_bytes(path, data)
        plain = " ".join(re.sub(r"(?s)<[^>]+>", " ", text).split())
        release_date = self._release_date(plain)
        report_date = self._report_date(plain)
        metadata = {
            "document_id": f"pdd_ir:{release_date or 'undated'}:{slug}",
            "source_id": "pdd_investor_relations",
            "source_url": url,
            "archive_url": url,
            "form": "IR",
            "document_type": "pdd_ir:news_release",
            "document_role": "primary",
            "downloaded_file": path.name,
            "local_path": str(path),
            "sha256": digest,
            "byte_length": len(data),
            "filing_date": release_date,
            "report_date": report_date,
            "title": link_text or self._title(plain),
            "research_category": "KEEP_CORE_INTERIM_EARNINGS",
            "research_decision": "Keep",
            "research_reason": "Official PDD investor-relations unaudited financial-results news release.",
        }
        write_json(path.with_suffix(path.suffix + ".metadata.json"), metadata)
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

    @staticmethod
    def filter_financial_results_links(links: list[dict[str, str]]) -> list[dict[str, str]]:
        candidates = []
        seen = set()
        for link in links:
            url = link.get("url", "")
            haystack = f"{link.get('text', '')} {url}".lower()
            if "news-release-details" not in url:
                continue
            if "financial" not in haystack or "results" not in haystack:
                continue
            if url in seen:
                continue
            seen.add(url)
            candidates.append(link)
        return candidates

    @staticmethod
    def _safe_slug(url: str) -> str:
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", slug).strip("_") or "news_release"

    @staticmethod
    def _release_date(text: str) -> str | None:
        match = re.search(r"\b([A-Z][a-z]+)\s+(\d{1,2}),\s+(20\d{2})\b", text)
        if not match:
            return None
        month_name, day, year = match.groups()
        month = {
            "January": "01",
            "February": "02",
            "March": "03",
            "April": "04",
            "May": "05",
            "June": "06",
            "July": "07",
            "August": "08",
            "September": "09",
            "October": "10",
            "November": "11",
            "December": "12",
        }.get(month_name)
        if month is None:
            return None
        return f"{year}-{month}-{int(day):02d}"

    @staticmethod
    def _report_date(text: str) -> str | None:
        match = re.search(r"(?:quarter ended|three months ended)\s+([A-Z][a-z]+)\s+(\d{1,2}),\s+(20\d{2})", text)
        if not match:
            return None
        month_name, day, year = match.groups()
        month = {
            "January": "01",
            "February": "02",
            "March": "03",
            "April": "04",
            "May": "05",
            "June": "06",
            "July": "07",
            "August": "08",
            "September": "09",
            "October": "10",
            "November": "11",
            "December": "12",
        }.get(month_name)
        if month is None:
            return None
        return f"{year}-{month}-{int(day):02d}"

    @staticmethod
    def _title(text: str) -> str:
        match = re.search(r"(PDD Holdings Announces .*?Financial Results)", text)
        return match.group(1) if match else "PDD Holdings financial results news release"
