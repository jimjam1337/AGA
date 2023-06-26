import time
import tkinter as tk
from tkinter import simpledialog  # Add this line
import logging
import pyautogui
import os
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# Set up logging to write to /logs/aga/account tool
dir_path = 'C:/logs/aga/account tool'
if not os.path.exists(dir_path):
    os.makedirs(dir_path)
logging.basicConfig(filename='/logs/aga/account tool/selenium.log', level=logging.INFO)


# CODE FOR DIALOGUE BOX

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


root = tk.Tk()
root.title("AGA GamePass Account Tool")

# Load the background image
bg_image = tk.PhotoImage(file="c:\\AGALogoV4.png")

# Create a label with the background image
bg_label = tk.Label(root, image=bg_image)
bg_label.image = bg_image  # Store the PhotoImage object as an attribute of the label
bg_label.place(x=0, y=-20, relwidth=1, relheight=1)

# Adjust the size of the window to fit the graphic
root.geometry(f"{bg_image.width() + 75}x{bg_image.height() + 50}")

Reactivate_button = tk.Button(root, text="Reactivate", command=set_result_reactivate)
Reactivate_button.place(relx=0.2, rely=0.5, anchor="center")

deactivate_button = tk.Button(root, text="Deactivate", command=set_result_deactivate)
deactivate_button.place(relx=.5, rely=0.5, anchor="center")

setup_button = tk.Button(root, text="Setup", command=set_result_setup)
setup_button.place(relx=.7, rely=0.5, anchor="center")

root.mainloop()

# DIALOGUE BOX ENDS

# DEFINE LOGIN FUNCTION BEGINS

def Login_Function():
    print("begin login sequence")

    # Create a new instance of the Chrome driver
    driver = webdriver.Chrome()
    print("driver opened")

    # Navigate to the Microsoft login page
    driver.get("https://account.microsoft.com/")

    # Wait for the first signin field to be present and clickable
    signin_field = WebDriverWait(driver, 500).until(
        EC.element_to_be_clickable((By.ID, "id__4"))
    )
    print("first signin field clickable")

    # Click the email field
    signin_field.click()

    # Wait for the email field to be present and clickable
    email_field = WebDriverWait(driver, 500).until(
        EC.element_to_be_clickable((By.ID, "i0116"))
    )
    print("second email field clickable")

    # Send the email to the email field
    email_field.send_keys(email)
    email_field.send_keys(Keys.RETURN)

    print("email sent")

    # Wait for the password field to be present and clickable
    password_field = WebDriverWait(driver, 500).until(
        EC.element_to_be_clickable((By.ID, "i0118"))
    )

    print("password field clickable")

    # Send the password to the email field
    password_field.send_keys(password)
    password_field.send_keys(Keys.RETURN)

    print("password sent")

    # CODE IN CASE UPDATE SECURITY INFO PAGE LOADS (case1)

    try:
        # Check if the 'iLooksGood' element is present and clickable
        looks_good_field = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "iLooksGood")))
        # if the element is clickable, send enter to the looks good field
        looks_good_field.send_keys(Keys.RETURN)
        logging.info("update security info window appeared and was bypassed")
    except TimeoutException:
        logging.info("update security info window did not appear")

    # CODE IN CASE PRIVACY NOTICE PAGE LOADS (case2)

    try:
        # Waiting up to 10 seconds for the privacy notice page to load
        WebDriverWait(driver, 10).until(EC.url_contains("https://privacynotice.account.microsoft.com/"))
        logging.info("Waiting to see if privacy notice page appears")

        # if URL contains "https://privacynotice.account.microsoft.com/", bypass and go to the main account page
        driver.get("https://account.microsoft.com/")
        logging.info(
            "privacy notice page 'https://privacynotice.account.microsoft.com/' appeared and was bypassed")

    except TimeoutException:
        # if the URL does not contain "https://privacynotice.account.microsoft.com/"
        logging.info("privacy notice page 'https://privacynotice.account.microsoft.com/' did not appear")

    # CODE IN CASE BREAK FREE OF YOUR PASSWORDS (UPSELL) PAGE LOADS (case3)

    try:
        # waiting for up to 10 seconds to see if the break free of your passwords page loads
        WebDriverWait(driver, 10).until(EC.url_contains("https://account.live.com/apps/upsell?"))

        # if the URL contains "https://account.live.com/apps/upsell?", skip it and go to the main account page
        driver.get("https://account.microsoft.com/")
        logging.info("Upsell page 'https://account.live.com/apps/upsell?' appeared and was bypassed")

    except TimeoutException:
        # if the URL does not contain "https://account.live.com/apps/upsell?"
        logging.info("Upsell page 'https://account.live.com/apps/upsell?' did not appear")

    # CODE IN CASE STAY SIGNED IN WINDOW APPEARS (case4)

    try:
        # Wait for the 'stayed signed in? no' field to be present and clickable
        staysignedin_no_field = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "idBtn_Back"))
        )

        # send enter to the 'stay signed in? no' field
        staysignedin_no_field.send_keys(Keys.RETURN)

        logging.info("stay signed in window appeared and was completed")

    except TimeoutException:
        logging.info("stay signed in window did not appear")

        # CODE IN CASE SECOND PRIVACY NOTICE PAGE LOADS (case5)

    try:
        # Waiting up to 10 seconds for the privacy notice page to load
        WebDriverWait(driver, 10).until(EC.url_contains("https://privacynotice.account.microsoft.com/"))
        logging.info("Waiting to see if privacy notice page appears")

        # if URL contains "https://privacynotice.account.microsoft.com/", bypass and go to the main account page
        driver.get("https://account.microsoft.com/")
        logging.info(
            "second privacy notice page 'https://privacynotice.account.microsoft.com/' appeared and was bypassed")

    except TimeoutException:
        # if the URL does not contain "https://privacynotice.account.microsoft.com/"
        logging.info("second privacy notice page 'https://privacynotice.account.microsoft.com/' did not appear")

    print("login function completed")
    logging.info("login function completed within login function")

