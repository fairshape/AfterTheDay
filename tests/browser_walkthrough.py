"""Run against an already-started fictional demo. Install Playwright separately for browser QA."""
import argparse
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright


def check_day_deletion_in_frame(page, base, day_id):
    # Telegram-style embedding can disable native confirm dialogs.
    page.route("**/deletion-test-host", lambda route: route.fulfill(
        content_type="text/html",
        body=f'<iframe sandbox="allow-scripts allow-same-origin" src="/?day={day_id}"></iframe>',
    ))
    page.goto(base + "/deletion-test-host")
    frame = page.frame_locator("iframe")
    frame.get_by_text("Изменить сведения о записи", exact=True).click()
    delete = frame.get_by_role("button", name="Удалить запись", exact=True)
    delete.click()
    frame.get_by_role("button", name="Отмена", exact=True).click()
    assert page.request.get(f"{base}/api/days/{day_id}").status == 200
    delete.click()
    frame.get_by_role("button", name="Да, удалить", exact=True).click()
    expect(frame.locator(".exhibition")).to_be_visible()
    assert page.request.get(f"{base}/api/days/{day_id}").status == 404
    assert all(day["id"] != day_id for day in page.request.get(base + "/api/days").json())


def walkthrough(base, executable, snapshots, disposable_demo=False):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=executable)
        try:
            page = browser.new_page(viewport={"width": 390, "height": 844})
            if not page.request.get(base + "/api/mode").json()["demo"]:
                raise RuntimeError("This walkthrough requires DEMO_MODE=true.")
            errors = []
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            page.goto(base)
            expect(page.locator(".shelf-card[aria-current] img")).to_be_visible()
            first = page.locator(".shelf-title").inner_text()
            page.get_by_role("button", name="Следующее воспоминание").click()
            expect(page.locator(".shelf-counter")).to_have_text("2 / 6")
            assert page.locator(".shelf-title").inner_text() != first
            selected = page.locator(".shelf-card[aria-current]").get_attribute("href")
            page.locator(".shelf-card[aria-current]").click()
            expect(page.locator(".folder")).to_be_visible()
            assert page.url.endswith(selected)
            page.go_back()
            expect(page.locator(".shelf-counter")).to_have_text("2 / 6")
            if disposable_demo:
                page.locator(".shelf-card[aria-current]").click()
                page.get_by_role("button", name="Пережить день", exact=True).click()
                scene = page.locator("#theater")
                scrub = scene.locator(".scene-scrub")
                expect(scrub).to_be_visible()
                scene.get_by_role("button", name="Пауза", exact=True).click()
                scrub.fill("11")
                expect(scene.locator(".scene-caption")).to_have_text("Фонарь дрожал в луже")
                expect(scene.locator(".scene-caption")).to_be_visible()
                scrub.fill(str(float(scrub.get_attribute("max")) - .3))
                expect(scene.locator(".scene-caption")).to_be_hidden()
                page.go_back()
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
            if disposable_demo:
                archived = page.request.get(base + "/api/days").json()
                check_day_deletion_in_frame(page, base, archived[-1]["id"])
            assert not errors, errors
        finally:
            browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", default="http://127.0.0.1:8000")
    parser.add_argument("--chromium", help="Path to Chromium if using a system installation")
    parser.add_argument("--screenshots", type=Path)
    parser.add_argument("--disposable-demo", action="store_true", help="Enable deletion QA on a freshly seeded temporary demo database")
    args = parser.parse_args()
    if urlsplit(args.origin).hostname not in {"localhost", "127.0.0.1", "::1"}:
        parser.error("Use a local demo origin.")
    walkthrough(args.origin.rstrip("/"), args.chromium, args.screenshots, args.disposable_demo)
    print("Browser walkthrough passed.")
