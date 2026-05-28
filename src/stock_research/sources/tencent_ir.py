from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from stock_research.sources.http import fetch_bytes, write_bytes, write_json


TENCENT_FINANCIAL_REPORTS_URL = "https://www.tencent.com/en-us/investors/financial-reports.html"
TENCENT_IR_HOME = "https://www.tencent.com/en-us/investors.html"


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._current_href: str | None = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._current_href = dict(attrs).get("href")
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._current_href:
            self.links.append(
                {
                    "href": self._current_href,
                    "text": " ".join("".join(self._text_parts).split()),
                }
            )
            self._current_href = None
            self._text_parts = []


class TencentIrClient:
    def __init__(self, *, cache_dir: str | Path = "data/raw/tencent_ir") -> None:
        self.cache_dir = Path(cache_dir)

    def fetch_financial_reports_index(self) -> dict[str, Any]:
        data = fetch_bytes(
            TENCENT_FINANCIAL_REPORTS_URL,
            headers={"User-Agent": "stock-research-system/0.1"},
        )
        path = self.cache_dir / "financial_reports.html"
        write_bytes(path, data)
        html = data.decode("utf-8", errors="replace")
        links = self.extract_links(html, TENCENT_FINANCIAL_REPORTS_URL)
        reports = self.filter_financial_report_links(links)
        metadata = {
            "url": TENCENT_FINANCIAL_REPORTS_URL,
            "local_path": str(path),
            "sha256": hashlib.sha256(data).hexdigest(),
            "byte_length": len(data),
            "financial_reports": reports,
        }
        write_json(self.cache_dir / "financial_reports.metadata.json", metadata)
        return metadata

    def download_financial_reports(self) -> dict[str, Any]:
        index = self.fetch_financial_reports_index()
        downloaded = []
        errors = []
        for report in index.get("financial_reports", []):
            try:
                downloaded.append(self.download_report(report))
            except Exception as exc:  # noqa: BLE001 - recorded for audit.
                errors.append({"url": report.get("url"), "title": report.get("title"), "error": str(exc)})
        return {**index, "downloaded_documents": downloaded, "download_errors": errors}

    def download_report(self, report: dict[str, Any]) -> dict[str, Any]:
        url = str(report["url"])
        year = int(report["fiscal_year"])
        report_kind = str(report["report_kind"])
        data = fetch_bytes(
            url,
            headers={"User-Agent": "stock-research-system/0.1", "Accept": "application/pdf,*/*"},
            timeout=45,
        )
        filename = f"{year}_{report_kind}.pdf"
        path = self.cache_dir / "financial_reports" / str(year) / filename
        write_bytes(path, data)
        return {
            "document_id": f"tencent_ir:{year}:{report_kind}",
            "source_id": "tencent_investor_relations",
            "document_type": "annual_report_pdf" if report_kind == "annual" else "interim_report_pdf",
            "form": "annual_report" if report_kind == "annual" else "interim_report",
            "filing_date": report.get("published_date"),
            "report_date": f"{year}-12-31" if report_kind == "annual" else f"{year}-06-30",
            "fiscal_year": year,
            "report_kind": report_kind,
            "title": report.get("title"),
            "source_url": url,
            "local_path": str(path),
            "downloaded_file": filename,
            "checksum": hashlib.sha256(data).hexdigest(),
            "byte_length": len(data),
            "status": "downloaded",
            "research_category": "KEEP_CORE_ANNUAL_REPORT"
            if report_kind == "annual"
            else "KEEP_CORE_INTERIM_EARNINGS",
            "research_decision": "Keep",
            "research_reason": "Official Tencent investor-relations financial report.",
        }

    @staticmethod
    def extract_links(raw_html: str, base_url: str) -> list[dict[str, str]]:
        parser = LinkParser()
        parser.feed(raw_html)
        return [
            {"url": urljoin(base_url, link["href"]), "text": link.get("text", "")}
            for link in parser.links
            if link.get("href")
        ]

    @staticmethod
    def filter_financial_report_links(links: list[dict[str, str]]) -> list[dict[str, Any]]:
        reports = []
        seen_urls = set()
        for link in links:
            url = link.get("url", "")
            text = link.get("text", "")
            if not url.lower().endswith(".pdf") or url in seen_urls:
                continue
            match = re.search(r"(20\d{2})\s+(Annual|Interim)\s+Report", text, flags=re.IGNORECASE)
            if not match:
                continue
            seen_urls.add(url)
            year = int(match.group(1))
            kind = match.group(2).lower()
            reports.append(
                {
                    "title": f"{year} {kind.title()} Report",
                    "fiscal_year": year,
                    "report_kind": kind,
                    "url": url,
                    "published_date": _published_date_from_url(url),
                }
            )
        return sorted(reports, key=lambda report: (report["fiscal_year"], report["report_kind"]))


def _published_date_from_url(url: str) -> str | None:
    match = re.search(r"/uploads/(\d{4})/(\d{2})/(\d{2})/", url)
    if not match:
        return None
    year, month, day = match.groups()
    return f"{year}-{month}-{day}"
