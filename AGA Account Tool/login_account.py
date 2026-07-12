from pathlib import Path
import time

import pyautogui
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


XBOX_ULTIMATE_URL = (
    "https://www.xbox.com/en-AU/games/store/game-pass-premium/"
    "CFQ7TTC0P85B?rpid=cfq7ttc0khs0&ocid=PROD_AMC_Cons_MEEMG_Renew_XboxGPU"
)

FIDO_URL_PART = "https://login.microsoft.com/consumers/fido"
INTERRUPT_PASSKEY_ENROLL_URL_PART = "https://account.live.com/interrupt/passkey/enroll"
STAY_SIGNED_IN_URL_PART = "https://login.live.com/ppsecure"
TOU_URL_PART = "https://account.live.com/tou/accrue?"

BASE_DIR = Path(__file__).resolve().parent
ICONS_DIR = BASE_DIR / "icons"
PASSKEY_CANCEL_IMAGE = ICONS_DIR / "passkey_cancel.png"


def log_step(logger, message: str) -> None:
    logger.info(message)
    print(message)


def safe_click(
    driver: WebDriver,
    by: By,
    value: str,
    timeout: int,
    logger,
    step_name: str,
    retries: int = 3,
    use_js_fallback: bool = True,
) -> bool:
    for attempt in range(1, retries + 1):
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            element.click()
            log_step(logger, f"{step_name} clicked")
            return True

        except StaleElementReferenceException:
            log_step(
                logger,
                f"{step_name} became stale on attempt {attempt}/{retries}, retrying",
            )
            time.sleep(0.5)

        except ElementClickInterceptedException:
            log_step(
                logger,
                f"{step_name} click was intercepted on attempt {attempt}/{retries}",
            )

            if use_js_fallback:
                try:
                    element = driver.find_element(by, value)
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});",
                        element,
                    )
                    time.sleep(0.3)
                    driver.execute_script("arguments[0].click();", element)
                    log_step(logger, f"{step_name} clicked with JS fallback")
                    return True

                except Exception as js_exc:
                    logger.warning(
                        "JS fallback click failed for %s: %s",
                        step_name,
                        js_exc,
                    )

            time.sleep(0.5)

        except TimeoutException:
            log_step(logger, f"Timed out waiting for {step_name} to become clickable")
            return False

        except Exception as exc:
            logger.exception("Error clicking %s: %s", step_name, exc)
            print(f"Error clicking {step_name}: {exc}")
            return False

    log_step(logger, f"Failed to click {step_name} after {retries} attempts")
    return False


def safe_send_keys(
    driver: WebDriver,
    by: By,
    value: str,
    text: str,
    timeout: int,
    logger,
    field_name: str,
    submit_with_enter: bool = False,
    retries: int = 3,
) -> bool:
    for attempt in range(1, retries + 1):
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            element.clear()
            element.send_keys(text)

            if submit_with_enter:
                element.send_keys(Keys.RETURN)

            log_step(logger, f"{field_name} entered")
            return True

        except StaleElementReferenceException:
            log_step(
                logger,
                f"{field_name} field became stale on attempt {attempt}/{retries}, retrying",
            )
            time.sleep(0.5)

        except TimeoutException:
            log_step(logger, f"Timed out waiting for {field_name} field")
            return False

        except Exception as exc:
            logger.exception("Error entering %s: %s", field_name, exc)
            print(f"Error entering {field_name}: {exc}")
            return False

    log_step(logger, f"Failed to enter {field_name} after {retries} attempts")
    return False


def get_password_for_account(email: str, password: str, alternate_password: str) -> str:
    alternate_password_accounts = {
        "aga11@activegamers.com.au",
        "aga22@activegamers.com.au",
        "aga26@activegamers.com.au",
        "aga110@activegamers.com.au",
        "aga111@activegamers.com.au",
    }

    return alternate_password if email in alternate_password_accounts else password


def is_element_visible(driver: WebDriver, by: By, value: str) -> bool:
    elements = driver.find_elements(by, value)

    for element in elements:
        try:
            if element.is_displayed():
                return True
        except StaleElementReferenceException:
            continue

    return False


def is_no_account_error_visible(driver: WebDriver) -> bool:
    xpath = "//*[contains(text(), \"We couldn't find a Microsoft account\")]"
    return is_element_visible(driver, By.XPATH, xpath)


