import logging
import os
import time
import tkinter as tk
from tkinter import simpledialog
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from PIL import Image, ImageTk
from selenium.webdriver.common.action_chains import ActionChains

import pyautogui
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Get today's date in the format YYYY-MM-DD
today_date = datetime.now().strftime("%Y-%m-%d")

# Create the log directory if it doesn't exist
log_directory = 'logs'
os.makedirs(log_directory, exist_ok=True)

# Create the log filename with today's date
log_filename = f'{log_directory}selenium_{today_date}.log'

# Configure logging with the filename
logging.basicConfig(filename=log_filename, level=logging.INFO)

# email configuration

sender_email = "raxtech@activegamers.com.au"
sender_password = ")_U+My@Q%4?*"
recipient_email = "jim@activegamers.com.au"

# Your SMTP server and port
smtp_server = "activegamers.com.au"
smtp_port = 587


# function to send en email at the end of reactive/deactivate/create loop

# Create the email message
def send_end_of_loop_email():
    message = MIMEText(email_body)
    message["Subject"] = f"account management ({result}) process has completed for {email}"
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

    logging.info("Email sent at the end of the loop.")


# CODE FOR DIALOGUE BOX

result = None  # Default value, can be changed in the dialogue box functions


def set_result_reactivate():
    global result
    result = "Reactivate"
    root.destroy()


def set_result_deactivate():
    global result
    result = "Deactivate"
    root.destroy()


def set_result_setup():
    global result
    result = "First time setup"
    root.destroy()


# Get the user's home directory
home_dir = os.path.expanduser("~")

# Construct the path to the documents directory
documents_dir = os.path.join(home_dir, "Documents", "GitHub", "AGA", "AGA Account Tool", "icons")

# Construct the path to the background image
bg_image_path = os.path.join(documents_dir, "aga_logo_600x345.png")

root = tk.Tk()
root.title("AGA GamePass Account Tool")

# Load the background image
original_image = Image.open(bg_image_path)

# Set the desired window size
window_width = 600
window_height = 345

# Resize the image to fit the window using LANCZOS resampling
resized_image = original_image.resize((window_width, window_height), Image.LANCZOS)
bg_image = ImageTk.PhotoImage(resized_image)

# Create a label with the background image
bg_label = tk.Label(root, image=bg_image)
bg_label.image = bg_image  # Store the PhotoImage object as an attribute of the label
bg_label.place(x=0, y=0, relwidth=1, relheight=1)

# Set the window size
root.geometry(f"{window_width}x{window_height}")

Reactivate_button = tk.Button(root, text="Reactivate", command=set_result_reactivate)
Reactivate_button.place(relx=0.2, rely=0.5, anchor="center")

deactivate_button = tk.Button(root, text="Deactivate", command=set_result_deactivate)
deactivate_button.place(relx=.5, rely=0.5, anchor="center")

setup_button = tk.Button(root, text="Setup", command=set_result_setup)
setup_button.place(relx=.7, rely=0.5, anchor="center")

root.mainloop()


# DIALOGUE BOX ENDS

# CODE FOR LOGIN FUNCTION

