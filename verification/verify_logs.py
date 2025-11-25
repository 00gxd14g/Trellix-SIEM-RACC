from playwright.sync_api import sync_playwright

def verify_logs_page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Capture console logs
        page.on("console", lambda msg: print(f"BROWSER LOG: {msg.text}"))
        page.on("pageerror", lambda err: print(f"BROWSER ERROR: {err}"))

        # Navigate to dashboard first (Vite is on port 3000 as per config)
        print("Navigating to http://localhost:3000...")
        page.goto("http://localhost:3000")

        # Wait a bit for React to hydrate
        page.wait_for_timeout(2000)

        # Take a screenshot of the dashboard to see if "Logs" is visible
        page.screenshot(path="verification/dashboard_debug.png", full_page=True)

        # Wait for the logs link in sidebar and click it
        # Try a more specific selector
        print("Clicking Logs link...")
        page.locator("a[href='/logs']").click()

        # Wait for the logs page to load (look for "Audit Logs" header)
        print("Waiting for 'Audit Logs' text...")
        page.wait_for_selector("text=Audit Logs")

        # Take a screenshot
        page.screenshot(path="verification/logs_page.png", full_page=True)

        browser.close()

if __name__ == "__main__":
    verify_logs_page()
