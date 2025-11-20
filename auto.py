import json
import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

# ---------------- LOAD CONFIG ----------------
with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

MOBILE = cfg["MOBILE"]
PASSWORD = cfg["PASSWORD"]
FROM_CITY = cfg["FROM_CITY"]
TO_CITY = cfg["TO_CITY"]
DOJ = cfg["DOJ"]
TARGET_TRAIN = cfg["TARGET_TRAIN"]
SEAT_CLASS = cfg["SEAT_CLASS"]
SEATS_TO_SELECT = cfg["SEATS_TO_SELECT"]
PASSENGERS = cfg["PASSENGERS"]  # Only Passenger 2–4
RETRY_COUNT = cfg.get("RETRY_COUNT", 3)
RETRY_DELAY = cfg.get("RETRY_DELAY", 5)

LOGIN_URL = "https://eticket.railway.gov.bd/login"
SEARCH_URL = f"https://eticket.railway.gov.bd/booking/train/search?fromcity={FROM_CITY}&tocity={TO_CITY}&doj={DOJ}&class={SEAT_CLASS}"

# ---------------- BROWSER SETUP ----------------
options = uc.ChromeOptions()
options.add_argument("--no-first-run")
options.add_argument("--no-default-browser-check")
options.add_argument("--disable-blink-features=AutomationControlled")

# Workaround: make Chrome.__del__ safe to avoid unhandled WinError during GC
_orig_chrome_del = getattr(uc.Chrome, "__del__", None)
def _safe_chrome_del(self):
    try:
        if _orig_chrome_del:
            _orig_chrome_del(self)
    except Exception:
        # Silently ignore cleanup errors (e.g. WinError 6)
        pass

uc.Chrome.__del__ = _safe_chrome_del

driver = uc.Chrome(options=options)
wait = WebDriverWait(driver, 15)

def safe_quit():
    try:
        driver.quit()
    except:
        pass

# ---------------- LOGIN ----------------
driver.get(LOGIN_URL)
time.sleep(2)
driver.delete_all_cookies()

try:
    wait.until(EC.presence_of_element_located((By.ID, "mobile_number"))).send_keys(MOBILE)
    wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys(PASSWORD)
    login_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".login-form-submit-btn")))
    driver.execute_script("arguments[0].click();", login_btn)
    time.sleep(3)
    print("✔ Login successful")
except Exception as e:
    print("❌ Login failed:", e)
    safe_quit()
    exit()

# ---------------- DISCLAIMER ----------------
try:
    agree = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "app-disclaimer-modal button"))
    )
    driver.execute_script("arguments[0].click();", agree)
    WebDriverWait(driver, 5).until(
        EC.invisibility_of_element_located((By.CSS_SELECTOR, "app-disclaimer-modal"))
    )
    print("✔ Disclaimer accepted")
except:
    print("⚠ No disclaimer popup")

# ---------------- DIRECT SEARCH ----------------
driver.get(SEARCH_URL)
time.sleep(3)

# ---------------- PARSE TRAINS ----------------
train_rows = driver.find_elements(By.CSS_SELECTOR, "app-single-trip .single-trip-wrapper")
if not train_rows:
    print("❌ No trains found")
    safe_quit()
    exit()

print(f"✔ Found {len(train_rows)} trains")

target_row = None
for row in train_rows:
    try:
        t_name = row.find_element(By.CSS_SELECTOR, ".trip-left-info h2").text.strip().upper()
        if TARGET_TRAIN.upper() in t_name:
            target_row = row
            break
    except:
        continue

if not target_row:
    print("❌ Train not found:", TARGET_TRAIN)
    safe_quit()
    exit()

# ---------------- SELECT SEAT CLASS ----------------
seat_rows = target_row.find_elements(By.CSS_SELECTOR, ".seat-available-wrap")
selected_seat = None
max_seats = 0

for seat in seat_rows:
    try:
        name = seat.find_element(By.CSS_SELECTOR, ".seat-class-name").text.strip()
        seats_available = int(seat.find_element(By.CSS_SELECTOR, ".all-seats").text.strip())
        if name.upper() == SEAT_CLASS.upper():
            selected_seat = seat
            max_seats = seats_available
    except:
        continue

if not selected_seat:
    print(f"❌ Seat class '{SEAT_CLASS}' not found.")
    safe_quit()
    exit()

print(f"✔ Selected seat class {SEAT_CLASS} with {max_seats} available")

# ---------------- CLICK BOOK NOW ----------------
book_btn = selected_seat.find_element(By.CSS_SELECTOR, ".book-now-btn")
driver.execute_script("arguments[0].click();", book_btn)
print("✔ BOOK NOW clicked")
time.sleep(3)