def login_function():
    logging.info("begin login sequence")

    # set driver to be full screen
    driver.set_window_size(1920, 1080)
    driver.maximize_window()

    # Navigate to the Microsoft login page
    driver.get("https://account.microsoft.com/")

    try:
        # Waiting up to 20 seconds for the Microsoft account sign in page to load
        WebDriverWait(driver, 20).until(EC.url_contains("https://account.microsoft.com/"))

        try:
            # Wait up to 20 seconds for the 'sign in' button to be present and clickable
            signin_field = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.ID, "id__8"))
            )
            # Click the 'sign in' button
            signin_field.click()
            logging.info("'sign in' button clicked")

            try:
                # Wait up to 20 seconds for the email field to be present and clickable
                email_field = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.ID, "i0116"))
                )
                logging.info("email field clickable")
                # Send the email to the email field
                email_field.send_keys(email)
                email_field.send_keys(Keys.RETURN)
                logging.info("email string sent to email field")

                try:
                    # Wait up to 20 seconds for the password field to be present and clickable
                    password_field = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.ID, "i0118"))
                    )
                    logging.info("password field clickable")
                    # Send the password to the email field

                    # List of accounts which have a different password (activegamers111222)
                    alternate_password_accounts = ["aga11@activegamers.com.au", "aga22@activegamers.com.au",
                                                   "aga26@activegamers.com.au", "aga110@activegamers"
                                                                                ".com.au", "aga111@activegamers.com.au"]
                    # Check if the email variable is in the list of certain values
                    if email in alternate_password_accounts:
                        logging.info("account is on the alternate password list")
                        # Send the alternate password if the email matches any of the certain values
                        password_field.send_keys(alternate_password)
                        password_field.send_keys(Keys.RETURN)
                        logging.info("alternate password string sent to password field")
                    else:
                        # Send the default password for other cases
                        password_field.send_keys(password)
                        password_field.send_keys(Keys.RETURN)
                        logging.info("standard password string sent to pword field")

                except TimeoutException:
                    # if the email field does not become present and clickable
                    logging.info("email field did not become present and clickable")

            except TimeoutException:
                # if the signin button field does not become present and clickable
                logging.info("'sign in' button did was become present and clickable")

        except TimeoutException:
            # if the password field did not become present and clickable
            logging.info("password field did not become present and clickable")

        # CODE IN CASE 'WE'RE UPDATING OUR TOU PAGE LOADS'

        try:
            # Wait up to 5 seconds for the TOU update page to load
            WebDriverWait(driver, 5).until(EC.url_contains("https://account.live.com/tou/accrue?"))
            logging.info("TOU page loaded")

            try:
                # wait up to 5 seconds for the 'Next' button to become present and clickable
                next_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "iNext"))
                )
                next_button.send_keys(Keys.RETURN)
                logging.info("'Next' button on TOU page clicked")

            except TimeoutException:
                # if the 'Next' button did not become present and clickable
                logging.info("next button did not become present and clickable")

            # if URL contains "https://account.live.com/tou/accrue?", press enter
            pyautogui.press('enter', presses=1)
            logging.info(
                "second privacy notice page 'https://privacynotice.account.microsoft.com/' appeared and was bypassed")

        except TimeoutException:
            # if the URL does not contain "https://privacynotice.account.microsoft.com/"
            logging.info("second privacy notice page 'https://privacynotice.account.microsoft.com/' did not appear")

    except TimeoutException:
        # if the URL does not contain "https://account.microsoft.com"
        logging.info("Microsoft account page sign in page did not load")

    # CODE IN CASE UPDATE SECURITY INFO PAGE LOADS

    try:
        # Check if the 'iLooksGood' element is present and clickable
        looks_good_field = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "iLooksGood")))
        # if the element is clickable, send enter to the looks good field
        looks_good_field.send_keys(Keys.RETURN)
        logging.info("update security info window appeared and was bypassed")
    except TimeoutException:
        logging.info("update security info window did not appear")

    # CODE IN CASE PRIVACY NOTICE PAGE LOADS

    try:
        # Waiting up to 5 seconds for the privacy notice page to load
        WebDriverWait(driver, 5
                      ).until(EC.url_contains("https://privacynotice.account.microsoft.com/"))
        logging.info("Waiting to see if privacy notice page appears")

        # if URL contains "https://privacynotice.account.microsoft.com/", bypass and go to the main account page
        driver.get("https://account.microsoft.com/")
        logging.info(
            "privacy notice page 'https://privacynotice.account.microsoft.com/' appeared and was bypassed")

    except TimeoutException:
        # if the URL does not contain "https://privacynotice.account.microsoft.com/"
        logging.info("privacy notice page 'https://privacynotice.account.microsoft.com/' did not appear")

    # CODE IN CASE BREAK FREE OF YOUR PASSWORDS (UPSELL) PAGE LOADS

    try:
        # waiting for up to 5 seconds to see if the break free of your passwords page loads
        WebDriverWait(driver, 5).until(EC.url_contains("https://account.live.com/apps/upsell?"))

        # if the URL contains "https://account.live.com/apps/upsell?", skip it and go to the main account page
        driver.get("https://account.microsoft.com/")
        logging.info("Upsell page 'https://account.live.com/apps/upsell?' appeared and was bypassed")

    except TimeoutException:
        # if the URL does not contain "https://account.live.com/apps/upsell?"
        logging.info("Upsell page 'https://account.live.com/apps/upsell?' did not appear")

    # CODE IN CASE STAY SIGNED IN WINDOW APPEARS

    try:
        # Wait for the 'stayed signed in? no' field to be present and clickable
        stay_signed_in_no_field = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "declineButton"))
        )

        # send enter to the 'stay signed in? no' field
        stay_signed_in_no_field.send_keys(Keys.RETURN)

        logging.info("stay signed in window appeared and was completed")

    except TimeoutException:
        logging.info("stay signed in window did not appear")

        # CODE IN CASE SECOND PRIVACY NOTICE PAGE LOADS (case5)

    try:
        # Waiting up to 10 seconds for the privacy notice page to load
        WebDriverWait(driver, 5).until(EC.url_contains("https://privacynotice.account.microsoft.com/"))
        logging.info("Waiting to see if privacy notice page appears")

        # if URL contains "https://privacynotice.account.microsoft.com/", bypass and go to the main account page
        driver.get("https://account.microsoft.com/")
        logging.info(
            "second privacy notice page 'https://privacynotice.account.microsoft.com/' appeared and was bypassed")

    except TimeoutException:
        # if the URL does not contain "https://privacynotice.account.microsoft.com/"
        logging.info("second privacy notice page 'https://privacynotice.account.microsoft.com/' did not appear")

    logging.info("login function completed for %s", email)


