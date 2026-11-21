"""Run against an already-started fictional demo. Install Playwright separately for browser QA."""
import argparse
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright


def walkthrough(base, executable, snapshots):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=executable)
        try:
            page = browser.new_page(viewport={"width": 390, "height": 844})
            if not page.request.get(base + "/api/mode").json()["demo"]:
                raise RuntimeError("This walkthrough requires DEMO_MODE=true.")
            errors = []
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            page.goto(base)
            expect(page.locator(".feature-photo img")).to_be_visible()
            if snapshots:
                snapshots.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=snapshots / "home.png", animations="disabled")
            page.get_by_role("link", name="Архив эмоций", exact=True).click()
            cards = page.locator(".archive-print")
            for index in range(3):
                cards.nth(index).get_by_role("button").click()
            page.get_by_role("button", name="В монтажную", exact=True).click()
            expect(page.locator(".timeline-row")).to_have_count(3)
            page.get_by_label("Название фильма").fill("Три главы")
            page.get_by_role("button", name="Сохранить фильм").click()
            page.get_by_role("button", name="▶ Смотреть фильм").click()
            seek = page.get_by_label("Позиция в фильме")
            for _ in range(50):
                if float(seek.input_value()) > .2:
                    break
                page.wait_for_timeout(100)
            assert float(seek.input_value()) > .2
            page.get_by_role("button", name="Пауза", exact=True).click()
            at = seek.input_value()
            page.wait_for_timeout(200)
            assert seek.input_value() == at
            if snapshots:
                page.screenshot(path=snapshots / "life-replay.png")
            page.get_by_role("button", name="Закрыть ×").click()
            page.reload()
            expect(page.get_by_role("heading", name="Три главы")).to_be_visible()
            page.goto(base + "/?view=studio")
            page.locator(".studio-entry").first.get_by_role("link").click()
            editor = page.locator(".montage-editor")
            expect(editor).to_have_attribute("open", "")
            editor.get_by_label("Движение камеры").select_option("still")
            editor.get_by_label("Длительность, с").fill("12")
            editor.locator("button[type=submit]").click()
            editor.get_by_role("button", name="Сохранить монтаж").click()
            page.get_by_role("button", name="Пережить день", exact=True).click()
            expect(page.locator("#theater .scene-scrub")).to_be_visible()
            assert not errors, errors
        finally:
            browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", default="http://127.0.0.1:8000")
    parser.add_argument("--chromium", help="Path to Chromium if using a system installation")
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    if urlsplit(args.origin).hostname not in {"localhost", "127.0.0.1", "::1"}:
        parser.error("Use a local demo origin.")
    walkthrough(args.origin.rstrip("/"), args.chromium, args.screenshots)
    print("Browser walkthrough passed.")
