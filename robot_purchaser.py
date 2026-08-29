"""
Playwright Automated Robot Purchase Script for AgentTrust.
Simulates an automated AI purchasing bot completing a purchase on the storefront.
Captured signals (Headless/Automated User-Agent, fast click timing) will be evaluated by the classifier.
"""
import time
import random
from playwright.sync_api import sync_playwright

STOREFRONT_URL = "http://127.0.0.1:8000/store"

def run_robot_purchase():
    print("=========================================================")
    print("        PLAYWRIGHT ROBOT AUTOMATED PURCHASER             ")
    print("=========================================================")
    print(f"-> Launching automated browser and navigating to {STOREFRONT_URL}...")

    with sync_playwright() as p:
        # Launch Chromium (headed mode so you can watch the bot act)
        browser = p.chromium.launch(
            headless=False,
            slow_mo=500  # Slight delay between actions so you can visually follow
        )
        
        # Create browser context with automated user agent signature
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/128.0.0.0 Safari/537.36 (PlaywrightBot/1.0)"
        )
        page = context.new_page()

        # Step 1: Open Storefront
        page.goto(STOREFRONT_URL)
        page.wait_for_load_state("networkidle")
        print("-> Storefront loaded.")

        # Step 2: Automated delay (0.5 to 1.2 seconds — distinctly faster than human)
        bot_delay = round(random.uniform(0.5, 1.2), 2)
        print(f"-> Bot simulated processing delay: {bot_delay} seconds...")
        time.sleep(bot_delay)

        # Step 3: Locate and click 'Buy Now' on Product #2 (Mechanical Gaming Keyboard RGB)
        print("-> Locating product and clicking 'Buy Now'...")
        buy_button = page.locator("button.buy-btn").nth(1)  # Product 2
        buy_button.click()

        # Step 4: Wait for Razorpay redirect
        print("-> Waiting for Razorpay Checkout page to load...")
        page.wait_for_url(lambda u: "payment-link" in u or "rzp.io" in u or "razorpay.com" in u, timeout=20000)
        print(f"-> Arrived at Razorpay Checkout URL: {page.url}")

        # Step 5: Fill Razorpay Card Details
        print("-> Automating Razorpay test card entry...")
        time.sleep(2)

        # Handle Card payment selection if present
        try:
            card_option = page.locator("text=Card").first
            if card_option.is_visible(timeout=3000):
                card_option.click()
        except Exception:
            pass

        # Fill Card Number
        card_num_input = page.locator("input[name='cardnumber'], input[placeholder*='Card Number'], input[autocomplete='cc-number']").first
        if card_num_input.is_visible(timeout=5000):
            card_num_input.fill("4111111111111111")
        
        # Fill Expiry
        expiry_input = page.locator("input[name='exp'], input[placeholder*='MM / YY'], input[autocomplete='cc-exp']").first
        if expiry_input.is_visible(timeout=3000):
            expiry_input.fill("1230")

        # Fill CVV
        cvv_input = page.locator("input[name='cvv'], input[placeholder*='CVV'], input[autocomplete='cc-csc']").first
        if cvv_input.is_visible(timeout=3000):
            cvv_input.fill("123")

        # Fill Cardholder Name
        name_input = page.locator("input[name='name'], input[placeholder*='Name']").first
        if name_input.is_visible(timeout=3000):
            name_input.fill("Robot Test Buyer")

        # Click Continue / Pay
        pay_btn = page.locator("button:has-text('Pay'), button:has-text('Continue')").first
        if pay_btn.is_visible(timeout=3000):
            pay_btn.click()

        # Handle Test OTP simulation success button if presented
        try:
            time.sleep(3)
            success_btn = page.locator("button:has-text('Success'), iframe >> button:has-text('Success')").first
            if success_btn.is_visible(timeout=5000):
                success_btn.click()
                print("-> Clicked Razorpay OTP 'Success' button.")
        except Exception:
            pass

        print("\n-> Playwright Robot Purchase flow completed successfully!")
        time.sleep(3)
        browser.close()

if __name__ == "__main__":
    run_robot_purchase()