# DEFINE THE BASE EMAIL AND PASSWORD
email_base = ["aga", "agapc"]
password = "AGA111222"
alternate_password = "activegamers111222"
# Ask for the starting and ending values of the ranges
start_value_1 = simpledialog.askinteger("Input", "Enter the starting value for Xbox accounts [1]")
# Use the default value if the user didn't enter anything
if not start_value_1:
    start_value_1 = 1
end_value_1 = simpledialog.askinteger("Input", "Enter the ending value for Xbox accounts [119]")
# Use the default value if the user didn't enter anything
if not end_value_1:
    end_value_1 = 119
start_value_2 = simpledialog.askinteger("Input", "Enter the starting value for PC accounts [1]")
# Use the default value if the user didn't enter anything
if not start_value_2:
    start_value_2 = 1
end_value_2 = simpledialog.askinteger("Input", "Enter the ending value for PC accounts [24]")
# Use the default value if the user didn't enter anything
if not end_value_2:
    end_value_2 = 24

ranges = [(start_value_1, end_value_1 + 1), (start_value_2, end_value_2 + 1)]

logging.info("define base email and password finished")

# REACTIVATE CODE

if result == "Reactivate":
    logging.info("Reactivate loop initiated")

    # Loop through each base email and range
    for email_base, r in zip(email_base, ranges):
        # Loop through each account
        for i in range(*r):
            # Create the email address
            email = email_base + str(i) + "@activegamers.com.au"

            # log which account will be reactivated based on email variable
            logging.info('Beginning reactivation of account %s', email)

            # Initialize the driver
            driver = webdriver.Chrome()
            logging.info("driver initialized")

            login_function()

            # Navigate to the subscriptions page
            #driver.get(
            #    "https://www.xbox.com/en-au/games/store/xbox-game-pass-ultimate/cfq7ttc0khs0?=&OCID"
            #   "=PROD_AMC_Cons_MEEMG_Renew_XboxGPU&rtc=1")

            driver.get("https://www.xbox.com/en-AU/auth/msa?action=logIn&amp;returnUrl=https%3A%2F%2Fwww.xbox.com%2Fen-au%2Fgames%2Fstore%2Fxbox-game-pass-ultimate%2Fcfq7ttc0khs0%3F%3D%26OCID%2522%2522%3DPROD_AMC_Cons_MEEMG_Renew_XboxGPU%26rtc%3D1&amp;ru=https%3A%2F%2Fwww.xbox.com%2Fen-au%2Fgames%2Fstore%2Fxbox-game-pass-ultimate%2Fcfq7ttc0khs0%3F%3D%26OCID%2522%2522%3DPROD_AMC_Cons_MEEMG_Renew_XboxGPU%26rtc%3D1")

            time.sleep(5)

            logging.info('slept 5 seconds')

            pyautogui.press('enter')

            logging.info('pressed enter')

            time.sleep(10)

            logging.info('slept 10 seconds')

            driver.get(
                "https://www.xbox.com/en-au/games/store/xbox-game-pass-ultimate/cfq7ttc0khs0?=&OCID"
               "=PROD_AMC_Cons_MEEMG_Renew_XboxGPU&rtc=1")

            logging.info('go to gamepass url')

            try:
                # wait up to 10 seconds for the join button to become present and clickable
                join_button = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH,
                                                "//button[@aria-label='Join Xbox Game Pass Ultimate. AU$22.95 per month']"))
                )

                logging.info("join button is present and clickable")
                join_button.send_keys(Keys.RETURN)

                time.sleep(10)
                logging.info("sleeping for 10 seconds to allows the subscribe modal to load")

                try:
                    # Set the path to the subscribe button image
                    icon_path = "C:/Users/james/Documents/GitHub/AGA/AGA Account " \
                                "Tool/icons/subscribe_button.png"

                    try:
                        # Locate the icon on the screen
                        subscribe_button_position = pyautogui.locateOnScreen(icon_path, confidence=0.7)

                        if subscribe_button_position is not None:
                            # Get the center coordinates of the icon
                            icon_x, icon_y = pyautogui.center(subscribe_button_position)

                            # Move the mouse to the icon's center and click it to get window focus
                            pyautogui.click(icon_x, icon_y)

                            # Optionally, add a short delay before clicking (adjust as needed)
                            time.sleep(1)

                            # Move the mouse to the icon's center and click it
                            pyautogui.click(icon_x, icon_y)

                            logging.info("Icon clicked successfully!")

                            try:
                                # Wait until the 'download the xbox app' button is present and clickable.
                                # this will confirm reactivation.
                                '''subscribe_button = WebDriverWait(driver, 20).until( 
                                EC.presence_of_element_located((By.XPATH, "//a[text()='DOWNLOAD THE XBOX 
                                APP']")) )

                                '''
                                logging.info("Account reactivation is complete for account %s", email)
                                email_body = "Account has been reactivated, confirm this by checking the " \
                                             "account " \
                                             "inbox"
                                send_end_of_loop_email()
                                time.sleep(15)

                            except TimeoutException:
                                logging.info(
                                    "DOWNLOAD THE XBOX APP button did not become present and clickable")

                        else:
                            logging.info("Icon not found on the screen.")
                            input()

                    except Exception as e:
                        logging.info(f"Error: {e}")

                except TimeoutException:
                    logging.info("subscribe button did not become present and clickable")

            except TimeoutException:
                logging.info("Join button did not become present and clickable")


