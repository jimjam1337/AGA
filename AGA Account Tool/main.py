import json
import logging
import os
import re
import smtplib
import time
import tkinter as tk
from datetime import datetime
from email.mime.text import MIMEText
from tkinter import simpledialog
import pyautogui
from PIL import Image, ImageTk
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# START FUNCTIONS

def create_log():
    print("starting log function")

    today_date = datetime.now().strftime("%Y-%m-%d")
    log_directory = r'.\logs'
    os.makedirs(log_directory, exist_ok=True)

    log_filename = os.path.join(log_directory, f'selenium_{today_date}.log')
    logger = logging.getLogger("selenium")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        file_handler = logging.FileHandler(log_filename)
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.info("log has been created")

    return logger


# Set up end of loop emails
def send_end_of_loop_email(email, email_body, operation_choice):
    # configure email accounts and settings
    sender_email = "raxtech@activegamers.com.au"
    sender_password = ")_U+My@Q%4?*"
    recipient_email = "jim@activegamers.com.au"

    # Your SMTP server and port
    smtp_server = "activegamers.com.au"
    smtp_port = 587

    # Create the email message

    message = MIMEText(email_body)
    message["Subject"] = f"account management ({operation_choice}) process has completed for {email}"
    message["From"] = sender_email
    message["To"] = recipient_email

    # Connect to the SMTP server and send the email
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        # Start TLS for security
        server.starttls()

        # Login to the email server
        server.login(sender_email, sender_password)

        # Send the email
        server.sendmail(sender_email, recipient_email, message.as_string())

    logger.info("Email sent at the end of the loop.")


