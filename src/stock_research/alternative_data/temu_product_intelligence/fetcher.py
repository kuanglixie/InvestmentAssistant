"""Playwright-backed page fetcher with fixture support."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

from .models import CrawlerSettings, ProductConfig, RawFetchResult
from .rate_limiter import RateLimiter
from .retry_policy import RetryPolicy


class TemuPageFetcher:
    def __init__(self, settings: CrawlerSettings, artifact_dir: Path, fixture_dir: Path | None = None) -> None:
        self.settings = settings
        self.artifact_dir = artifact_dir
        self.fixture_dir = fixture_dir
        self.rate_limiter = RateLimiter(settings.min_delay_seconds)
        self.retry = RetryPolicy(settings.max_retries)
        self._playwright = None
        self._browser = None
        self._context = None

    def __enter__(self) -> "TemuPageFetcher":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._context is not None:
            self._context.close()
            self._context = None
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    def fetch(self, product: ProductConfig) -> RawFetchResult:
        if product.url.startswith("fixture://"):
            return self._fetch_fixture(product)

        self.rate_limiter.wait()
        try:
            return self.retry.run(lambda: self._fetch_live(product))
        except Exception as exc:
            return RawFetchResult(
                tracking_id=product.tracking_id,
                url=product.url,
                fetched_at=datetime.now(timezone.utc),
                fetch_success=False,
                fetch_error=str(exc),
            )

    def _fetch_fixture(self, product: ProductConfig) -> RawFetchResult:
        if self.fixture_dir is None:
            raise ValueError("fixture_dir is required for fixture:// URLs")
        fixture_name = product.url.removeprefix("fixture://")
        fixture_path = self.fixture_dir / fixture_name
        html = fixture_path.read_text(encoding="utf-8")
        return self._store_html(product, product.url, html, status_code=200)

    def _ensure_context(self):
        if self._context is not None:
            return self._context
        try:
            from playwright.sync_api import sync_playwright
        except ModuleNotFoundError:  # pragma: no cover - depends on local install.
            return None

        self._playwright = sync_playwright().start()
        launch_kwargs = {"headless": self.settings.headless}
        if self.settings.chrome_executable_path and Path(self.settings.chrome_executable_path).exists():
            launch_kwargs["executable_path"] = self.settings.chrome_executable_path
        self._browser = self._playwright.chromium.launch(**launch_kwargs)
        self._context = self._browser.new_context(
            user_agent=self.settings.user_agent,
            viewport={"width": 1440, "height": 1000},
            locale="en-US",
            timezone_id="America/Los_Angeles",
        )
        return self._context

    def _fetch_live(self, product: ProductConfig) -> RawFetchResult:
        context = self._ensure_context()
        if context is None:
            return self._fetch_live_with_node(product)
        page = context.new_page()
        try:
            response = page.goto(product.url, wait_until=self.settings.wait_until, timeout=self.settings.timeout_ms)
            if self.settings.post_load_wait_ms:
                page.wait_for_timeout(self.settings.post_load_wait_ms)
            self._close_popups(page)
            self._scroll_page(page)
            html = page.content()
            status_code = response.status if response is not None else None
            return self._store_html(product, page.url, html, status_code=status_code)
        finally:
            page.close()

    def _close_popups(self, page) -> None:
        for selector in ('[aria-label="close"]', '[aria-label="Close"]', 'text=No thanks'):
            try:
                locator = page.locator(selector).first()
                if locator.count():
                    locator.click(timeout=1_500, force=True)
                    page.wait_for_timeout(500)
            except Exception:
                continue

    def _scroll_page(self, page) -> None:
        for _ in range(max(0, self.settings.scroll_steps)):
            try:
                page.evaluate("window.scrollBy(0, Math.max(window.innerHeight * 0.85, 700))")
                if self.settings.scroll_wait_ms:
                    page.wait_for_timeout(self.settings.scroll_wait_ms)
                self._close_popups(page)
            except Exception:
                break

    def _fetch_live_with_node(self, product: ProductConfig) -> RawFetchResult:
        node = self.settings.node_executable_path
        node_modules = self.settings.node_modules_path
        chrome = self.settings.chrome_executable_path
        if not node or not Path(node).exists():
            raise RuntimeError("Python Playwright is missing and node_executable_path is not available.")
        if not node_modules or not Path(node_modules).exists():
            raise RuntimeError("Python Playwright is missing and node_modules_path is not available.")
        if not chrome or not Path(chrome).exists():
            raise RuntimeError("Python Playwright is missing and chrome_executable_path is not available.")

        script = """
