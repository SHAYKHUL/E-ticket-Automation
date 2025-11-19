import time
import pickle
import os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --------------------------------------------------------------
# CONFIGURATION
# --------------------------------------------------------------
LOGIN_URL = "https://eticket.railway.gov.bd/login"

MOBILE = "01334042089"      # replace with your mobile number
PASSWORD = "A17041994"  # replace with your password

# --------------------------------------------------------------
# LAUNCH BROWSER
# --------------------------------------------------------------
options = uc.ChromeOptions()
options.add_argument("--no-first-run")
options.add_argument("--no-default-browser-check")
options.add_argument("--disable-blink-features=AutomationControlled")


COOKIES_FILE = "cookies.pkl"

driver = uc.Chrome(options=options)
driver.get(LOGIN_URL)

# Use a shorter wait for faster Cloudflare check
wait = WebDriverWait(driver, 10)

# --------------------------------------------------------------
# LOAD COOKIES IF AVAILABLE
# --------------------------------------------------------------
def load_cookies(driver, cookies_file):
    if os.path.exists(cookies_file):
        with open(cookies_file, "rb") as f:
            cookies = pickle.load(f)
            for cookie in cookies:
                driver.add_cookie(cookie)
        driver.refresh()

def save_cookies(driver, cookies_file):
    with open(cookies_file, "wb") as f:
        pickle.dump(driver.get_cookies(), f)

# Try to load cookies and refresh
logged_in = False
try:
    load_cookies(driver, COOKIES_FILE)
    time.sleep(2)
    # Check if already logged in (by checking for a known element after login)
    # You may need to update this selector to something only visible when logged in
    if driver.current_url != LOGIN_URL:
        logged_in = True
except Exception as e:
    print("Could not load cookies:", e)


# --------------------------------------------------------------
# FILL MOBILE NUMBER
# --------------------------------------------------------------

if not logged_in:
    mobile_field = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#mobile_number"))
    )
    mobile_field.click()
    mobile_field.send_keys(MOBILE)
    time.sleep(1)

# --------------------------------------------------------------
# FILL PASSWORD
# --------------------------------------------------------------
    password_field = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#password"))
    )
    password_field.click()
    password_field.send_keys(PASSWORD)
    time.sleep(1)

# --------------------------------------------------------------
# WAIT FOR CLOUDFLARE TURNSTILE SUCCESS
# --------------------------------------------------------------
    print("⏳ Waiting for Cloudflare verification...")
    try:
        # Wait for the success text element to appear
        success_elem = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#success-text"))
        )
        print("Cloudflare message:", success_elem.text)
        # Optionally, check for 'Success' in the text
        if "Success" in success_elem.text:
            print("✔ Cloudflare verification completed!")
        else:
            print("⚠ Cloudflare message found, but not 'Success'. Text:", success_elem.text)
    except Exception as e:
        print("❌ Could not verify Cloudflare success message.", str(e))
        print("Page source for debugging:")
        print(driver.page_source)

# --------------------------------------------------------------
# CLICK LOGIN BUTTON
# --------------------------------------------------------------
    login_btn = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, ".login-form-submit-btn"))
    )
    login_btn.click()

    print("✔ Login submitted successfully!")

    # Save cookies after login
    time.sleep(3)
    save_cookies(driver, COOKIES_FILE)
    print("✔ Cookies saved for future sessions.")

# --------------------------------------------------------------
# OPTIONAL: Keep browser open for review
# --------------------------------------------------------------

# --------------------------------------------------------------
# TICKET BOOKING: SELECT 'FROM STATION' AS DHAKA
# --------------------------------------------------------------
try:
    # Wait for landing page after login
    WebDriverWait(driver, 15).until(
        EC.url_to_be("https://eticket.railway.gov.bd/")
    )
    print("✔ Landed on main page after login.")


    # Click 'I AGREE' button using full selector if present
    agree_selector = "body > app-root > app-home > app-disclaimer-modal > div > div > div.disclaimer-bottom-sheet-text-wrapper.ng-tns-c49-8 > div.disclaimer-bottom-sheet-action-btn.ng-tns-c49-8 > button"
    modal_selector = ".disclaimer-bottom-sheet"
    try:
        # Wait for modal to be visible
        WebDriverWait(driver, 3).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, modal_selector))
        )
        agree_btn = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, agree_selector))
        )
        # Scroll button into view before clicking
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", agree_btn)
        try:
            agree_btn.click()
            print("✔ 'I AGREE' button clicked.")
        except Exception as click_err:
            print("⚠ Click intercepted, retrying...")
            time.sleep(1)
            driver.execute_script("arguments[0].click();", agree_btn)
            print("✔ 'I AGREE' button clicked via JS.")
        time.sleep(1)
    except Exception:
        print("'I AGREE' button not found, already clicked, or modal already gone.")

    # Wait for the disclaimer modal to disappear
    try:
        WebDriverWait(driver, 12).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, modal_selector))
        )
        print("✔ Disclaimer modal disappeared.")
    except Exception:
        print("Disclaimer modal already gone or not found.")

    # Find 'From Station' input and ensure it's enabled and clickable
    from_station = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "#dest_from"))
    )
    from_station.click()
    from_station.clear()
    from_station.send_keys("Dhaka")
    time.sleep(2)  # Wait for dropdown to appear

    # Select 'Dhaka' from dropdown
    dhaka_option = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.XPATH, "//li[@class='ui-menu-item']/a[text()='Dhaka']"))
    )
    dhaka_option.click()
    print("✔ 'Dhaka' selected as From Station.")
except Exception as e:
    print("❌ Error during ticket booking automation:", e)

input("Press Enter to exit...")
