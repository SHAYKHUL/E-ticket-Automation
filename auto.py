import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc

# ---------------- CONFIG ----------------
MOBILE = "01749473613"
PASSWORD = "Sh@ykhul_2004!"

FROM_CITY = "Dhaka"
TO_CITY = "Cox's Bazar"
DOJ = "29-Nov-2025"

SEAT_CLASS = "AC_S"
TARGET_TRAIN = "PARJOTAK EXPRESS (816)"
SEATS_TO_SELECT = 4

PASSENGERS = [
    {"name": "John Doe", "type": "1"},    # Passenger 2
    {"name": "Jane Smith", "type": "1"},  # Passenger 3
    {"name": "Bob Johnson", "type": "2"}  # Passenger 4
]

PAYMENT_METHOD = "bkash"  # Options: "bkash", "nagad", "rocket"

LOGIN_URL = "https://eticket.railway.gov.bd/login"
SEARCH_URL = f"https://eticket.railway.gov.bd/booking/train/search?fromcity={FROM_CITY}&tocity={TO_CITY}&doj={DOJ}&class={SEAT_CLASS}"

# ---------------- BROWSER SETUP ----------------
options = uc.ChromeOptions()
options.add_argument("--no-first-run")
options.add_argument("--no-default-browser-check")
options.add_argument("--disable-blink-features=AutomationControlled")

# Auto-allow location
prefs = {
    "profile.default_content_setting_values.geolocation": 1  # 1 = allow, 2 = block
}
options.add_experimental_option("prefs", prefs)

# Launch Chrome without persistent profile
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
    options_list = coach_select.find_elements(By.TAG_NAME, "option")
    chosen_option = None
    for opt in options_list:
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
    print("📱 OTP verification required. Enter the 4-digit OTP manually in the browser.")
    WebDriverWait(driver, 120).until_not(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#railway-otp-input-wrapper"))
    )
    print("✔ OTP verified successfully!")
except TimeoutException:
    print("✔ No OTP required. Proceeding automatically.")

# ---------------- FILL PASSENGER 2,3,4 ----------------
try:
    passenger_forms = driver.find_elements(By.CSS_SELECTOR, "app-passenger-form")
    for i, passenger in enumerate(PASSENGERS, start=1):  # start=1 skips Passenger 1
        if i >= len(passenger_forms):
            print(f"⚠ Only {len(passenger_forms)} passenger forms found, expected at least {i+1}")
            break
        form = passenger_forms[i]
        name_input = form.find_element(By.CSS_SELECTOR, "input[formcontrolname='full_name']")
        name_input.clear()
        name_input.send_keys(passenger['name'])
        type_select = form.find_element(By.CSS_SELECTOR, "select[formcontrolname='passenger_type']")
        driver.execute_script(
            "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change'))",
            type_select, passenger['type']
        )
        print(f"✔ Passenger {i+1} Name & Type filled: {passenger['name']} / {'Adult' if passenger['type']=='1' else 'Child'}")
    print("✔ All passenger details filled successfully")
except Exception as e:
    print("❌ Could not fill passenger details:", e)

# ---------------- SELECT PAYMENT METHOD ----------------
try:
    payment_section = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "mobileBanking"))
    )
    payment_btn = payment_section.find_element(
        By.CSS_SELECTOR, f"div.payment-icon-holder.{PAYMENT_METHOD}"
    )
    driver.execute_script("arguments[0].click();", payment_btn)
    print(f"✔ Payment method selected: {PAYMENT_METHOD.capitalize()}")
    
    proceed_btn = driver.find_element(By.CSS_SELECTOR, "#confirm_button")
    driver.execute_script("arguments[0].click();", proceed_btn)
    print("✔ Proceeded to payment page")
except Exception as e:
    print("❌ Payment selection failed:", e)

# ---------------- MANUAL bKash PAYMENT ----------------
if PAYMENT_METHOD.lower() == "bkash":
    print("⚠ bKash payment modal opened.")
    print("📌 PLEASE complete the bKash payment manually in the popup window.")
    input("Press Enter here AFTER payment is done...")
    print("✔ Payment completed manually.")

# ---------------- END ----------------
print("🎉 FLOW COMPLETE — All steps done.")
input("Press Enter to exit...")
driver.quit()
