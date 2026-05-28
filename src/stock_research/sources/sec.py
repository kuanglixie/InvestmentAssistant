from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from stock_research.sources.document_policy import classify_sec_document_text
from stock_research.sources.http import fetch_bytes, fetch_json, sec_user_agent, write_bytes, write_json


SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik_padded}.json"
SEC_SUBMISSIONS_FILE_URL = "https://data.sec.gov/submissions/{name}"
SEC_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"
SEC_FILING_INDEX_URL = SEC_ARCHIVES_BASE + "/{cik}/{accession_no_dashes}/index.json"


FINANCIAL_RESULT_KEYWORDS = (
    "results",
    "financial",
    "quarter",
    "quarterly",
    "annual",
    "earnings",
    "interim",
    "unaudited",
    "revenues",
    "net income",
    "cash flow",
)


class SecClient:
    def __init__(self, *, cache_dir: str | Path = "data/raw/sec", user_agent: str | None = None) -> None:
        self.cache_dir = Path(cache_dir)
        self.user_agent = user_agent or sec_user_agent()

    @property
    def headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov",
        }

    @property
    def data_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov",
        }

    def fetch_ticker_map(self) -> list[dict[str, Any]]:
        cached_path = self.cache_dir / "company_tickers.json"
        if cached_path.exists():
            return json.loads(cached_path.read_text(encoding="utf-8"))
        raw = fetch_json(SEC_TICKERS_URL, headers=self.headers)
        records = list(raw.values())
        write_json(cached_path, records)
        return records

    def resolve_ticker(self, ticker: str) -> dict[str, Any] | None:
        records = self.fetch_ticker_map()
        ticker_upper = ticker.upper()
        for record in records:
            if str(record.get("ticker", "")).upper() == ticker_upper:
                cik = int(record["cik_str"])
                resolved = {
                    "ticker": record["ticker"],
                    "title": record["title"],
                    "cik": cik,
                    "cik_padded": f"{cik:010d}",
                }
                write_json(self.cache_dir / ticker_upper / "identity.json", resolved)
                return resolved
        return None

    def fetch_submissions(self, cik_padded: str) -> dict[str, Any]:
        url = SEC_SUBMISSIONS_URL.format(cik_padded=cik_padded)
        company_dir = self.cache_dir / cik_padded
        submissions_path = company_dir / "submissions.json"
        if submissions_path.exists():
            submissions = json.loads(submissions_path.read_text(encoding="utf-8"))
        else:
            submissions = fetch_json(url, headers=self.data_headers)
            write_json(submissions_path, submissions)

        filings = submissions.get("filings", {})
        older_files = filings.get("files", [])
        older_payloads = []
        for file_record in older_files:
            name = file_record.get("name")
            if not name:
                continue
            older_path = company_dir / name
            if older_path.exists():
                payload = json.loads(older_path.read_text(encoding="utf-8"))
            else:
                payload = fetch_json(SEC_SUBMISSIONS_FILE_URL.format(name=name), headers=self.data_headers)
                write_json(older_path, payload)
            older_payloads.append(payload)
        submissions["_older_filings_payloads"] = older_payloads
        return submissions

    def filing_index(self, submissions: dict[str, Any]) -> list[dict[str, Any]]:
        recent = submissions.get("filings", {}).get("recent", {})
        filings = self._records_from_columns(recent)
        for payload in submissions.get("_older_filings_payloads", []):
            filings.extend(self._records_from_columns(payload))

        cik = str(submissions.get("cik", "")).lstrip("0")
        cik_padded = str(submissions.get("cik", "")).zfill(10)
        normalized = []
        for record in filings:
            accession = record.get("accessionNumber")
            primary_doc = record.get("primaryDocument")
            if not accession or not primary_doc:
                continue
            accession_no_dashes = accession.replace("-", "")
            archive_url = f"{SEC_ARCHIVES_BASE}/{cik}/{accession_no_dashes}/{primary_doc}"
            normalized.append(
                {
                    "accession_number": accession,
                    "filing_date": record.get("filingDate"),
                    "report_date": record.get("reportDate"),
                    "form": record.get("form"),
                    "primary_document": primary_doc,
                    "primary_doc_description": record.get("primaryDocDescription"),
                    "archive_url": archive_url,
                    "cik": cik,
                    "cik_padded": cik_padded,
                    "is_financial_report": self.is_financial_report(record),
                    "download_priority": self.download_priority(record),
                }
            )
        return normalized

    def download_filing(self, filing: dict[str, Any]) -> dict[str, Any]:
        cached = self.cached_downloaded_documents(filing)
        for document in cached:
            if document.get("downloaded_file") == filing.get("primary_document"):
                return document
        url = filing["archive_url"]
        data = fetch_bytes(url, headers=self.headers)
        return self.save_filing_bytes(filing, filing["primary_document"], data, role="primary")

    def filing_directory_index(self, filing: dict[str, Any]) -> dict[str, Any]:
        url = SEC_FILING_INDEX_URL.format(
            cik=filing["cik"],
            accession_no_dashes=filing["accession_number"].replace("-", ""),
        )
        accession = self._safe_path_part(str(filing["accession_number"]))
        path = self.cache_dir / filing["cik_padded"] / "directories" / f"{accession}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        data = fetch_json(url, headers=self.headers)
        write_json(path, data)
        return data

    def download_6k_if_financial(self, filing: dict[str, Any]) -> list[dict[str, Any]]:
        if str(filing.get("form", "")).upper() not in {"6-K", "6-K/A"}:
            return []
        cached = self.cached_downloaded_documents(filing)
        if cached:
            return cached

        directory = self.filing_directory_index(filing)
        candidate_names = self._candidate_6k_file_names(filing, directory)
        fetched: list[tuple[str, bytes]] = []
        combined_text_parts = []
        for name in candidate_names:
            url = self._archive_file_url(filing, name)
            data = fetch_bytes(url, headers=self.headers)
            fetched.append((name, data))
            combined_text_parts.append(data[:1_000_000].decode("utf-8", errors="ignore").lower())

        combined_text = "\n".join(combined_text_parts)
        if not self._looks_like_financial_results(combined_text):
            return []

        saved = []
        for index, (name, data) in enumerate(fetched):
            role = "primary" if name == filing.get("primary_document") else f"exhibit_{index}"
            classification = classify_sec_document_text(
                filename=name,
                form=str(filing.get("form") or ""),
                role=role,
                text=data[:1_000_000].decode("utf-8", errors="ignore"),
            )
            if classification["category"] == "DROP_SEC_INDEX_OR_HEADERS":
                continue
            saved.append(self.save_filing_bytes(filing, name, data, role=role))
        return saved

    def save_filing_bytes(
        self,
        filing: dict[str, Any],
        filename: str,
        data: bytes,
        *,
        role: str,
    ) -> dict[str, Any]:
        digest = hashlib.sha256(data).hexdigest()
        form = self._safe_path_part(str(filing.get("form", "unknown")))
        accession = self._safe_path_part(str(filing["accession_number"]))
        safe_filename = self._safe_path_part(filename)
        path = self.cache_dir / filing["cik_padded"] / "documents" / form / accession / safe_filename
        write_bytes(path, data)
        metadata = {
            **filing,
            "downloaded_file": filename,
            "document_role": role,
            **{
                f"research_{key}": value
                for key, value in classify_sec_document_text(
                    filename=filename,
                    form=str(filing.get("form") or ""),
                    role=role,
                    text=data[:1_000_000].decode("utf-8", errors="ignore"),
                ).items()
            },
            "local_path": str(path),
            "sha256": digest,
            "byte_length": len(data),
            "archive_url": self._archive_file_url(filing, filename),
        }
        write_json(path.with_suffix(path.suffix + ".metadata.json"), metadata)
        return metadata

    def cached_downloaded_documents(self, filing: dict[str, Any]) -> list[dict[str, Any]]:
        form = self._safe_path_part(str(filing.get("form", "unknown")))
        accession = self._safe_path_part(str(filing["accession_number"]))
        directory = self.cache_dir / filing["cik_padded"] / "documents" / form / accession
        if not directory.exists():
            return []
        documents = []
        for metadata_path in sorted(directory.glob("*.metadata.json")):
            documents.append(json.loads(metadata_path.read_text(encoding="utf-8")))
        return documents

    def discover_company_filings(self, ticker: str) -> dict[str, Any]:
        identity = self.resolve_ticker(ticker)
        if identity is None:
            raise ValueError(f"SEC ticker not found: {ticker}")
        submissions = self.fetch_submissions(identity["cik_padded"])
        filings = self.filing_index(submissions)
        company_dir = self.cache_dir / identity["cik_padded"]
        write_json(company_dir / "filing_index.json", filings)
        return {
            "identity": identity,
            "submissions": submissions,
            "filings": filings,
        }

    @staticmethod
    def _records_from_columns(columns: dict[str, list[Any]]) -> list[dict[str, Any]]:
        if not columns:
            return []
        keys = list(columns.keys())
        length = max((len(columns.get(key, [])) for key in keys), default=0)
        records = []
        for index in range(length):
            records.append(
                {
                    key: columns.get(key, [None] * length)[index]
                    if index < len(columns.get(key, []))
                    else None
                    for key in keys
                }
            )
        return records

    @staticmethod
    def is_financial_report(record: dict[str, Any]) -> bool:
        form = str(record.get("form") or "").upper()
        description = str(record.get("primaryDocDescription") or "").lower()
        primary_doc = str(record.get("primaryDocument") or "").lower()
        if form in {"20-F", "20-F/A", "10-K", "10-Q"}:
            return True
        if form in {"6-K", "6-K/A"}:
            haystack = f"{description} {primary_doc}"
            return any(keyword in haystack for keyword in FINANCIAL_RESULT_KEYWORDS)
        return False

    @staticmethod
    def download_priority(record: dict[str, Any]) -> int:
        form = str(record.get("form") or "").upper()
        if form in {"20-F", "10-K"}:
            return 1
        if form in {"20-F/A", "10-K/A"}:
            return 2
        if form in {"6-K", "6-K/A"} and SecClient.is_financial_report(record):
            return 3
        if SecClient.is_financial_report(record):
            return 4
        return 99

    @staticmethod
    def _candidate_6k_file_names(filing: dict[str, Any], directory: dict[str, Any]) -> list[str]:
        names: list[str] = []
        primary = filing.get("primary_document")
        if primary:
            names.append(primary)
        for item in directory.get("directory", {}).get("item", []):
            name = item.get("name")
            if not name or name in names:
                continue
            lower = name.lower()
            if "index" in lower or "headers" in lower:
                continue
            if not lower.endswith((".htm", ".html")):
                continue
            if lower.startswith("r") and lower[1:].split(".", 1)[0].isdigit():
                continue
            if lower in {"report.css", "filingsummary.xml"}:
                continue
            if "ex" in lower or "exhibit" in lower or "press" in lower or "release" in lower:
                names.append(name)
        return names

    @staticmethod
    def _looks_like_financial_results(text: str) -> bool:
        return any(keyword in text for keyword in FINANCIAL_RESULT_KEYWORDS)

    @staticmethod
    def _archive_file_url(filing: dict[str, Any], filename: str) -> str:
        accession_no_dashes = filing["accession_number"].replace("-", "")
        return f"{SEC_ARCHIVES_BASE}/{filing['cik']}/{accession_no_dashes}/{filename}"

    @staticmethod
    def _safe_path_part(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "unknown"