# DEFINE LOGIN FUNCTION ENDS

logging.info("Beginning login function")
print("login function defined")

# DEFINE THE BASE EMAIL AND PASSWORD
email_base = ["aga", "agapc"]
password = "AGA111222"
# Ask for the starting and ending values of the ranges
start_value_1 = simpledialog.askinteger("Input", "Enter the starting value for Xbox accounts [1]")
# Use the default value if the user didn't enter anything
if not start_value_1:
    start_value_1 = 1
end_value_1 = simpledialog.askinteger("Input", "Enter the ending value for Xbox accounts [104]")
# Use the default value if the user didn't enter anything
if not end_value_1:
    end_value_1 = 104
start_value_2 = simpledialog.askinteger("Input", "Enter the starting value for PC accounts [1]")
# Use the default value if the user didn't enter anything
if not start_value_2:
    start_value_2 = 1
end_value_2 = simpledialog.askinteger("Input", "Enter the ending value for PC accounts [24]")
# Use the default value if the user didn't enter anything
if not end_value_2:
    end_value_2 = 24

ranges = [(start_value_1, end_value_1), (start_value_2, end_value_2)]

print("define base email and password finished")
logging.info("define base email and password finished")

# Loop through each base email and range
for email_base, r in zip(email_base, ranges):
    # Loop through each account
    for i in range(*r):
        # Create the email address
        email = email_base + str(i) + "@activegamers.com.au"

        # log which account will be deactivated based on email variable
        logging.info('Beginning deactivation of account %s', email)

