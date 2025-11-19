import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc

# ---------------- CONFIG ----------------
MOBILE = "01334042089"       # Your mobile number
PASSWORD = "A17041994"      # Your password
FROM_CITY = "Dhaka"
TO_CITY = "Cox's Bazar"
DOJ = "29-Nov-2025"
SEAT_CLASS = "S_CHAIR"
TARGET_TRAIN = "PARJOTAK EXPRESS (816)"  # User-defined train name

LOGIN_URL = "https://eticket.railway.gov.bd/login"
SEARCH_URL = f"https://eticket.railway.gov.bd/booking/train/search?fromcity={FROM_CITY}&tocity={TO_CITY}&doj={DOJ}&class={SEAT_CLASS}"

# ---------------- BROWSER SETUP ----------------
options = uc.ChromeOptions()
options.add_argument("--no-first-run")
options.add_argument("--no-default-browser-check")
options.add_argument("--disable-blink-features=AutomationControlled")

driver = uc.Chrome(options=options)
wait = WebDriverWait(driver, 15)

# ---------------- LOGIN ----------------
driver.get(LOGIN_URL)
time.sleep(2)
driver.delete_all_cookies()

try:
    mobile_field = wait.until(EC.presence_of_element_located((By.ID, "mobile_number")))
    mobile_field.clear()
    mobile_field.send_keys(MOBILE)

    password_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
    password_field.clear()
    password_field.send_keys(PASSWORD)

    login_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".login-form-submit-btn")))
    driver.execute_script("arguments[0].click();", login_btn)

    # Wait for successful login: check URL change or dashboard element
    wait.until(EC.url_contains("/"))
    print("✔ Login successful")
except Exception as e:
    print("❌ Login failed:", e)
    driver.quit()
    exit()

# ---------------- DISCLAIMER ACCEPT ----------------
try:
    agree_selector = "body > app-root > app-home > app-disclaimer-modal button"
    modal_selector = "app-disclaimer-modal"
    agree_btn = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, agree_selector))
    )
    driver.execute_script("arguments[0].click();", agree_btn)
    WebDriverWait(driver, 5).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, modal_selector)))
    print("✔ Disclaimer accepted")
except TimeoutException:
    print("⚠ No disclaimer modal found, skipping...")

# ---------------- DIRECT TRAIN SEARCH ----------------
driver.get(SEARCH_URL)
time.sleep(3)  # wait for trains to render

# ---------------- FETCH TRAIN ROWS ----------------
train_rows = driver.find_elements(By.CSS_SELECTOR, "app-single-trip .single-trip-wrapper")
if not train_rows:
    print("❌ No trains found")
    driver.quit()
    exit()

print(f"✔ Found {len(train_rows)} trains")

# ---------------- SELECT TARGET TRAIN ----------------
target_row = None
for row in train_rows:
    try:
        train_name = row.find_element(By.CSS_SELECTOR, ".trip-left-info h2").text.strip().upper()
        print("Train found:", train_name)
        if TARGET_TRAIN.upper() in train_name:
            target_row = row
            break
    except NoSuchElementException:
        continue

if not target_row:
    print(f"❌ Target train '{TARGET_TRAIN}' not found")
    driver.quit()
    exit()

# ---------------- SELECT SEAT CLASS ----------------
seat_rows = target_row.find_elements(By.CSS_SELECTOR, ".seat-available-wrap")
selected_seat = None
for seat in seat_rows:
    try:
        seat_name = seat.find_element(By.CSS_SELECTOR, ".seat-class-name").text.strip()
        if SEAT_CLASS.upper() in seat_name.upper():
            selected_seat = seat
            break
    except NoSuchElementException:
        continue

if not selected_seat:
    print(f"❌ Seat class '{SEAT_CLASS}' not found in train '{TARGET_TRAIN}'")
    driver.quit()
    exit()

# ---------------- CLICK BOOK NOW ----------------
try:
    book_btn = selected_seat.find_element(By.CSS_SELECTOR, ".book-now-btn")
    driver.execute_script("arguments[0].click();", book_btn)
    print(f"✔ 'BOOK NOW' clicked for {TARGET_TRAIN} ({SEAT_CLASS})")
    time.sleep(2)  # wait for booking page to load
except Exception as e:
    print("❌ Could not click BOOK NOW:", e)
    driver.quit()
    exit()

# ---------------- SELECT COACH ----------------
try:
    coach_dropdown = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "select-bogie"))
    )
    select = Select(coach_dropdown)
    options = select.options
    selected = False
    for option in options:
        text = option.text.strip()
        if "0 Seat(s)" not in text:
            select.select_by_visible_text(text)
            print(f"✔ Selected coach: {text}")
            selected = True
            break
    if not selected:
        print("❌ No coach with available seats found")
        driver.quit()
        exit()
except Exception as e:
    print("❌ Could not select coach:", e)
    driver.quit()
    exit()

# ---------------- END ----------------
print("✅ Automation completed. Proceed with booking manually if needed.")
input("Press Enter to exit...")
driver.quit()
