import time
import pickle
import os
import sys
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, ElementClickInterceptedException, TimeoutException

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

    # Find 'From Station' input and ensure it's enabled and clickable (robust)
    from_selector = "#dest_from"
    max_attempts = 3
    from_filled = False
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"Attempt {attempt}: locating From Station input ({from_selector})...")
            from_station = WebDriverWait(driver, 12).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, from_selector))
            )
            # Scroll into view
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", from_station)
            time.sleep(0.2)
            try:
                from_station.click()
            except ElementClickInterceptedException as e:
                print(f"⚠ Click intercepted on From Station, attempting JS click: {e}")
                driver.execute_script("arguments[0].click();", from_station)
            except Exception as e:
                print(f"⚠ Click failed on From Station (non-intercept): {e}, attempting JS click as fallback")
                driver.execute_script("arguments[0].click();", from_station)

            # Clear the input (use JS to ensure readonly inputs are reset)
            try:
                driver.execute_script("arguments[0].value = ''", from_station)
            except Exception:
                pass
            time.sleep(0.2)
            from_station.send_keys("Dhaka")
            print("✔ 'Dhaka' typed into From Station")
            time.sleep(2)
            from_filled = True
            break
        except StaleElementReferenceException:
            print(f"⚠ Stale element while locating From Station on attempt {attempt}, retrying...")
            time.sleep(0.4)
        except Exception as e:
            print(f"❌ Error interacting with From Station on attempt {attempt}: {e}")
            time.sleep(0.6)
    if not from_filled:
        print("❌ Failed to fill From Station after multiple attempts")

    # Select 'Dhaka' from dropdown
    dhaka_option = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.XPATH, "//li[@class='ui-menu-item']/a[text()='Dhaka']"))
    )
    dhaka_option.click()
    print("✔ 'Dhaka' selected as From Station.")

    # Select 'To Station' as 'Cox Bazar' in the same way
    try:
        print("🔎 Waiting for 'To Station' input (#dest_to)...")
        to_station = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#dest_to"))
        )
        print("✔ 'To Station' input found, clicking and typing...")
        to_station.click()
        to_station.clear()
        to_station.send_keys("Cox's Bazar")
        time.sleep(2)  # Wait for dropdown to appear

        print("🔎 Waiting for 'Cox's Bazar' dropdown option...")
        cox_option = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//li[@class='ui-menu-item']/a[text()=\"Cox's Bazar\"]"))
        )
        cox_option.click()
        print("✔ 'Cox's Bazar' selected as To Station.")
    except Exception as e:
        print(f"❌ Error selecting 'To Station' or 'Cox's Bazar': {e}")

    # Print all input fields and clickable elements to help find correct calendar trigger
    print("--- All input fields on page ---")
    for inp in driver.find_elements(By.TAG_NAME, "input"):
        print(f"Input: id={inp.get_attribute('id')}, name={inp.get_attribute('name')}, type={inp.get_attribute('type')}, class={inp.get_attribute('class')}, value={inp.get_attribute('value')}")
    print("--- End input fields ---")

    print("--- All buttons and clickable elements on page ---")
    for btn in driver.find_elements(By.TAG_NAME, "button"):
        print(f"Button: id={btn.get_attribute('id')}, name={btn.get_attribute('name')}, class={btn.get_attribute('class')}, text={btn.text}")
    for a in driver.find_elements(By.TAG_NAME, "a"):
        if a.get_attribute('onclick') or a.get_attribute('role') == 'button':
            print(f"Clickable <a>: id={a.get_attribute('id')}, class={a.get_attribute('class')}, text={a.text}")
    print("--- End clickable elements ---")
    try:
        # Click the date input (#doj) using an in-page click to avoid stale element refs
        target_day = 23  # desired date
        print("🔎 Opening calendar by clicking #doj (in-page JS click)...")
        try:
            driver.execute_script("var e=document.querySelector('#doj'); if(e){e.click(); return true;} return false;")
            print("✔ Clicked #doj to open calendar")
        except Exception as e:
            print("⚠ Could not click #doj via JS, falling back to selenium click:", e)
            date_input = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#doj"))
            )
            date_input.click()

        # Wait for calendar container to appear
        try:
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#ui-datepicker-div"))
            )
            print("✔ Calendar container is present")
        except Exception as e:
            print("❌ Calendar did not appear:", e)

        # Allow overriding target_day via CLI arg only (no env vars)
        if len(sys.argv) > 1:
            try:
                arg_day = int(sys.argv[1])
                target_day = arg_day
            except Exception:
                pass

        # Try to set the date input value directly using visible month/year from calendar
        try:
            js_get_month_year = (
                "var root=document.getElementById('ui-datepicker-div');"
                "if(!root) return null;"
                "var m = root.querySelector('.ui-datepicker-month');"
                "var y = root.querySelector('.ui-datepicker-year');"
                "if(!m||!y) return null;"
                "return [m.textContent.trim(), y.textContent.trim()];"
            )
            my = driver.execute_script(js_get_month_year)
            if my and isinstance(my, list) and len(my) == 2:
                month_name, year_str = my[0], my[1]
                months = {"January":1,"February":2,"March":3,"April":4,"May":5,"June":6,"July":7,"August":8,"September":9,"October":10,"November":11,"December":12}
                month_num = months.get(month_name, None)
                if month_num:
                    target_date_value = f"{int(target_day):02d}/{month_num:02d}/{int(year_str)}"
                else:
                    target_date_value = f"{int(target_day):02d}/01/{int(year_str)}"
            else:
                target_date_value = f"{int(target_day):02d}/11/2025"

            # First, try jQuery UI datepicker API if available: use .datepicker('setDate')
            js_try_jquery = (
                "var el=document.querySelector('#doj');"
                "if(!el) return 'noel';"
                "if(window.jQuery && jQuery.fn && jQuery.fn.datepicker){"
                "  try{"
                "    var d = new Date(arguments[2], arguments[1]-1, arguments[0]);"
                "    jQuery(el).datepicker('setDate', d);"
                "    jQuery(el).trigger('change');"
                "    return 'jquery-ok';"
                "  }catch(e){ return 'jquery-err:'+e; }"
                "}"
                "return 'no-jquery';"
            )
            # arguments: day, month_num, year
            try_jq = driver.execute_script(js_try_jquery, int(target_day), month_num if 'month_num' in locals() and month_num else 1, int(year_str) if 'year_str' in locals() else 2025)
            if isinstance(try_jq, str) and try_jq.startswith('jquery-ok'):
                print("✔ Date set via jQuery datepicker API")
                ok = True
            else:
                # Fallback: set value and dispatch a variety of events to satisfy different frameworks
                js_set_date = (
                    "var sel='#doj'; var val=arguments[0]; var el=document.querySelector(sel);"
                    "if(!el) return false;"
                    "try{ el.focus(); }catch(e){}"
                    "el.value = val;"
                    "try{ el.dispatchEvent(new Event('input', {bubbles:true})); }catch(e){}"
                    "try{ el.dispatchEvent(new Event('change', {bubbles:true})); }catch(e){}"
                    "try{ el.dispatchEvent(new KeyboardEvent('keyup', {key:'', bubbles:true})); }catch(e){}"
                    "try{ el.dispatchEvent(new Event('blur', {bubbles:true})); }catch(e){}"
                    "try{ el.dispatchEvent(new Event('focusout', {bubbles:true})); }catch(e){}"
                    "return true;"
                )
                ok = driver.execute_script(js_set_date, target_date_value)
                print("JS set date result:", ok, "value set to", target_date_value)

            # After setting the date, optionally click SEARCH TRAINS
            try:
                search_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'SEARCH TRAINS')]") )
                )
                try:
                    search_btn.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", search_btn)
                print("✔ Clicked SEARCH TRAINS after setting date")
            except Exception:
                print("⚠ SEARCH TRAINS button not found or not clickable immediately after setting date")
        except Exception as e:
            print("❌ Error while setting date via JS:", e)
            # Fallback: try clicking the date link inside the calendar
            try:
                day_xpath = f"//div[@id='ui-datepicker-div']//a[text()='{int(target_day)}']"
                day_el = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, day_xpath))
                )
                try:
                    day_el.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", day_el)
                print(f"✔ Clicked calendar day {target_day} via fallback")
            except Exception as e2:
                print("❌ Fallback calendar click failed:", e2)
                try:
                    calendar_table = driver.find_element(By.CLASS_NAME, "ui-datepicker-calendar")
                    print(calendar_table.get_attribute("outerHTML"))
                except Exception as e3:
                    print("❌ Could not get calendar HTML for debugging:", e3)
    except Exception as e:
        print(f"❌ Error during calendar date selection: {e}")

    # Select Class from dropdown (e.g., 'AC_B')
    class_select = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "#choose_class"))
    )
    class_select.click()
    class_option = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//select[@id='choose_class']/option[@value='AC_B']"))
    )
    class_option.click()
    print("✔ Class selected: AC_B")
except Exception as e:
    print("❌ Error during ticket booking automation:", e)

input("Press Enter to exit...")
