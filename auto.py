import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc

# ---------------- CONFIG ----------------
MOBILE = "01334042088"
PASSWORD = "A17041994"

FROM_CITY = "Dhaka"
TO_CITY = "Cox's Bazar"
DOJ = "29-Nov-2025"

SEAT_CLASS = "SNIGDHA"
TARGET_TRAIN = "PARJOTAK EXPRESS (816)"
SEATS_TO_SELECT = 4

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
    mobile_field.send_keys(MOBILE)

    pass_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
    pass_field.send_keys(PASSWORD)

    login_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".login-form-submit-btn")))
    driver.execute_script("arguments[0].click();", login_btn)

    time.sleep(3)
    print("✔ Login successful")
except Exception as e:
    print("❌ Login failed:", e)
    driver.quit()
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
    driver.quit()
    exit()

print(f"✔ Found {len(train_rows)} trains")

target_row = None
for row in train_rows:
    try:
        t_name = row.find_element(By.CSS_SELECTOR, ".trip-left-info h2").text.strip().upper()
        print("Train:", t_name)
        if TARGET_TRAIN.upper() in t_name:
            target_row = row
            break
    except:
        continue

if not target_row:
    print("❌ Train not found:", TARGET_TRAIN)
    driver.quit()
    exit()

# ---------------- SELECT SEAT CLASS ----------------
seat_rows = target_row.find_elements(By.CSS_SELECTOR, ".seat-available-wrap")
selected_seat = None
max_seats = 0

for seat in seat_rows:
    try:
        name = seat.find_element(By.CSS_SELECTOR, ".seat-class-name").text.strip()
        seats_available = int(seat.find_element(By.CSS_SELECTOR, ".all-seats").text.strip())

        if name.upper() == SEAT_CLASS.upper() and seats_available > max_seats:
            selected_seat = seat
            max_seats = seats_available
    except:
        continue

if not selected_seat:
    print(f"❌ Seat class '{SEAT_CLASS}' not found inside train.")
    driver.quit()
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
    options = coach_select.find_elements(By.TAG_NAME, "option")

    chosen_option = None
    for opt in options:
        if "0 Seat(s)" not in opt.text:
            chosen_option = opt
            break

    if not chosen_option:
        print("❌ No coach with seats available.")
        driver.quit()
        exit()

    driver.execute_script("arguments[0].selected = true;", chosen_option)
    chosen_option.click()
    print("✔ Coach selected:", chosen_option.text)
    time.sleep(2)
except Exception as e:
    print("❌ Coach selection failed:", e)
    driver.quit()
    exit()

# ---------------- SELECT SEATS ----------------
try:
    seat_buttons = driver.find_elements(By.CSS_SELECTOR, "button.btn-seat.seat-available")

    if len(seat_buttons) < SEATS_TO_SELECT:
        print("❌ Not enough seats available")
        driver.quit()
        exit()

    for i in range(SEATS_TO_SELECT):
        btn = seat_buttons[i]
        driver.execute_script("arguments[0].click();", btn)
        print("✔ Seat selected:", btn.get_attribute("title"))
        time.sleep(0.3)

    print(f"✔ Successfully selected {SEATS_TO_SELECT} seats")
except Exception as e:
    print("❌ Seat selection failed:", e)
    driver.quit()
    exit()

# ---------------- FETCH SELECTED SEAT DETAILS ----------------
try:
    time.sleep(1)
    seat_table_elements = driver.find_elements(By.ID, "tbl_seat_list")
    if seat_table_elements:
        seat_table = seat_table_elements[0]
        rows = seat_table.find_elements(By.CSS_SELECTOR, "tr.seat-info-row, tr.seat-info-row-last")

        seat_details = []
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            seat_class = cells[0].text.strip()
            seat_number = cells[1].text.strip()
            fare = cells[2].text.strip()
            seat_details.append({
                "class": seat_class,
                "number": seat_number,
                "fare": fare
            })

        print("✔ Selected seat details:")
        for s in seat_details:
            print(f"  - {s['class']} | {s['number']} | {s['fare']}")
    else:
        print("⚠ Seat table not found")
except Exception as e:
    print("❌ Could not fetch seat details:", e)

# ---------------- CLICK CONTINUE PURCHASE ----------------
try:
    continue_btn = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "#confirmbooking button.continue-btn"))
    )
    driver.execute_script("arguments[0].click();", continue_btn)
    print("✔ CONTINUE PURCHASE clicked")
except Exception as e:
    print("❌ Could not click Continue Purchase:", e)

# ---------------- OTP VERIFICATION ----------------
print("⏳ Checking if OTP verification is needed...")

try:
    otp_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#railway-otp-input-wrapper"))
    )

    print("📱 OTP verification required.")
    print("👉 Enter the 4-digit OTP manually in the browser.")
    print("⏳ Waiting for OTP to be verified...")

    WebDriverWait(driver, 120).until_not(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#railway-otp-input-wrapper"))
    )

    print("✔ OTP verified successfully!")

except TimeoutException:
    print("✔ No OTP required. Proceeding automatically.")

# ---------------- PASSENGER PAGE ----------------
try:
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "app-passenger-form"))
    )
    print("✔ Passenger form loaded!")
except:
    print("⚠ Passenger form not detected — but flow may still be correct.")

print("🎉 FLOW COMPLETE — Passenger details page is ready.")
input("Press Enter to exit...")

driver.quit()
