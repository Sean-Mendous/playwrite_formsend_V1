import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
import base64
from playwright.sync_api import sync_playwright

def open_browser(url, p):
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    # ページが完全に読み込まれるまで待機
    page.goto(url, wait_until="load")
    time.sleep(3)
    return browser, page

def get_encoded_image(page):
    image_bytes = page.screenshot(timeout=5000)
    encoded_image = base64.b64encode(image_bytes).decode("utf-8")
    return encoded_image
    