def start_failed_accounts_log():
    """
    Initialize a new run with a timestamp.
    Returns the run entry dict you can append failures to.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {"timestamp": timestamp, "failed_accounts": []}


def save_failed_accounts(entry, file_path="failed_accounts.json"):
    """
    Save the collected failures for this run into the history JSON file.
    """
    if not entry["failed_accounts"]:
        return  # nothing to log

    # Load existing history if file exists
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                history = []  # reset if file is corrupt
    else:
        history = []

    # Append this run’s entry
    history.append(entry)

    # Save back to file
    with open(file_path, "w") as f:
        json.dump(history, f, indent=4)

    logger.info(f"Failed accounts saved to {file_path}")


# Set up account credentials
def define_base_credentials():
    email_bases = ["aga", "agapc", "wanxb", "wanpc","wodxb", "wodpc", "eagxb", "eagpc"]
    ranges_dict = {}

    root = tk.Tk()
    root.withdraw()  # Hide main window

    password = "AGA111222"
    alternate_password = "activegamers111222"

    for base in email_bases:
        user_input = simpledialog.askstring(
            "Input",
            f"Enter ranges for {base} (e.g. 1-3,7-10 or 0 to skip):",
            parent=root
        )
        if user_input is None:
            user_input = "0"
        ranges_dict[base] = parse_ranges(user_input)

    return email_bases, password, alternate_password, ranges_dict


def parse_ranges(range_str):
    ranges = []
    if not range_str.strip():
        return ranges

    for part in range_str.split(','):
        part = part.strip()
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                if 0 < start <= end:
                    ranges.append((start, end))
            except ValueError:
                continue  # skip invalid range
        else:
            try:
                n = int(part)
                if n > 0:
                    ranges.append((n, n))
            except ValueError:
                continue  # skip invalid number

    return ranges


# FUNCTION TO CREATE DIALOGUE BOX
def create_dialogue_box():
    result = {'value': None}  # Mutable container to store result

    # Function to update the result based on button clicked
    def set_result(value):
        result['value'] = value
        root.destroy()

    def set_result_activate():
        set_result("activate")

    def set_result_deactivate():
        set_result("deactivate")

    def set_result_add_gift_card():
        set_result("add_gift_card")

    def set_result_check_status():
        set_result("check_status")

    # GUI setup
#    home_dir = os.path.expanduser("~")
#    image_path = os.path.join(home_dir, "Documents", "GitHub", "AGA", "AGA Account Tool", "icons",
#                              "aga_logo_600x345.png")

    image_path = os.path.join("icons", "aga_logo_600x345.png")

    root = tk.Tk()
    root.title("AGA GamePass Account Tool")

    # Load image
    image = Image.open(image_path)
    image = image.resize((600, 345), Image.LANCZOS)
    photo = ImageTk.PhotoImage(image)

    # Background label
    label = tk.Label(root, image=photo)
    label.image = photo  # Keep a reference
    label.place(x=0, y=0, relwidth=1, relheight=1)

    # Buttons
    tk.Button(root, text="Activate", command=set_result_activate).place(relx=0.1, rely=0.5, anchor="center")
    tk.Button(root, text="Deactivate", command=set_result_deactivate).place(relx=0.35, rely=0.5, anchor="center")
    tk.Button(root, text="Add Gift Card", command=set_result_add_gift_card).place(relx=0.6, rely=0.5, anchor="center")
    tk.Button(root, text="Check Status", command=set_result_check_status).place(relx=0.85, rely=0.5, anchor="center")

    root.geometry("600x345")
    root.mainloop()

    if result['value'] is not None:
        logger.info("Returned result is %s", result['value'])
        return result['value']
    else:
        logging.warning("Dialog closed without selection")
        return "cancel"  # or None


# Process account action based on user input

def process_accounts_with_action(action_callback):
    email_bases, password, alternate_password, ranges = define_base_credentials()

    for email_base in email_bases:
        base_ranges = ranges.get(email_base, [])
        if not base_ranges:
            logger.info(f"Skipping {email_base} - no valid ranges")
            continue

        for start, end in base_ranges:
            for i in range(start, end + 1):
                if email_base in ["aga", "agapc"]:
                    email = f"{email_base}{i}@activegamers.com.au"
                else:
                    email = f"{email_base}{i:02}@activegamers.com.au"

                logger.info("Processing account: %s", email)
                driver = webdriver.Chrome()
                logger.info("Driver initialized")

                try:
                    action_callback(driver, email, password, alternate_password)
                finally:
                    driver.quit()


# LOGIN FUNCTIONS
def login_function(driver, email, password, alternate_password):
    logger.info("Begin login sequence")

    driver.set_window_size(1920, 1080)
    driver.maximize_window()
    driver.get("https://account.microsoft.com/")

    try:
        WebDriverWait(driver, 20).until(EC.url_contains("https://account.microsoft.com/"))

        signin_field = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "id__8"))
        )
        signin_field.click()
        logger.info("'Sign in' button clicked")

        email_field = WebDriverWait(driver, 40).until(
            EC.element_to_be_clickable((By.ID, "i0116"))
        )
        email_field.send_keys(email)
        email_field.send_keys(Keys.RETURN)
        logger.info("Email entered")

        other_ways_to_sign_in_bypass(driver)
        get_a_code_to_sign_in_bypass(driver)

        possible_signin_locators = [
            (By.ID, "id__8"),
            (By.ID, "passwordEntry"),
            (By.ID, "i0118")
        ]

        for locator in possible_signin_locators:
            try:
                password_field = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable(locator)
                )

                alternate_password_accounts = [
                    "aga11@activegamers.com.au", "aga22@activegamers.com.au",
                    "aga26@activegamers.com.au", "aga110@activegamers.com.au",
                    "aga111@activegamers.com.au"
                ]

                if email in alternate_password_accounts:
                    password_field.send_keys(alternate_password)
                    logger.info("Alternate password used")
                else:
                    password_field.send_keys(password)
                    logger.info("Standard password used")

                password_field.send_keys(Keys.RETURN)
                break
            except TimeoutException:
                logging.warning(f"Password field with locator {locator} not found. Trying next...")

    except TimeoutException:
        logging.error("Login page did not load or an element was not clickable")


def other_ways_to_sign_in_bypass(driver):
    try:
        # Wait up to 15 seconds for the element to be present and clickable
        other_ways_to_sign_in_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//span[text()="Other ways to sign in"]'))
        )
        other_ways_to_sign_in_button.click()
        logger.info('Clicked the \'Other ways to sign in\' button.')
    except TimeoutException:
        logger.info('Timed out waiting for \'Other ways to sign in\' button to appear.')


def get_a_code_to_sign_in_bypass(driver):
    try:
        # Wait up to 15 seconds for the element to be present and clickable
        use_your_password_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//span[text()="Use your password"]'))
        )
        use_your_password_button.click()
        logger.info("Clicked the 'Use your password' button.")
    except TimeoutException:
        logger.info("Timed out waiting for 'Use your password' button to appear.")


def handle_stay_signed_in_page(driver):
    try:
        WebDriverWait(driver, 5).until(EC.url_contains("https://login.live.com/ppsecure"))
        logger.info("Stay signed in page loaded")
        driver.get("https://account.microsoft.com/services")
        logger.info("stay signed in page was bypassed by loading https://account.microsoft.com")
    except TimeoutException:
        logger.info("Stay signed in page did not load")


def handle_tou_page(driver):
    try:
        WebDriverWait(driver, 5).until(EC.url_contains("https://account.live.com/tou/accrue?"))
        logger.info("TOU page loaded")
        driver.get("https://account.microsoft.com/")
        logger.info("TOU page was bypassed")
    except TimeoutException:
        logger.info("TOU page did not appear")


def handle_update_security_info_page(driver):
    try:
        looks_good_field = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.ID, "iLooksGood"))
        )
        looks_good_field.send_keys(Keys.RETURN)
        logger.info("Update security info window appeared enter was pressed on looks good button")
    except TimeoutException:
        logger.info("Update security info window did not appear")


def handle_privacy_notice_page(driver):
    try:
        WebDriverWait(driver, 3).until(
            EC.url_contains("https://privacynotice.account.microsoft.com/")
        )
        logger.info("Privacy notice page appeared")
        driver.get("https://account.microsoft.com/")
        logger.info("Privacy notice page was bypassed")
    except TimeoutException:
        logger.info("Privacy notice page did not appear")


def handle_upsell_page(driver):
    try:
        WebDriverWait(driver, 3).until(
            EC.url_contains("https://account.live.com/apps/upsell?")
        )
        driver.get("https://account.microsoft.com/")
        logger.info("Upsell page appeared and was bypassed")
    except TimeoutException:
        logger.info("Upsell page did not appear")


def handle_passkey_interrupt_page(driver):
    try:
        WebDriverWait(driver, 10).until(
            EC.url_contains("login.microsoft.com/consumers/fido")
        )
        #driver.get("https://account.live.com/interrupt/passkey/enrol")

        pyautogui.moveTo(1059, 623)
        time.sleep(1)
        pyautogui.click()
        time.sleep(1)
        pyautogui.click()
        logger.info("Passkey interrupt page appeared and was bypassed")
    except TimeoutException:
        logger.info("Passkey interrupt page did not appear")


def check_for_active_subscription(driver, email):
    global manage_xbox_element
    driver.get("https://account.microsoft.com/services")
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//span[contains(text(), "Next charge on")]'))
        )
        manage_xbox_element = "active"
        print(f"Account {email} is active")
        logger.info(f"Account {email} is active")

    except TimeoutException:
        manage_xbox_element = "inactive"
        print(f"Account {email} is not active")
        logger.info(f"Account {email} is not active")


def login_full_flow(driver, email, password, alternate_password):
    login_function(driver, email, password, alternate_password)
    logger.info("Handling any post-login interruptions for %s", email)
    #handle_stay_signed_in_page(driver)
    #handle_passkey_interrupt_page(driver)
    handle_tou_page(driver)
    handle_update_security_info_page(driver)
    time.sleep(30)
    #handle_privacy_notice_page(driver)
    #handle_upsell_page(driver)
    #handle_privacy_notice_page(driver)
    #check_for_active_subscription(driver, email)
    logger.info("login_full_flow completed for %s", email)


# ACTIVATE FLOW


def load_renew_page(driver, email):
    driver.set_page_load_timeout(20)
    try:
        driver.get(
            "https://www.xbox.com/en-AU/games/store/game-pass-premium/CFQ7TTC0P85B?rpid=cfq7ttc0khs0&ocid"
            "=PROD_AMC_Cons_MEEMG_Renew_XboxGPU")
        logger.info('load_renew_page finished. loading gamepass url...')
    except TimeoutException:
        logger.info("xbox renew page did not load within 20 seconds")
        run_entry["failed_accounts"].append({
            "email": email,
            "reason": "xbox renew page did not load within 20 seconds"
        })


def handle_passkey_interrupt_page_2(driver):
    try:
        WebDriverWait(driver, 10).until(
            EC.url_contains("/interrupt/passkey")
        )
        driver.get(
            "https://www.xbox.com/en-AU/games/store/game-pass-premium/CFQ7TTC0P85B?rpid=cfq7ttc0khs0&ocid"
            "=PROD_AMC_Cons_MEEMG_Renew_XboxGPU")
        logger.info(
            "handle_passkey_interrupt_page_2 completed. Second Passkey interrupt page appeared and was bypassed")
    except TimeoutException:
        logger.info(
            "handle_passkey_interrupt_page_2 completed. Second Passkey interrupt page did not appear")


def click_account_selection_button(driver):
    # wait up to 30 seconds for the account selection button to become present and clickable
    try:
        WebDriverWait(driver, 15).until(
            EC.url_contains("https://login.live.com/oauth20_authorize.srf")
        )
        actions = ActionChains(driver)
        actions.send_keys(Keys.RETURN)
        time.sleep(2)
        actions.perform()
        logger.info("click_account_selection_button completed. Account selection button was found")
        click_join_button(driver)

    except TimeoutException:
        logger.info("click_account_selection_button completed. Account selection button was not found.")


def find_manage_button(driver):
    try:
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="PageContent"]/div/div[1]/div[1]/div[6]/div/div[1]/a'))
        )
        logger.info("find_manage_button completed. Manage button was found. This account is already activated")

    except TimeoutException:
        logger.info(
            "find_manage_button completed. Manage button was not found. ")


def click_join_button(driver):
    try:
        join_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(@aria-label, 'Join')]")
            )
        )
        join_button.send_keys(Keys.RETURN)
        logger.info("click_join_button completed. Join button appeared and was clicked")

    except TimeoutException:
        logger.info(
            "click_join_button completed. Join button was not found. Will refresh the page"
        )

        try:
            driver.get(
                "https://www.xbox.com/en-AU/games/store/game-pass-premium/CFQ7TTC0P85B"
                "?rpid=cfq7ttc0khs0&ocid=PROD_AMC_Cons_MEEMG_Renew_XboxGPU"
            )

            join_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(@aria-label, 'Join')]")
                )
            )
            join_button.send_keys(Keys.RETURN)
            logger.info(
                "click_join_button completed. Join button appeared and was clicked after refresh"
            )

        except TimeoutException:
            logger.info(
                "click_join_button completed. Join button was not found after refresh."
            )


def load_subscription_page(driver, email):
    driver.set_page_load_timeout(20)
    try:
        # Navigate to the subscription page
        driver.get("https://account.microsoft.com/services")

        WebDriverWait(driver, 10).until(EC.url_contains(
            "https://account.microsoft.com/services")
        )
        logger.info("loading subscription page")

    except TimeoutException:
        logger.info("Subscription page timed out")
        run_entry["failed_accounts"].append({
            "email": email,
            "reason": "Subscription page timed out"
        })


def load_billing_page(driver, email):
    driver.set_page_load_timeout(20)  # max 20 seconds
    driver.get("https://account.microsoft.com/billing/payments")
    try:

        logger.info("Loading billing page")
        WebDriverWait(driver, 20).until(EC.url_contains(
            "https://account.microsoft.com/billing/payments")
        )
        logger.info("billing page loaded")

    except TimeoutException:
        logger.info("billing page timed out")
        run_entry["failed_accounts"].append({
            "email": email,
            "reason": "billing page timed out"
        })


def activate_account_flow(driver, email, password, alternate_password):
    logger.info("Activate loop initiated for %s", email)
    login_full_flow(driver, email, password, alternate_password)

    #if manage_xbox_element == "inactive":
    #    print(email, manage_xbox_element)
    load_renew_page(driver, email)
    handle_passkey_interrupt_page_2(driver)
    click_account_selection_button(driver)
    find_manage_button(driver)
    load_renew_page(driver, email)
    click_join_button(driver)
    time.sleep(15)
    logger.info("sleeping for 15 seconds to allows the subscribe modal to load")

    try:
        # Set the path to the subscribe button image
        icon_path = "C:/Users/james/Documents/GitHub/AGA/AGA Account Tool/icons/subscribe_button.png"

        try:
            # Locate the icon on the screen
            subscribe_button_position = pyautogui.locateOnScreen(icon_path, confidence=0.7)

            if subscribe_button_position is not None:
                logger.info("position is not none")
                # Get the center coordinates of the icon
                icon_x, icon_y = pyautogui.center(subscribe_button_position)

                pyautogui.click(icon_x, icon_y)
                time.sleep(1)
                pyautogui.click(icon_x, icon_y)

                logger.info("Icon clicked successfully!")

                try:
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, "//p[text()='Launch or install Xbox PC app']"))
                    )

                    logger.info("Launch or install Xbox PC app button was found. Account reactivation is complete "
                                "for account %s", email)
                    email_body = f"Account {email} has been activated"
                    send_end_of_loop_email(email, email_body, user_choice)
                    time.sleep(15)

                except TimeoutException:
                    logger.info(
                        "Launch or install Xbox PC app button did not become present and clickable. Check to "
                        "see if account has valid payment method (convert to gift code)")

                    run_entry["failed_accounts"].append({
                        "email": email,
                        "reason": "Launch or install Xbox PC app button did not become present and clickable. Check"
                                  "to see if account has valid payment method (convert to gift code)"
                    })

            else:
                logger.info("Subscribe button not found. Check for backup payment method on account")
                '''run_entry["failed_accounts"].append({
                    "email": email,
                    "reason": "Subscribe button not found. Check for backup payment method on account"
                })'''

        except Exception as e:
            logger.info(f"Error: {e}")
            print(f"{email} has not been activated due to {e}")
            '''run_entry["failed_accounts"].append({
                "email": email,
                "reason": f"{e}"
            })'''

    except TimeoutException:
        logger.info("Could not find subscribe button on screen (possible icon mismatch)")
        run_entry["failed_accounts"].append({
            "email": email,
            "reason": "Could not find subscribe button on screen (possible icon mismatch)"
        })
#else:
#    print("account is active, activation will not proceed")
#    logger.info(f"Account {email} is already active")

    logger.info("-----------------------------------------------------------------------------")


def deactivate_account_flow(driver, email, password, alternate_password):
    logger.info("Deactivate loop initiated for %s", email)
    login_full_flow(driver, email, password, alternate_password)
    email_body = ""

    try:
        # wait up to 10 seconds for main account page to load
        WebDriverWait(driver, 30).until(EC.url_contains("https://account.microsoft.com"))
        logger.info("main account page loaded")

        # load the billing cancellation page
        driver.get("https://account.microsoft.com/services/premium/cancel?fref=billing-cancel")
        logger.info("loading billing cancellation page")

        # wait 10 seconds for the page to load
        time.sleep(10)
        logger.info("sleeping for 10 seconds")

        # check to see if the services page has loaded instead of the billing page - this will indicate that
        # the account has no active subscriptions
        if driver.current_url == "https://account.microsoft.com/services/":
            logger.info("Services page loaded instead of billing page. This indicates the account has no "
                        "active subscriptions")
            email_body = "Services page loaded instead of billing page. This indicates the account has no " \
                         "active subscriptions"

        else:

            try:
                # wait up to 10 seconds for the billing cancellation page to load
                WebDriverWait(driver, 10).until(EC.url_contains(
                    "https://account.microsoft.com/services/premium/cancel"))

                try:
                    # Wait up to 20 seconds for the first cancel button to be present and clickable
                    cancel_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "benefit-cancel"))
                    )
                    cancel_button.send_keys(Keys.RETURN)
                    logger.info("First cancel button clicked")

                    # CODE TO HANDLE NON-REFUNDABLE SUBSCRIPTION (PAST FIRST MONTH)
                    try:
                        # wait up to 20 seconds for the 'back to subscription' button and 'resubscribe'
                        # button to be present and clickable. If this happens in this code block (before the
                        # ability to send keystrokes to the refund button), it tells us that a refund was not
                        # able to be issued, for whatever reason. Add more code here later allow us to
                        # clarify why not.
                        WebDriverWait(driver, 1).until(
                            EC.element_to_be_clickable(
                                (By.XPATH, '//span[contains(text(), "Back to subscription")]'))
                        )

                        WebDriverWait(driver, 1).until(
                            EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "Resubscribe")]'))
                        )

                        logger.info("Account %s has been deactivated but no refund was issued. Possibly the "
                                    "account was already deactivated with recurring billing turned off, "
                                    "or else we were over the threshold to be able to get a refund", email)
                        email_body = "Account %s has been deactivated but no refund was issued. Possibly the " \
                                     "account was already deactivated with recurring billing turned off, " \
                                     "or else we were over the threshold to be able to get a refund."

                    except TimeoutException:
                        logger.info("Back to subscription' and 'resubscribe' button did not become present"
                                    "and clickable. We will now send keystrokes for deactivation with refund.")

                    try:
                        # Optional: small delay to ensure page/modal is ready
                        time.sleep(2)

                        # Get screen size
                        screen_width, screen_height = pyautogui.size()

                        # Move mouse to center of the screen
                        center_x = screen_width // 2
                        center_y = screen_height // 2
                        pyautogui.moveTo(center_x, center_y, duration=0.5)

                        # Click at center
                        pyautogui.click()
                        time.sleep(2)

                        actions = ActionChains(driver)
                        actions.send_keys(Keys.ARROW_DOWN)
                        time.sleep(2)
                        actions.perform()

                        actions = ActionChains(driver)
                        actions.send_keys(Keys.TAB)
                        time.sleep(2)
                        actions.perform()

                        actions = ActionChains(driver)
                        actions.send_keys(Keys.RETURN)
                        time.sleep(2)
                        actions.perform()

                        logger.info("Refund keystrokes have been sent")

                        try:
                            # Wait up to 20 seconds for the 'back to subscription' and 'resubscribe' buttons
                            # to become present and clickable. If this happens in this code block (after the
                            # keystrokes have been sent) it will indicate that the subscription was
                            # correctly cancelled (and refund therefore issues).
                            WebDriverWait(driver, 20).until(
                                EC.element_to_be_clickable(
                                    (By.XPATH, '//span[contains(text(), "Back to subscription")]'))
                            )

                            WebDriverWait(driver, 20).until(
                                EC.element_to_be_clickable(
                                    (By.XPATH, '//span[contains(text(), "Resubscribe")]'))
                            )

                            logger.info(
                                "back to subscription' and 'refund' elements were located after refund "
                                "keystrokes were sent. This account should be deactivated and refund issued")
                            email_body = "Account has been deactivated and refund issued."

                        except TimeoutException:
                            logger.info("Cancel with refund keystrokes were sent but the back to sub and "
                                        "refund elements were not found. Something has gone wrong.")
                            email_body = "cancel with refund keystrokes were sent but the back to sub and " \
                                         "refund elements were not found. Something has gone wrong and this " \
                                         "account might not be deactivated."

                    except TimeoutException:
                        logger.info("refund button is not in the DOM")

                    # Close the browser window
                    logger.info("browser closed")

                except TimeoutException:
                    # if the cancel button did not become present and clickable
                    logger.info(
                        "Cancel button did not become present and clickable for account %s. "
                        "Probably the account has already been deactivated.", email)
                    email_body = "Cancel button did not become present and clickable. Probably the account" \
                                 "has already been deactivated."

            except TimeoutException:
                # if the billing cancellation page did not load
                logger.info("Billing cancellation page did not load for account %s", email)
                email_body = "Billing cancellation page did not load. Account has not been deactivated"

    except TimeoutException:
        # if the main account page failed to load
        logger.info("main account page failed to load within 30 seconds." ""
                    "Account %s has not been deactivated", email)
        email_body = "main account page failed to load within 30 seconds. Account has not been deactivated"


# REPLACE CREDIT CARD WITH GIFT CARD

def find_first_available_gift_card():
    for card in gift_card_data["codes"]:
        if card["status"] == "available":
            return card  # Return the first available card

    return None  # No available cards found


def mark_code_as_used(code_to_mark):
    # Find and update the matching code
    for card in gift_card_data["codes"]:
        if card["code"] == code_to_mark:
            card["status"] = "used"
            logger.info("Marked code as used: %s", code_to_mark)
            break

    # Write updated data back to the JSON gift_code_file
    with open("gift_card_codes.json", "w") as gift_code_file:
        json.dump(gift_card_data, gift_code_file, indent=2)


def click_remove_card_button(driver):
    try:
        # Wait until the "Remove card" button is clickable using a general XPath that contains "Remove card"
        remove_card_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "Remove card")]'))
        )
        remove_card_button.click()  # Click the button once it is clickable
        logger.info("Remove card button clicked successfully.")

        try:
            # Wait until the button specified by the absolute XPath is clickable
            confirm_remove_card_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH,
                                            '//*[@id="fluent-default-layer-host"]/div/div/div/div/div[2]/div['
                                            '2]/div/div['
                                            '2]/div[1]/div[2]/button[2]/span'))
            )
            confirm_remove_card_button.click()  # Click the button once it is clickable
            logger.info("confirm_remove_card_button clicked successfully.")

            # enter_gift_card_code()

        except TimeoutException:
            logger.info("Timeout: The 'Confirm Remove card' button was not found or not clickable.")

    except TimeoutException:
        logger.info("Timeout: The 'Remove card' button was not found or not clickable.")


def load_redeem_page(driver):
    driver.get("https://account.microsoft.com/billing/redeem")

    try:
        logger.info("Loading redeem page")
        WebDriverWait(driver, 20).until(EC.url_contains(
            "https://account.microsoft.com/billing/redeem")
        )
        logger.info("redeem page loaded")

    except TimeoutException:
        logger.info("redeem page did not load")


def check_account_balance(driver):
    balance_threshold = 18.0

    # Wait for the balance value
    balance_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((
            By.XPATH,
            '//span[contains(text(), "Microsoft account balance")]/parent::span/span[last()]'
        ))
    )

    raw_text = balance_element.text.strip()  # e.g. "2.05 AUD" or "25.00 USD"
    logger.info("Raw balance text: %s", raw_text)

    # Extract numeric value
    match = re.search(r"[-+]?\d*\.?\d+", raw_text)
    if not match:
        raise ValueError(f"Could not parse balance from text: {raw_text}")

    balance_value = float(match.group())
    logger.info("Parsed account balance: %.2f", balance_value)

    # ---- CONDITIONAL ACTION ----
    if balance_value < balance_threshold:
        logging.warning(
            "Balance below threshold (%.2f < %.2f)",
            balance_value,
            balance_threshold
        )
        print("⚠️ Balance is below threshold — proceed with gift card redemption")
        load_redeem_page(driver)
        add_gift_code(driver)
        print("⚠️ Balance is below threshold — action taken")

    else:
        logger.info(
            "Balance is sufficient (%.2f >= %.2f)",
            balance_value,
            balance_threshold
        )


def add_gift_code(driver):
    available_code = find_first_available_gift_card()

    # IF available code
    if available_code:
        gift_card_code = available_code["code"]
        logger.info("First available gift card: %s", gift_card_code)

        time.sleep(5)
        actions = ActionChains(driver)
        actions.send_keys(gift_card_code)
        actions.perform()
        time.sleep(10)
        actions.send_keys(Keys.TAB * 3)
        actions.send_keys(Keys.RETURN)
        actions.perform()
        logger.info("Gift card code submitted.")
        time.sleep(10)
        actions.send_keys(Keys.RETURN)
        actions.perform()
        logger.info("Confirmation submitted.")
        mark_code_as_used(gift_card_code)
        time.sleep(2)
    else:
        logger.info("No available gift cards found.")


#
def add_gift_card_flow(driver, email, password, alternate_password):
    logger.info("Add gift card loop initiated for %s", email)
    login_full_flow(driver, email, password, alternate_password)

    if manage_xbox_element == "inactive":
        logger.info("{email}, manage_xbox_element")
        load_billing_page(driver, email)
        click_remove_card_button(driver)
        logger.info("remove card function finished")
        check_account_balance(driver)


    else:
        print("account is active, gift card addition will not proceed")
        logger.info("account is active, gift card addition will not proceed")

    logger.info("-----------------------------------------------------------------------------------------")


def check_status_flow(driver, email, password, alternate_password):
    logger.info("Check status loop initiated for %s", email)
    login_full_flow(driver, email, password, alternate_password)


# MAIN EXECUTION FLOW


create_log()  # set up logging
logger = logging.getLogger("selenium")
print("log is created")
run_entry = start_failed_accounts_log()

# get the users choice from the dialogue box
user_choice = create_dialogue_box()

if user_choice == "activate":
    process_accounts_with_action(activate_account_flow)
    save_failed_accounts(run_entry)

if user_choice == "deactivate":
    process_accounts_with_action(deactivate_account_flow)
    save_failed_accounts(run_entry)

if user_choice == "add_gift_card":
    # Load JSON object from file
    with open("gift_card_codes.json", "r") as file:
        gift_card_data = json.load(file)

    # Access the data
    print(gift_card_data)

    process_accounts_with_action(add_gift_card_flow)
    save_failed_accounts(run_entry)

if user_choice == "check_status":
    process_accounts_with_action(check_status_flow)
