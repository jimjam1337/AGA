from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time


URL = "https://www.everyday.com.au/gift-cards/xbox-gift-card-a4c483d1-99cb-4d30-8bea-dfa3948ed5d2"

EMAIL = "jim@activegamers.com.au"
PASSWORD = "AGA111222"


def click_span_text(driver, wait, text):
    xpath = f"//span[normalize-space()='{text}']"
    element = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    try:
        element.click()
    except:
        driver.execute_script("arguments[0].click();", element)


def set_quantity(driver, wait, qty="5"):
    qty_input = wait.until(EC.presence_of_element_located((By.ID, "quantity")))
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", qty_input)
    qty_input.clear()
    qty_input.send_keys(qty)


def handle_login_if_present(driver):
    wait = WebDriverWait(driver, 10)

    try:
        # Check if username field appears
        username = wait.until(EC.presence_of_element_located((By.ID, "username")))
        print("Login detected, entering credentials...")

        username.clear()
        username.send_keys(EMAIL)

        password = wait.until(EC.presence_of_element_located((By.ID, "password")))
        password.clear()
        password.send_keys(PASSWORD)
        password.send_keys(Keys.ENTER)

        # Wait briefly for login to complete (page change or element disappears)
        WebDriverWait(driver, 15).until(
            EC.any_of(
                EC.staleness_of(username),
                EC.invisibility_of_element(username)
            )
        )

        print("Login completed.")

    except TimeoutException:
        # Login not present, continue normally
        print("No login prompt detected.")


def run_once(driver):
    wait = WebDriverWait(driver, 30)

    driver.get(URL)

    # Handle login if it appears
    handle_login_if_present(driver)

    click_span_text(driver, wait, "Buy for myself")
    set_quantity(driver, wait, "5")
    click_span_text(driver, wait, "Go to payment")

    # Login can sometimes appear AFTER clicking payment
    handle_login_if_present(driver)

    print("Reached payment step. Stopping before Pay now for safety.")
    input("Press Enter to continue to next loop...")


def main():
    try:
        loops = int(input("How many times do you want to repeat? ").strip())
    except ValueError:
        print("Invalid number.")
        return

    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        for i in range(loops):
            print(f"\nStarting loop {i + 1} of {loops}")
            run_once(driver)
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()