# REACTIVATE CODE
if result == "Reactivate":
    print("Reactivate loop initiated")

    Login_Function()
    print("login function completed outside login function")
    logging.info("login function completed outside login function")

    # Navigate to the subscriptions page
    driver.get(
        "https://www.xbox.com/en-au/games/store/xbox-game-pass-ultimate/cfq7ttc0khs0?=&OCID=PROD_AMC_Cons_MEEMG_Renew_XboxGPU&rtc=1")

    time.sleep(10)

    print("getting focus")

    # Get focus on the subscriptions page window

    reactivate_join_now_icon = "C:/Users/james/Dropbox/Active Gamers Australia USE THIS/Jim's Tech Folder/Python/pythonProject_gp activate/icons/reactivate_join_now.PNG"

    # Search for the icon on the screen
    reactivate_join_now_pos = pyautogui.locateOnScreen(reactivate_join_now_icon, confidence=0.5)

    # If the icon is found, click it to bring the window to focus
    if reactivate_join_now_pos is not None:
        reactivate_join_now_center = pyautogui.center(reactivate_join_now_pos)
        pyautogui.click(reactivate_join_now_center)
    else:
        print("Icon not found")

    print("subscriptions page loaded")

    # Wait for the join button to be present & clickable
    # join_button = WebDriverWait(driver, 15).until(
    #    EC.element_to_be_clickable((By.CSS_SELECTOR,
    #                                "#PageContent > div > div:nth-child(1) > div.ModuleContainer-module__container___pkhPl.ProductDetailsHeader-module__container___zvKSX > div.FadeContainers-module__fadeIn___5xlsD.FadeContainers-module__widthInherit___5fuOa > div > div:nth-child(1) > button"))
    # )
    # print("join button found")

    # join_button.click()

    # print("join button clicked")

    time.sleep(5)

    # Wait for the Purchase iframe to be present & clickable
    purchase_iframe = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH, '//iframe[@title="Purchase Frame"]'))
    )

    print("purchase iframe clickable")

    pyautogui.press('enter')

    print("enter clicked (hopefully on sub button)")

    time.sleep(30)

    # script needs to confirm that susbcription has been usccessful at this point - could search for 'thank for joining' text

    print(email + " completed")

    # DEACTIVATE CODE
    if result == "Deactivate":
        print("Deactivate")

        logging.info("Now beginning deactivation process")

        Login_Function()

        driver = webdriver.Chrome()

        try:
            # Wait for the manage link to be present and clickable
            manage_link = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Manage"))
            )

            # send enter to the manage link
            manage_link.send_keys(Keys.RETURN)

            # Wait for the first cancel link to be present and clickable
            cancel_link1 = WebDriverWait(driver, 500).until(
                EC.element_to_be_clickable((By.ID, "cancel-sub-button"))
            )

            print("cancel link 1 found")

            # Use JavaScript to click the cancel link
            driver.execute_script("arguments[0].click();", cancel_link1)

            print("cancel link 1 clicked")

            # Wait for the second cancel link (cancel button) to be present and clickable
            cancel_link2 = WebDriverWait(driver, 500).until(
                EC.element_to_be_clickable((By.ID, "benefit-cancel"))
            )

            print("cancel link 2 found")

            # Use JavaScript to click the second cancel link
            driver.execute_script("arguments[0].click();", cancel_link2)

            # print message to indicate that second cancel link has been clicked
            print("cancel link 2 clicked")

            time.sleep(5)

            actions = ActionChains(driver)
            actions.send_keys(Keys.ARROW_DOWN)
            print("down arrow sent")
            actions.send_keys(Keys.TAB)
            print("tab  sent")
            actions.send_keys(Keys.RETURN)
            print("return sent")
            actions.perform()

            # Close the browser window
            driver.close()

            print("browser closed")

            # log the completed deactivation for the account
            logging.info('Account %s has been completed', email)
            logging.info("---------------------------------------------------------")

        except TimeoutException:
            logging.info("Manage link for %s did not become clickable - probably the account is already deactivated")
            logging.info("---------------------------------------------------------")
