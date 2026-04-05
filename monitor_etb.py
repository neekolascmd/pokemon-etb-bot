from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError, async_playwright

DEFAULT_INTERVAL_SECONDS = 300
DEFAULT_TIMEOUT_MS = 45_000
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class CheckResult:
    url: str
    retailer: str
    title: str
    available: bool
    evidence: str
    error: str | None = None


def now_stamp() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def normalize(text: str) -> str:
    return " ".join(text.lower().split())


def domain_for(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def retailer_for(url: str) -> str:
    domain = domain_for(url)
    if "pokemoncenter.com" in domain:
        return "pokemon_center"
    if "target.com" in domain:
        return "target"
    if "walmart.com" in domain:
        return "walmart"
    if "amazon." in domain:
        return "amazon"
    return "generic"


async def body_text(page: Page) -> str:
    try:
        return await page.locator("body").inner_text(timeout=15_000)
    except Exception:
        return ""


async def title_text(page: Page) -> str:
    try:
        return await page.title()
    except Exception:
        return ""


async def first_visible_text(page: Page, selectors: Iterable[str]) -> str:
    for selector in selectors:
        locator = page.locator(selector)
        try:
            if await locator.count() and await locator.first.is_visible():
                text = normalize(await locator.first.inner_text())
                if text:
                    return text
        except Exception:
            continue
    return ""


async def inspect_url(page: Page, url: str) -> CheckResult:
    retailer = retailer_for(url)
    title = ""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT_MS)
        try:
            await page.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            pass
        await page.wait_for_timeout(1500)

        title = await title_text(page)
        text = normalize(await body_text(page))

        available = False
        evidence = ""

        if retailer == "pokemon_center":
            positive = ["add to cart", "add to bag"]
            negative = ["sold out", "out of stock", "currently unavailable", "unavailable"]
            available = any(p in text for p in positive) and not any(n in text for n in negative)
            evidence = "add to cart text present" if available else "stock text not found"
        elif retailer == "target":
            positive = ["add to cart", "ship it"]
            negative = ["out of stock", "not sold", "sold out", "currently unavailable"]
            available = any(p in text for p in positive) and not any(n in text for n in negative)
            evidence = "target purchase button text present" if available else "target stock text not found"
        elif retailer == "walmart":
            positive = ["add to cart", "pickup today", "delivery"]
            negative = ["out of stock", "sold out", "currently unavailable"]
            available = any(p in text for p in positive) and not any(n in text for n in negative)
            evidence = "walmart purchase text present" if available else "walmart stock text not found"
        elif retailer == "amazon":
            add_to_cart_visible = False
            try:
                locator = page.locator("#add-to-cart-button")
                add_to_cart_visible = await locator.count() > 0 and await locator.first.is_visible()
            except Exception:
                add_to_cart_visible = False
            negative = ["currently unavailable", "temporarily out of stock", "unavailable"]
            available = add_to_cart_visible and not any(n in text for n in negative)
            if available:
                evidence = "amazon add-to-cart button visible"
            else:
                evidence = await first_visible_text(
                    page,
                    [
                        "#availability span",
                        "#outOfStock",
                        "#availability",
                    ],
                ) or "amazon stock text not found"
        else:
            positive = ["add to cart", "add to bag", "buy now"]
            negative = ["out of stock", "sold out", "currently unavailable"]
            available = any(p in text for p in positive) and not any(n in text for n in negative)
            evidence = "generic purchase text present" if available else "generic stock text not found"

        return CheckResult(url=url, retailer=retailer, title=title, available=available, evidence=evidence)
    except PlaywrightTimeoutError as exc:
        return CheckResult(url=url, retailer=retailer, title=title, available=False, evidence="timeout", error=str(exc))
    except Exception as exc:
        return CheckResult(url=url, retailer=retailer, title=title, available=False, evidence="error", error=str(exc))


def format_result(result: CheckResult) -> str:
    status = "IN STOCK" if result.available else "out of stock"
    parts = [f"[{now_stamp()}]", result.retailer, status, result.url]
    if result.title:
        parts.append(f'title="{result.title.strip()}"')
    if result.evidence:
        parts.append(f'evidence="{result.evidence}"')
    if result.error:
        parts.append(f'error="{result.error}"')
    return " | ".join(parts)


def load_urls(args: argparse.Namespace) -> list[str]:
    urls: list[str] = []
    if args.urls_file:
        for line in Path(args.urls_file).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    urls.extend(args.urls)
    deduped: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped


async def run_once(urls: list[str], headless: bool) -> int:
    any_in_stock = False
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=DEFAULT_USER_AGENT,
            viewport={"width": 1440, "height": 1200},
            locale="en-US",
        )
        try:
            for url in urls:
                page = await context.new_page()
                try:
                    result = await inspect_url(page, url)
                    print(format_result(result))
                    if result.available:
                        any_in_stock = True
                finally:
                    await page.close()
        finally:
            await context.close()
            await browser.close()
    return 2 if any_in_stock else 0


async def run(args: argparse.Namespace) -> int:
    urls = load_urls(args)
    if not urls:
        raise SystemExit("Provide at least one product URL or --urls-file.")

    if args.once:
        return await run_once(urls, headless=not args.headed)

    while True:
        code = await run_once(urls, headless=not args.headed)
        if code == 2:
            return code
        await asyncio.sleep(args.interval)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor Pokémon ETB product pages for stock changes.")
    parser.add_argument("urls", nargs="*", help="Product page URLs to monitor")
    parser.add_argument("--urls-file", help="Text file with one product URL per line")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_SECONDS, help="Seconds between checks when looping")
    parser.add_argument("--once", action="store_true", help="Run one check and exit")
    parser.add_argument("--headed", action="store_true", help="Run with a visible browser window")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parse_args())))