#            try:
#                # wait up to 10 seconds for the buy gamepass as a gift button to become present and clickable
#                buy_gamepass_as_a_gift_button = WebDriverWait(driver, 10).until(
#                    EC.element_to_be_clickable(
#                        (By.XPATH, "//button[@title='Buy Xbox Game Pass Ultimate as a gift']"))
#                )
#                logging.info("buy gamepass as a gift button is present and clickable")
#                time.sleep(5)
#                buy_gamepass_as_a_gift_button.send_keys(Keys.RETURN)
#                logging.info("enter key pressed on buy gamepass as a gift button")


#            try:  # Check if the 'Tilelist' (sign in box?) element is present and clickable
#                tilelist_field = WebDriverWait(driver, 5).until(
#                    EC.element_to_be_clickable((By.XPATH, "//*[@id='tileList']/div[1]/div/button/div[2]/div[2]")))#
#
#               logging.info("tilelist_field is present and clickable")
#
#                pyautogui.press('enter')
#
#                logging.info("enter key pressed")
#
#                # CODE IN CASE STAY SIGNED IN WINDOW APPEARS
#
#                try:
#                    # Wait for the 'stayed signed in? no' field to be present and clickable
#                    stay_signed_in_no_field = WebDriverWait(driver, 5).until(
#                        EC.element_to_be_clickable((By.ID, "declineButton"))
#                    )
#
#                    # send enter to the 'stay signed in? no' field
#                    stay_signed_in_no_field.send_keys(Keys.RETURN)
#
#                    logging.info("stay signed in window appeared and was completed")
#
#                except TimeoutException:
#                    logging.info("stay signed in window did not appear")#
#
#
#
#            except TimeoutException:
#                logging.info("Element with ID 'tilelist' did not become present and clickable")