# ---------------- COACH SELECTION ----------------
try:
    coach_select = wait.until(EC.presence_of_element_located((By.ID, "select-bogie")))

    def _parse_seats_from_option(opt):
        text = opt.get_attribute("textContent") or opt.text
        m = re.search(r"(\d{1,3}(?:,\d{3})?)\s*Seat", text, re.IGNORECASE)
        return int(m.group(1).replace(",", "")) if m else 0

    tried_values = set()
    attempt = 0
    chosen_item = None  # tuple (opt, seats, val)

    while attempt <= RETRY_COUNT:
        options = coach_select.find_elements(By.TAG_NAME, "option")
        opt_list = []
        for opt in options:
            seats = _parse_seats_from_option(opt)
            # skip options explicitly showing 0 seats to avoid wasting retries
            if seats <= 0:
                continue
            val = opt.get_attribute("value") or opt.text
            opt_list.append((opt, seats, val))

        # Sort coaches by descending available seats
        opt_list.sort(key=lambda x: x[1], reverse=True)

        # Find first coach with enough seats that we haven't tried yet
        pick = next((item for item in opt_list if item[1] >= SEATS_TO_SELECT and item[2] not in tried_values), None)
        if pick:
            chosen_item = pick
        else:
            # fall back to the best coach we haven't tried yet
            pick2 = next((item for item in opt_list if item[2] not in tried_values), None)
            chosen_item = pick2

        if not chosen_item:
            # nothing left to try
            break

        opt_elem, chosen_seats, val = chosen_item
        tried_values.add(val)

        if chosen_seats >= SEATS_TO_SELECT:
            # we found a coach with sufficient seats
            break

        # not enough seats in this coach — prepare to retry excluding it
        attempt += 1
        if attempt > RETRY_COUNT:
            break
        print(f"⚠ Not enough seats in selected coach ({chosen_seats} available, {SEATS_TO_SELECT} needed). Retrying ({attempt}/{RETRY_COUNT}) excluding previously tried coaches...")
        time.sleep(RETRY_DELAY)
        coach_select = driver.find_element(By.ID, "select-bogie")

    if not chosen_item or chosen_item[1] < SEATS_TO_SELECT:
        max_found = max((item[1] for item in opt_list), default=0)
        print(f"❌ Not enough seats available in any coach ({max_found} max, {SEATS_TO_SELECT} needed).")
        safe_quit()
        exit()

    # select the final chosen coach element
    final_opt = chosen_item[0]
    driver.execute_script("arguments[0].selected = true;", final_opt)
    final_opt.click()
    print("✔ Coach selected:", final_opt.text)
    time.sleep(2)
except Exception as e:
    print("❌ Coach selection failed:", e)
    safe_quit()
    exit()

# ---------------- SELECT SEATS ----------------
try:
    attempt = 0
    while True:
        seat_buttons = driver.find_elements(By.CSS_SELECTOR, "button.btn-seat.seat-available")
        if len(seat_buttons) >= SEATS_TO_SELECT:
            break
        attempt += 1
        if attempt > RETRY_COUNT:
            print(f"❌ Not enough seats available ({len(seat_buttons)} available, {SEATS_TO_SELECT} needed).")
            safe_quit()
            exit()
        print(f"⚠ Found only {len(seat_buttons)} seats, retrying ({attempt}/{RETRY_COUNT})...")
        time.sleep(RETRY_DELAY)

    for i in range(SEATS_TO_SELECT):
        btn = seat_buttons[i]
        driver.execute_script("arguments[0].click();", btn)
        print("✔ Seat selected:", btn.get_attribute("title"))
        time.sleep(0.3)

    print(f"✔ Successfully selected {SEATS_TO_SELECT} seats")
except Exception as e:
    print("❌ Seat selection failed:", e)
    safe_quit()
    exit()

# ---------------- CONTINUE PURCHASE ----------------
try:
    continue_btn = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "#confirmbooking > button.continue-btn"))
    )
    driver.execute_script("arguments[0].click();", continue_btn)
    print("✔ Continue Purchase clicked")
except Exception as e:
    print("❌ Could not click Continue Purchase:", e)
    safe_quit()
    exit()

# ---------------- WAIT FOR PASSENGER FORM AUTOMATICALLY ----------------
print("🔔 Waiting for passenger form to load after OTP...")

try:
    WebDriverWait(driver, 300).until(EC.presence_of_element_located((By.ID, "pname2")))
    print("✔ Passenger form loaded automatically")
except:
    print("❌ Passenger form did not load")
    safe_quit()
    exit()

# ---------------- FILL PASSENGERS 2–4 ----------------
print("✔ Filling Passenger 2–4...")

for idx, passenger in enumerate(PASSENGERS, start=2):
    try:
        name_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, f"pname{idx}"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", name_input)
        name_input.clear()
        name_input.send_keys(passenger["name"])

        if passenger["type"].lower() == "child":
            type_select = driver.find_element(By.ID, f"pType{idx}")
            driver.execute_script(
                """
                arguments[0].value = '2';
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """,
                type_select
            )

        print(f"✔ Passenger {idx} filled: {passenger['name']} ({passenger['type']})")
        time.sleep(0.3)

    except Exception as e:
        print(f"❌ Could not fill passenger {idx}: {e}")

# ---------------- SELECT BKASH PAYMENT ----------------
try:
    bkash_btn = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "div.payment-icon-holder.bkash"))
    )
    driver.execute_script("arguments[0].click();", bkash_btn)
    print("✔ Bkash payment selected")
except Exception as e:
    print("❌ Could not select Bkash payment:", e)
    safe_quit()
    exit()

# ---------------- PROCEED TO PAYMENT ----------------
try:
    confirm_btn = wait.until(EC.element_to_be_clickable((By.ID, "confirm_button")))
    driver.execute_script("arguments[0].click();", confirm_btn)
    print("✔ Proceed to Payment clicked")
except Exception as e:
    print("❌ Could not click Proceed to Payment:", e)
    safe_quit()
    exit()

print("🎉 FULL AUTOMATION COMPLETED – Payment page loaded")