def is_password_field_visible(driver: WebDriver) -> bool:
    return is_element_visible(driver, By.ID, "passwordEntry")


def is_sign_in_another_way_visible(driver: WebDriver) -> bool:
    xpath = (
        "//a[@id='idA_PWD_SwitchToCredPicker' and "
        "contains(normalize-space(), 'Sign in another way')]"
    )
    return is_element_visible(driver, By.XPATH, xpath)


def is_other_ways_to_sign_in_visible(driver: WebDriver) -> bool:
    xpath = "//span[@role='button' and normalize-space()='Other ways to sign in']"
    return is_element_visible(driver, By.XPATH, xpath)


def is_use_your_password_visible(driver: WebDriver) -> bool:
    xpath = "//span[@role='button' and normalize-space()='Use your password']"
    return is_element_visible(driver, By.XPATH, xpath)


def is_cancel_button_visible(driver: WebDriver) -> bool:
    xpath = (
        "//button[@type='button' and @data-testid='secondaryButton' "
        "and normalize-space()='Cancel']"
    )
    return is_element_visible(driver, By.XPATH, xpath)


def is_stay_signed_in_no_visible(driver: WebDriver) -> bool:
    xpath = (
        "//button[@type='submit' and @data-testid='secondaryButton' "
        "and normalize-space()='No']"
    )
    return is_element_visible(driver, By.XPATH, xpath)


def is_skip_for_now_visible(driver: WebDriver) -> bool:
    xpath = (
        "//button[@type='button' and @data-testid='subtleButton' "
        "and normalize-space()='Skip for now']"
    )
    return is_element_visible(driver, By.XPATH, xpath)


def click_passkey_cancel_if_fido_page(driver: WebDriver, logger, timeout: int = 8) -> bool:
    try:
        WebDriverWait(driver, timeout).until(EC.url_contains(FIDO_URL_PART))
        log_step(logger, "FIDO/passkey page detected")

    except TimeoutException:
        log_step(logger, "FIDO/passkey page did not appear")
        return False

    def fido_page_still_active() -> bool:
        try:
            return FIDO_URL_PART in driver.current_url
        except Exception:
            return True

    def press_esc_and_check(label: str) -> bool:
        try:
            pyautogui.press("esc")
            log_step(logger, label)
            time.sleep(2)

            if not fido_page_still_active():
                log_step(logger, "Passkey popup dismissed with ESC")
                return True

        except Exception as exc:
            logger.warning("ESC fallback failed for passkey popup: %s", exc)

        return False

    # First attempt: Windows passkey dialogs often close cleanly with ESC.
    if press_esc_and_check("Pressed ESC to dismiss passkey popup"):
        return True

    if not PASSKEY_CANCEL_IMAGE.exists():
        log_step(logger, f"Passkey cancel image not found: {PASSKEY_CANCEL_IMAGE}")

        # Final fallback even if the image file is missing.
        if press_esc_and_check("Final ESC fallback sent for passkey popup"):
            return True

        return False

    try:
        time.sleep(3)

        for confidence in (0.8, 0.7, 0.6):
            region = pyautogui.locateOnScreen(
                str(PASSKEY_CANCEL_IMAGE),
                confidence=confidence,
            )

            if region is not None:
                x, y = pyautogui.center(region)
                pyautogui.click(x, y)
                log_step(
                    logger,
                    f"Passkey cancel button image clicked at confidence {confidence}",
                )
                time.sleep(2)

                if not fido_page_still_active():
                    log_step(logger, "Passkey popup dismissed with image click")
                    return True

                log_step(logger, "Image click was sent, but FIDO page is still active")
                break

        screenshot_path = f"debug_passkey_{int(time.time())}.png"
        pyautogui.screenshot(screenshot_path)
        log_step(
            logger,
            f"passkey_cancel.png was not found or did not dismiss the popup. Screenshot saved to {screenshot_path}",
        )

        # Final fallback after image search/click fails.
        if press_esc_and_check("Final ESC fallback sent for passkey popup"):
            return True

        return False

    except Exception as exc:
        logger.exception("Error clicking passkey cancel image: %s", exc)
        print(f"Error clicking passkey cancel image: {exc}")

        if press_esc_and_check("Final ESC fallback sent after passkey image error"):
            return True

        return False