#            except TimeoutException:
#                logging.info("Buy gamepass as a gift button did not become present and clickable")

            logging.info("-----------------------------------------------------------------------------")

# DEACTIVATE CODE
if result == "Deactivate":
    logging.info("Deactivate loop initiated")

    # Loop through each base email and range
    for email_base, r in zip(email_base, ranges):
        # Loop through each account
        for i in range(*r):
            # Create the email address
            email = email_base + str(i) + "@activegamers.com.au"

            # log which account will be deactivated based on email variable
            logging.info('Beginning deactivation of account %s', email)

            # Initialize the driver
            driver = webdriver.Chrome()
            logging.info("driver initialized")

            login_function()

            try:
                # wait up to 10 seconds for main account page to load
                WebDriverWait(driver, 10).until(EC.url_contains("https://account.microsoft.com"))
                logging.info("main account page loaded")

                # load the billing cancellation page
                driver.get("https://account.microsoft.com/services/xboxgamepassultimate/cancel?fref=billing-cancel")
                logging.info("loading billing cancellation page")

                # wait 10 seconds for the page to load
                time.sleep(10)
                logging.info("sleeping for 10 seconds")

                # check to see if the services page has loaded instead of the billing page - this will indicate that
                # the account has no active subscriptions
                if driver.current_url == "https://account.microsoft.com/services/":
                    logging.info("Services page loaded instead of billing page. This indicates the account has no "
                                 "active subscriptions")
                    email_body = "Services page loaded instead of billing page. This indicates the account has no " \
                                 "active subscriptions"

                else:

                    try:
                        # wait up to 10 seconds for the billing cancellation page to load
                        WebDriverWait(driver, 10).until(EC.url_contains(
                            "https://account.microsoft.com/services/xboxgamepassultimate/cancel?fref=billing-cancel"))

                        # confirm that the billing cancellation page loaded
                        if "https://account.microsoft.com/services/xboxgamepassultimate/cancel?fref=billing-cancel" in driver.current_url:
                            logging.info("billing cancellation page loaded")

                        else:
                            driver.get("https://account.microsoft.com/services/xboxgamepass/details#billing")
                            logging.info("account was using game pass for console. GPC billing page loaded instead.")

                        try:
                            # Wait up to 20 seconds for the cancel button to be present and clickable
                            cancel_button = WebDriverWait(driver, 10).until(
                                EC.element_to_be_clickable((By.ID, "benefit-cancel"))
                            )
                            cancel_button.send_keys(Keys.RETURN)
                            logging.info("Cancel button clicked")

                            try:
                                # wait up to 20 seconds for the 'back to subscription' button and 'resubscribe'
                                # button to be present and clickable. If this happens in this code block (before the
                                # ability to send keystrokes to the refund button), it tells us that a refund was not
                                # able to be issued, for whatever reason. Add more code here later allow us to
                                # clarify why not.
                                back_to_subscription_button = WebDriverWait(driver, 10).until(
                                    EC.element_to_be_clickable(
                                        (By.XPATH, '//span[contains(text(), "Back to subscription")]'))
                                )

                                resubscribe_button = WebDriverWait(driver, 10).until(
                                    EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "Resubscribe")]'))
                                )

                                logging.info("Account %s has been deactivated but no refund was issued. Possibly the "
                                             "account was already deactivated with recurring billing turned off, "
                                             "or else we were over the threshold to be able to get a refund", email)
                                email_body = "Account %s has been deactivated but no refund was issued. Possibly the " \
                                             "account was already deactivated with recurring billing turned off, " \
                                             "or else we were over the threshold to be able to get a refund."

                            except TimeoutException:
                                logging.info("Back to subscription' and 'resubscribe' button did not become present"
                                             "and clickable. We will now send keystrokes for deactivation with refund.")

                                time.sleep(5)
                                actions = ActionChains(driver)
                                actions.send_keys(Keys.ARROW_DOWN)
                                actions.send_keys(Keys.TAB)
                                actions.send_keys(Keys.RETURN)
                                actions.perform()

                                logging.info("Refund keystrokes have been sent")

                                try:
                                    # Wait up to 20 seconds for the 'back to subscription' and 'resubscribe' buttons
                                    # to become present and clickable. If this happens in this code block (after the
                                    # keystrokes have been sent) it will indicate that the subscription was
                                    # correctly cancelled (and refund therefore issues).
                                    back_to_subscription_button = WebDriverWait(driver, 20).until(
                                        EC.element_to_be_clickable(
                                            (By.XPATH, '//span[contains(text(), "Back to subscription")]'))
                                    )

                                    resubscribe_button = WebDriverWait(driver, 20).until(
                                        EC.element_to_be_clickable(
                                            (By.XPATH, '//span[contains(text(), "Resubscribe")]'))
                                    )

                                    logging.info(
                                        "back to subscription' and 'refund' elements were located after refund "
                                        "keystrokes were sent. This account should be deactivated and refund issued")
                                    email_body = "Account has been deactivated and refund issued."

                                except TimeoutException:
                                    logging.info("Cancel with refund keystrokes were sent but the back to sub and "
                                                 "refund elements were not found. Something has gone wrong.")
                                    email_body = "cancel with refund keystrokes were sent but the back to sub and " \
                                                 "refund elements were not found. Something has gone wrong and this " \
                                                 "account might not be deactivated."

                            '''
                            # CODE IN CASE OF 'TURN ON RECURRING BILLING' (account has already been cancelled, but still
                            # has a cancel link)

                            try:
                                # wait up 10 seconds for the 'back to subscription' button to be present and clickable
                                back_to_subscription_button = WebDriverWait(driver, 20).until(
                                    EC.element_to_be_clickable(
                                        (By.XPATH, '//span[contains(text(), "Back to subscription")]'))
                                )
                                logging.info("Account %s cannot be deactivated, but recurring billing is turned off. "
                                             "Check the expiry date for this account.", email)
                                email_body = "Account cannot be deactivated, but recurring billing is turned off. " \
                                             "Check the expiry date for this account."

                            except TimeoutException:
                                # if the back to subscription button did not become present and clickable
                                logging.info("back to subscription button did not become present and clickable")
                                email_body = "Account has not been deactivated."
                            '''

                            # Close the browser window
                            logging.info("browser closed")

                        except TimeoutException:
                            # if the cancel button did not become present and clickable
                            logging.info(
                                "Cancel button did not become present and clickable for account %s. "
                                "Probably the account has already been deactivated.", email)
                            email_body = "Cancel button did not become present and clickable. Probably the account" \
                                         "has already been deactivated."

                    except TimeoutException:
                        # if the billing cancellation page did not load
                        logging.info("Billing cancellation page did not load for account %s", email)
                        email_body = "Billing cancellation page did not load. Account has not been deactivated"

            except TimeoutException:
                # if the main account page failed to load
                logging.info("main account page failed to load within 20 seconds." ""
                             "Account %s has not been deactivated", email)
                email_body = "main account page failed to load within 20 seconds. Account has not been deactivated"

            send_end_of_loop_email()
            logging.info("-----------------------------------------------------------------------------")
