from pathlib import Path
import time

import pyautogui
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

RENEW_URL = (
    "https://www.xbox.com/en-AU/games/store/game-pass-premium/"
    "CFQ7TTC0P85B?rpid=cfq7ttc0khs0&ocid=PROD_AMC_Cons_MEEMG_Renew_XboxGPU"
)

MANAGE_BUTTON_XPATH = '//*[@id="PageContent"]/div/div[1]/div[1]/div[6]/div/div[1]/a'
JOIN_BUTTON_XPATH = "//button[contains(@aria-label, 'Join')]"
XBOX_APP_TEXT_XPATH = "//p[text()='Launch or install Xbox PC app']"

BASE_DIR = Path(__file__).resolve().parent
ICONS_DIR = BASE_DIR / "icons"
SUBSCRIBE_BUTTON_IMAGE = ICONS_DIR / "subscribe_button.png"


def record_failed_account(run_entry, email, reason) -> None:
    run_entry["failed_accounts"].append({
        "email": email,
        "reason": reason,
    })


def load_page_with_timeout(
        driver,
        url: str,
        timeout: int,
        logger,
        email: str,
        run_entry,
        failure_reason: str,
) -> bool:
    driver.set_page_load_timeout(timeout)

    try:
        driver.get(url)
        return True

    except TimeoutException:
        logger.info(failure_reason)
        record_failed_account(run_entry, email, failure_reason)
        return False


def load_renew_page(driver, email: str, logger, run_entry) -> bool:
    success = load_page_with_timeout(
        driver=driver,
        url=RENEW_URL,
        timeout=20,
        logger=logger,
        email=email,
        run_entry=run_entry,
        failure_reason="Xbox renew page did not load within 20 seconds",
    )

    if success:
        logger.info("load_renew_page completed. Loaded Game Pass renew page.")

    return success


def click_join_button(driver, logger, timeout: int = 30) -> bool:
    """
    Try to click Join. If not found, refresh once and try again.
    """
    try:
        join_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, JOIN_BUTTON_XPATH))
        )
        join_button.send_keys(Keys.RETURN)
        logger.info("click_join_button completed. Join button appeared and was clicked.")
        return True

    except TimeoutException:
        logger.info(
            "click_join_button completed. Join button was not found. Will refresh the page."
        )

    try:
        driver.get(RENEW_URL)

        join_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, JOIN_BUTTON_XPATH))
        )
        join_button.send_keys(Keys.RETURN)
        logger.info(
            "click_join_button completed. Join button appeared and was clicked after refresh."
        )
        return True

    except TimeoutException:
        logger.info(
            "click_join_button completed. Join button was not found after refresh."
        )
        return False


def handle_passkey_interrupt_page_2(driver, logger) -> bool:
    """
    If the second passkey interrupt page appears, bypass it by loading the renewal URL again.
    """
    try:
        WebDriverWait(driver, 10).until(
            EC.url_contains("/interrupt/passkey")
        )

        driver.get(RENEW_URL)
        logger.info(
            "handle_passkey_interrupt_page_2 completed. "
            "Second passkey interrupt page appeared and was bypassed."
        )
        return True

    except TimeoutException:
        logger.info(
            "handle_passkey_interrupt_page_2 completed. "
            "Second passkey interrupt page did not appear."
        )
        return False


def click_account_selection_button(driver, logger) -> bool:
    """
    Wait for the login/live authorization URL and return True if found.
    """
    try:
        WebDriverWait(driver, 15).until(
            EC.url_contains("https://login.live.com/oauth20_authorize.srf")
        )
        logger.info(
            "click_account_selection_button completed. "
            "Account selection/login authorize page was found."
        )
        return True

    except TimeoutException:
        logger.info(
            "click_account_selection_button completed. "
            "Account selection/login authorize page was not found."
        )
        return False


def find_manage_button(driver, logger, timeout: int = 5) -> bool:
    """
    Return True if the Manage button is found and clickable.
    This means the account is already activated.
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, MANAGE_BUTTON_XPATH))
        )
        logger.info("Manage button found. Account is already activated.")
        return True

    except TimeoutException:
        logger.info("Manage button not found. Account appears inactive.")
        return False


def wait_for_xbox_app_confirmation(driver, email: str, logger, timeout: int = 20) -> bool:
    """
    Wait for the post-subscription confirmation element to appear.
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, XBOX_APP_TEXT_XPATH))
        )
        logger.info(
            "Launch or install Xbox PC app element found. "
            "Account reactivation is complete for %s",
            email,
        )
        return True

    except TimeoutException:
        logger.info(
            "Launch or install Xbox PC app element was not found for %s. "
            "Check whether the account has a valid payment method.",
            email,
        )
        return False