def click_sign_in_another_way(driver: WebDriver, logger, timeout: int = 15) -> bool:
    xpath = (
        "//a[@id='idA_PWD_SwitchToCredPicker' and "
        "contains(normalize-space(), 'Sign in another way')]"
    )

    return safe_click(
        driver=driver,
        by=By.XPATH,
        value=xpath,
        timeout=timeout,
        logger=logger,
        step_name="'Sign in another way' link",
    )


def click_other_ways_to_sign_in(driver: WebDriver, logger, timeout: int = 15) -> bool:
    xpath = "//span[@role='button' and normalize-space()='Other ways to sign in']"

    return safe_click(
        driver=driver,
        by=By.XPATH,
        value=xpath,
        timeout=timeout,
        logger=logger,
        step_name="'Other ways to sign in' button",
    )


def click_use_your_password(driver: WebDriver, logger, timeout: int = 15) -> bool:
    clicked = safe_click(
        driver=driver,
        by=By.XPATH,
        value="//span[@role='button' and normalize-space()='Use your password']",
        timeout=timeout,
        logger=logger,
        step_name="'Use your password' button",
    )

    if not clicked:
        return False

    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "passwordEntry"))
        )
        log_step(logger, "Password field detected after clicking 'Use your password'")
        return True

    except TimeoutException:
        log_step(logger, "Password field did not appear after clicking 'Use your password'")
        return False


def click_interrupt_passkey_enroll_cancel(
    driver: WebDriver,
    logger,
    timeout: int = 15,
) -> bool:
    xpath = (
        "//button[@type='button' and @data-testid='secondaryButton' "
        "and normalize-space()='Cancel']"
    )

    return safe_click(
        driver=driver,
        by=By.XPATH,
        value=xpath,
        timeout=timeout,
        logger=logger,
        step_name="'Cancel' button on interrupt/passkey/enroll page",
    )


def click_post_fido_cancel_button(driver: WebDriver, logger, timeout: int = 15) -> bool:
    xpath = (
        "//button[@type='button' and @data-testid='secondaryButton' "
        "and normalize-space()='Cancel']"
    )

    return safe_click(
        driver=driver,
        by=By.XPATH,
        value=xpath,
        timeout=timeout,
        logger=logger,
        step_name="'Cancel' button after post-password FIDO",
    )


def click_stay_signed_in_no(driver: WebDriver, logger, timeout: int = 15) -> bool:
    xpath = (
        "//button[@type='submit' and @data-testid='secondaryButton' "
        "and normalize-space()='No']"
    )

    return safe_click(
        driver=driver,
        by=By.XPATH,
        value=xpath,
        timeout=timeout,
        logger=logger,
        step_name="'No' button on stay signed in page",
    )


def click_skip_for_now(driver: WebDriver, logger, timeout: int = 15) -> bool:
    xpath = (
        "//button[@type='button' and @data-testid='subtleButton' "
        "and normalize-space()='Skip for now']"
    )

    return safe_click(
        driver=driver,
        by=By.XPATH,
        value=xpath,
        timeout=timeout,
        logger=logger,
        step_name="'Skip for now' button",
    )


def handle_tou_page(driver: WebDriver, logger, timeout: int = 5) -> bool:
    try:
        WebDriverWait(driver, timeout).until(EC.url_contains(TOU_URL_PART))
        log_step(logger, "TOU page loaded")
        driver.get(XBOX_ULTIMATE_URL)
        log_step(logger, "TOU page was bypassed by loading the Xbox Ultimate page")
        return True

    except TimeoutException:
        return False


def handle_update_security_info_page(driver: WebDriver, logger, timeout: int = 3) -> bool:
    try:
        looks_good_field = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.ID, "iLooksGood"))
        )
        looks_good_field.send_keys(Keys.RETURN)
        log_step(logger, "Update security info window appeared and 'Looks good' was confirmed")
        return True

    except TimeoutException:
        return False


