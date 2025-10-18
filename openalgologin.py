import re
from playwright.sync_api import Playwright, sync_playwright, expect
import time

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.goto("http://127.0.0.1:5000/auth/login")
    time.sleep(2)
    #page.get_by_role("link", name="Login").click()
    page.get_by_role("textbox", name="Enter your username").click()
    page.get_by_role("textbox", name="Enter your username").fill("cool")
    page.get_by_role("textbox", name="Enter your username").press("Tab")
    page.get_by_role("textbox", name="Enter your password").fill("Demoacc@1")
    page.get_by_role("button", name="Sign in").click()
    time.sleep(5)
    page.get_by_role("button", name="Connect Account").click()
    time.sleep(5)
    page.close()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