const { chromium } = require('playwright');
const payload = JSON.parse(process.argv[2]);
async function closePopups(page) {
  for (const selector of ['[aria-label="close"]', '[aria-label="Close"]', 'text=No thanks']) {
    const locator = page.locator(selector).first();
    if (await locator.count()) {
      try {
        await locator.click({ timeout: 1500, force: true });
        await page.waitForTimeout(500);
      } catch (_) {}
    }
  }
}
async function scrollPage(page, steps, waitMs) {
  for (let i = 0; i < Math.max(0, steps || 0); i++) {
    try {
      await page.evaluate(() => window.scrollBy(0, Math.max(window.innerHeight * 0.85, 700)));
      if (waitMs) {
        await page.waitForTimeout(waitMs);
      }
      await closePopups(page);
    } catch (_) {
      break;
    }
  }
}
(async () => {
  const browser = await chromium.launch({
    headless: payload.headless,
    executablePath: payload.chromeExecutablePath
  });
  const context = await browser.newContext({
    userAgent: payload.userAgent,
    viewport: { width: 1440, height: 1000 },
    locale: 'en-US',
    timezoneId: 'America/Los_Angeles'
  });
  const page = await context.newPage();
  let statusCode = null;
  try {
    const response = await page.goto(payload.url, {
      waitUntil: payload.waitUntil,
      timeout: payload.timeoutMs
    });
    statusCode = response ? response.status() : null;
    if (payload.postLoadWaitMs) {
      await page.waitForTimeout(payload.postLoadWaitMs);
    }
    await closePopups(page);
    await scrollPage(page, payload.scrollSteps, payload.scrollWaitMs);
    const html = await page.content();
    const result = { ok: true, statusCode, finalUrl: page.url(), html };
    console.log(JSON.stringify(result));
  } finally {
    await browser.close();
  }
})().catch(err => {
  console.log(JSON.stringify({ ok: false, error: err && (err.stack || err.message) || String(err) }));
  process.exit(0);
});
"""
        payload = {
            "url": product.url,
            "headless": self.settings.headless,
            "chromeExecutablePath": chrome,
            "userAgent": self.settings.user_agent,
            "waitUntil": self.settings.wait_until,
            "timeoutMs": self.settings.timeout_ms,
            "postLoadWaitMs": self.settings.post_load_wait_ms,
            "scrollSteps": self.settings.scroll_steps,
            "scrollWaitMs": self.settings.scroll_wait_ms,
        }
        env = dict(os.environ)
        env["NODE_PATH"] = node_modules
        with NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as temp:
            temp.write(script)
            script_path = temp.name
        try:
            completed = subprocess.run(
                [node, script_path, json.dumps(payload)],
                check=False,
                capture_output=True,
                text=True,
                timeout=(self.settings.timeout_ms / 1000) + 30,
                env=env,
            )
        finally:
            Path(script_path).unlink(missing_ok=True)

        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "Node Playwright failed.")
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        if not lines:
            raise RuntimeError("Node Playwright returned no output.")
        result = json.loads(lines[-1])
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "Node Playwright failed.")
        return self._store_html(product, result.get("finalUrl") or product.url, result.get("html") or "", result.get("statusCode"))

    def _store_html(self, product: ProductConfig, final_url: str, html: str, status_code: int | None) -> RawFetchResult:
        fetched_at = datetime.now(timezone.utc)
        digest = hashlib.sha256(html.encode("utf-8")).hexdigest()
        raw_dir = self.artifact_dir / "raw_pages" / product.tracking_id
        raw_dir.mkdir(parents=True, exist_ok=True)
        html_path = raw_dir / f"{fetched_at.strftime('%Y%m%dT%H%M%SZ')}-{digest[:10]}.html"
        html_path.write_text(html, encoding="utf-8")
        return RawFetchResult(
            tracking_id=product.tracking_id,
            url=product.url,
            fetched_at=fetched_at,
            status_code=status_code,
            final_url=final_url,
            html_path=str(html_path),
            html_sha256=digest,
            html=html,
            fetch_success=True,
        )