def handle_pre_password_state(driver: WebDriver, logger) -> bool | None:
    """
    Returns:
        True  -> password field is ready
        False -> hard failure
        None  -> handled something, continue looping
    """
    current_url = driver.current_url

    if is_no_account_error_visible(driver):
        log_step(logger, "Microsoft account does not exist error detected")
        return False

    if is_password_field_visible(driver):
        log_step(logger, "Password field is present and visible")
        return True

    if is_stay_signed_in_no_visible(driver):
        log_step(logger, "'No' button is visible during pre-password transition")
        if not click_stay_signed_in_no(driver, logger, timeout=15):
            log_step(logger, "Could not click 'No' during pre-password transition")
            return False
        time.sleep(1)
        return None

    if is_skip_for_now_visible(driver):
        log_step(logger, "'Skip for now' is visible during pre-password transition")
        if not click_skip_for_now(driver, logger, timeout=15):
            log_step(logger, "Could not click 'Skip for now' during pre-password transition")
            return False
        time.sleep(1)
        return None

    if FIDO_URL_PART in current_url:
        log_step(logger, "FIDO/passkey page detected during pre-password transition")
        if not click_passkey_cancel_if_fido_page(driver, logger, timeout=8):
            log_step(logger, "FIDO page appeared but passkey cancel could not be clicked")
            return False
        time.sleep(1)
        return None

    if INTERRUPT_PASSKEY_ENROLL_URL_PART in current_url:
        log_step(logger, "Interrupt/passkey/enroll page detected during pre-password transition")
        if not click_interrupt_passkey_enroll_cancel(driver, logger, timeout=15):
            log_step(logger, "Could not click interrupt/passkey/enroll Cancel button")
            return False
        time.sleep(1)
        return None

    if is_other_ways_to_sign_in_visible(driver):
        log_step(logger, "'Other ways to sign in' is visible during pre-password transition")
        if not click_other_ways_to_sign_in(driver, logger, timeout=15):
            log_step(logger, "Could not click 'Other ways to sign in'")
            return False
        time.sleep(1)
        return None

    if is_sign_in_another_way_visible(driver):
        log_step(logger, "'Sign in another way' is visible during pre-password transition")
        if not click_sign_in_another_way(driver, logger, timeout=15):
            log_step(logger, "Could not click 'Sign in another way'")
            return False
        time.sleep(1)
        return None

    if is_use_your_password_visible(driver):
        log_step(logger, "'Use your password' is visible during pre-password transition")
        if not click_use_your_password(driver, logger, timeout=15):
            log_step(logger, "Could not click 'Use your password'")
            return False
        time.sleep(1)
        return None

    return None


def advance_login_until_password_field(driver: WebDriver, logger, timeout: int = 30) -> bool:
    end_time = time.time() + timeout

    while time.time() < end_time:
        result = handle_pre_password_state(driver, logger)

        if result is True:
            return True

        if result is False:
            return False

        time.sleep(0.5)

    log_step(
        logger,
        f"Timed out advancing login flow before password field appeared. Current URL: {driver.current_url}",
    )
    return False


def resubmit_password_if_still_on_password_page(driver: WebDriver, logger) -> bool | None:
    """
    Sometimes Microsoft keeps the password field visible after Enter is sent.
    This resubmits once per loop instead of clicking credential-picker options again.
    """
    if not is_password_field_visible(driver):
        return None

    try:
        password_field = driver.find_element(By.ID, "passwordEntry")
        password_field.send_keys(Keys.RETURN)
        log_step(logger, "Password field is still visible after submission; pressed Enter again")
        time.sleep(2)
        return None

    except Exception as exc:
        logger.exception("Could not resubmit password field: %s", exc)
        return False