def locate_and_click_subscribe_button(
        logger,
        image_path: Path,
        confidence: float = 0.7,
        pause_seconds: float = 1.0,
) -> bool:
    """
    Find the subscribe button on screen and click it twice.
    Returns True if successful, False otherwise.
    """
    if not image_path.exists():
        logger.error("Subscribe button image not found: %s", image_path)
        return False

    try:
        subscribe_button_position = pyautogui.locateOnScreen(
            str(image_path),
            confidence=confidence,
        )

        if subscribe_button_position is None:
            logger.info("Subscribe button image was not found on screen.")
            return False

        icon_x, icon_y = pyautogui.center(subscribe_button_position)

        pyautogui.click(icon_x, icon_y)
        time.sleep(pause_seconds)
        pyautogui.click(icon_x, icon_y)

        logger.info("Subscribe button image found and clicked successfully.")
        return True

    except Exception as exc:
        logger.exception("Error locating/clicking subscribe button: %s", exc)
        return False


def send_activation_success_email(email, user_choice, send_end_of_loop_email) -> None:
    """
    Send the completion email for a successfully activated account.
    """
    email_body = f"Account {email} has been activated"
    send_end_of_loop_email(email, email_body, user_choice)


def perform_subscription_flow(
        driver,
        email,
        *,
        logger,
        run_entry,
        user_choice,
        send_end_of_loop_email,
) -> bool:
    renew_loaded = load_renew_page(driver, email, logger, run_entry)
    if not renew_loaded:
        return False

    join_clicked = click_join_button(driver, logger)
    if not join_clicked:
        reason = "Join button was not found, including after refresh."
        logger.info("%s Account: %s", reason, email)
        record_failed_account(run_entry, email, reason)
        return False

    logger.info("Waiting 15 seconds to allow the subscribe modal to load.")
    time.sleep(15)

    subscribe_clicked = locate_and_click_subscribe_button(
        logger=logger,
        image_path=SUBSCRIBE_BUTTON_IMAGE,
    )

    if not subscribe_clicked:
        reason = "Subscribe button not found or could not be clicked."
        logger.info("%s Account: %s", reason, email)
        record_failed_account(run_entry, email, reason)
        return False

    activated = wait_for_xbox_app_confirmation(
        driver=driver,
        email=email,
        logger=logger,
    )

    if not activated:
        reason = (
            "Launch or install Xbox PC app element did not appear. "
            "Check whether the account has a valid payment method "
            "(may need gift code conversion)."
        )
        record_failed_account(run_entry, email, reason)
        return False

    send_activation_success_email(
        email=email,
        user_choice=user_choice,
        send_end_of_loop_email=send_end_of_loop_email,
    )
    time.sleep(15)
    return True


def activate_account_flow(
        driver,
        email,
        password,
        alternate_password,
        *,
        logger,
        run_entry,
        user_choice,
        login_full_flow,
        send_end_of_loop_email,
) -> bool:
    """
    Main activation flow.

    If the Manage button is found, the account is already active and
    subscription steps are skipped.
    """
    logger.info("Activation loop initiated for %s", email)

    try:
        login_full_flow(driver, email, password, alternate_password)

        renew_loaded = load_renew_page(driver, email, logger, run_entry)
        if not renew_loaded:
            return False

        handle_passkey_interrupt_page_2(driver, logger)
        click_account_selection_button(driver, logger)

        if find_manage_button(driver, logger):
            logger.info(
                "Account %s is already active. Skipping subscription flow.",
                email,
            )
            return True

        success = perform_subscription_flow(
            driver,
            email,
            logger=logger,
            run_entry=run_entry,
            user_choice=user_choice,
            send_end_of_loop_email=send_end_of_loop_email,
        )

        if success:
            logger.info("Subscription flow completed successfully for %s", email)
        else:
            logger.info("Subscription flow failed for %s", email)

        return success

    except Exception as exc:
        logger.exception("Unhandled error during activation flow for %s: %s", email, exc)
        record_failed_account(run_entry, email, f"Unhandled activation flow error: {exc}")
        return False

    finally:
        logger.info("-----------------------------------------------------------------------------")