def handle_post_password_state(driver: WebDriver, logger) -> bool | None:
    """
    Returns:
        True  -> login flow finished
        False -> hard failure
        None  -> handled something or waiting, continue looping

    Important:
        Do not click 'Other ways to sign in', 'Sign in another way', or
        'Use your password' after password submission. Those are pre-password
        credential-picker actions and can cause an infinite loop.
    """
    current_url = driver.current_url

    if is_no_account_error_visible(driver):
        log_step(logger, "Microsoft account does not exist error detected after password")
        return False

    if XBOX_ULTIMATE_URL in current_url:
        if is_cancel_button_visible(driver):
            log_step(logger, "Xbox page reached with Cancel button visible")
            if not click_post_fido_cancel_button(driver, logger, timeout=10):
                return False
            time.sleep(1)
            return None

        log_step(logger, "Final Xbox Ultimate URL reached")
        return True

    if is_stay_signed_in_no_visible(driver):
        log_step(logger, "'No' button is visible during post-password transition")
        if not click_stay_signed_in_no(driver, logger, timeout=15):
            log_step(logger, "Could not click 'No' on stay signed in page")
            return False
        time.sleep(1)
        return None

    if is_skip_for_now_visible(driver):
        log_step(logger, "'Skip for now' is visible during post-password transition")
        if not click_skip_for_now(driver, logger, timeout=15):
            log_step(logger, "Could not click 'Skip for now' during post-password transition")
            return False
        time.sleep(1)
        return None

    if STAY_SIGNED_IN_URL_PART in current_url:
        log_step(logger, "Stay signed in URL detected during post-password transition")
        if not click_stay_signed_in_no(driver, logger, timeout=15):
            log_step(logger, "Could not click 'No' on stay signed in page")
            return False
        time.sleep(1)
        return None

    if FIDO_URL_PART in current_url:
        log_step(logger, "FIDO/passkey page detected after password submission")
        if not click_passkey_cancel_if_fido_page(driver, logger, timeout=8):
            log_step(logger, "Post-password FIDO page appeared but passkey cancel could not be clicked")
            return False
        time.sleep(1)
        return None

    if INTERRUPT_PASSKEY_ENROLL_URL_PART in current_url:
        log_step(logger, "Interrupt/passkey/enroll page detected after password submission")
        if not click_interrupt_passkey_enroll_cancel(driver, logger, timeout=15):
            log_step(logger, "Could not click interrupt/passkey/enroll Cancel button after password")
            return False
        time.sleep(1)
        return None

    if handle_tou_page(driver, logger):
        time.sleep(1)
        return None

    if handle_update_security_info_page(driver, logger):
        time.sleep(1)
        return None

    password_resubmit_result = resubmit_password_if_still_on_password_page(driver, logger)
    if password_resubmit_result is False:
        return False

    return None


def advance_login_after_password(driver: WebDriver, logger, timeout: int = 45) -> bool:
    end_time = time.time() + timeout

    while time.time() < end_time:
        result = handle_post_password_state(driver, logger)

        if result is True:
            return True

        if result is False:
            return False

        time.sleep(1)

    log_step(
        logger,
        f"Timed out waiting for final Xbox page after password. Current URL: {driver.current_url}",
    )
    return False


def login_full_flow(
    driver: WebDriver,
    email: str,
    password: str,
    alternate_password: str,
    logger,
) -> bool:
    log_step(logger, f"Begin login sequence for {email}")

    try:
        driver.set_window_size(1920, 1080)
        driver.maximize_window()
        driver.set_page_load_timeout(30)
        driver.get(XBOX_ULTIMATE_URL)
        log_step(logger, "Xbox Ultimate page loaded")

        sign_in_clicked = safe_click(
            driver=driver,
            by=By.CSS_SELECTOR,
            value="uhf-mecontrol[sign-in-label='Sign in']",
            timeout=20,
            logger=logger,
            step_name="'Sign in' control",
        )
        if not sign_in_clicked:
            return False

        email_entered = safe_send_keys(
            driver=driver,
            by=By.ID,
            value="usernameEntry",
            text=email,
            timeout=20,
            logger=logger,
            field_name="Email",
            submit_with_enter=True,
        )
        if not email_entered:
            return False

        transition_success = advance_login_until_password_field(driver, logger, timeout=30)
        if not transition_success:
            return False

        selected_password = get_password_for_account(email, password, alternate_password)

        password_entered = safe_send_keys(
            driver=driver,
            by=By.ID,
            value="passwordEntry",
            text=selected_password,
            timeout=20,
            logger=logger,
            field_name="Password",
            submit_with_enter=True,
        )
        if not password_entered:
            return False

        post_password_success = advance_login_after_password(driver, logger, timeout=45)
        if not post_password_success:
            return False

        try:
            WebDriverWait(driver, 10).until(EC.url_contains(XBOX_ULTIMATE_URL))
            log_step(logger, f"login_full_flow completed successfully for {email}")
            return True

        except TimeoutException:
            log_step(logger, f"Timed out waiting for final Xbox renew page for {email}")
            log_step(logger, f"Current URL after login attempt: {driver.current_url}")
            log_step(logger, f"Current page title after login attempt: {driver.title}")
            return False

    except Exception as exc:
        logger.exception("Unhandled error in login_full_flow for %s: %s", email, exc)
        print(f"Unhandled error in login_full_flow for {email}: {exc}")
        return False
