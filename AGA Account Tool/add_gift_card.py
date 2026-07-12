import json
import time
from contextlib import contextmanager
from pathlib import Path

from selenium.common.exceptions import (
    NoSuchFrameException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

GIFT_CARD_FILE = Path(__file__).resolve().parent / "gift_card_codes.json"

CLOSE_BUTTON_XPATH = "//button[@aria-label='Close' and @title='Close']"
REDEEM_BUTTON_XPATH = "//button[@aria-label='Redeem a code' and @title='Redeem a code']"
REDEEM_INPUT_XPATH = "//input[@name='tokenString' and @aria-label='Enter 25-character code']"

NEXT_BUTTON_XPATH = (
    "//button[normalize-space()='Next' and @data-bi-dnt='true']"
    " | //button[@data-bi-dnt='true' and normalize-space()='Next']"
    " | //button[normalize-space()='Next']"
)

CONFIRM_BUTTON_XPATH = (
    "//button[normalize-space()='Confirm' and @data-bi-dnt='true']"
    " | //button[@data-bi-dnt='true' and normalize-space()='Confirm']"
    " | //button[normalize-space()='Confirm']"
)

OVERLAY_XPATH = "//div[contains(@class, 'modalOverlay')]"

THANK_YOU_CLOSE_XPATHS = [
    "//button[normalize-space()='Close']",
    "//button[contains(@class, 'ThankYouPage-module__heroButton')]",
    "//button[contains(@class, 'ThankYouPage-module__fontBold') and normalize-space()='Close']",
    "//button[contains(@class, 'Button-module__buttonBase') and normalize-space()='Close']",
]


def load_gift_card_data(logger):
    if not GIFT_CARD_FILE.exists():
        logger.error("Gift card file not found: %s", GIFT_CARD_FILE)
        return None

    try:
        with open(GIFT_CARD_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict) or "codes" not in data or not isinstance(data["codes"], list):
            logger.error("Gift card JSON has invalid structure. Expected {'codes': [...]} ")
            return None

        logger.info("Gift card JSON loaded successfully")
        return data

    except Exception as exc:
        logger.exception("Failed to load gift card JSON: %s", exc)
        return None


def save_gift_card_data(data, logger) -> bool:
    try:
        with open(GIFT_CARD_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info("Gift card JSON saved successfully")
        return True
    except Exception as exc:
        logger.exception("Failed to save gift card JSON: %s", exc)
        return False


def find_first_available_gift_card(gift_card_data):
    for card in gift_card_data.get("codes", []):
        if card.get("status") == "available":
            return card
    return None


def mark_code_as_used(gift_card_data, code_to_mark, logger) -> bool:
    for card in gift_card_data.get("codes", []):
        if card.get("code") == code_to_mark:
            card["status"] = "used"
            logger.info("Marked code as used: %s", code_to_mark)
            return save_gift_card_data(gift_card_data, logger)

    logger.warning("Could not find code to mark as used: %s", code_to_mark)
    return False


@contextmanager
def switch_to_frame(driver: WebDriver, iframe, logger):
    try:
        driver.switch_to.default_content()
        driver.switch_to.frame(iframe)
        yield
    finally:
        try:
            driver.switch_to.default_content()
        except Exception as exc:
            logger.info("Could not switch back to default content: %s", exc)


def get_iframes(driver: WebDriver):
    driver.switch_to.default_content()
    return driver.find_elements(By.TAG_NAME, "iframe")


def normalize_code(code: str) -> str:
    return code.replace("-", "").replace(" ", "").strip().upper()


def get_input_value(element) -> str:
    value = element.get_attribute("value")
    return value or ""


def clear_input_robustly(driver: WebDriver, element, logger) -> None:
    try:
        element.click()
        element.send_keys(Keys.CONTROL, "a")
        element.send_keys(Keys.DELETE)
        time.sleep(0.15)
        logger.info("Input cleared using Ctrl+A/Delete")
    except Exception as exc:
        logger.info("Robust clear failed, falling back to clear(): %s", exc)
        try:
            element.clear()
        except Exception as exc2:
            logger.info("Fallback clear() also failed: %s", exc2)
            try:
                driver.execute_script("arguments[0].value = '';", element)
                logger.info("Input cleared using JavaScript fallback")
            except Exception as exc3:
                logger.info("JavaScript clear fallback also failed: %s", exc3)


def type_text_slowly(element, text: str, delay: float = 0.03) -> None:
    for char in text:
        element.send_keys(char)
        time.sleep(delay)


def _safe_click(driver: WebDriver, element, logger, description: str) -> bool:
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.15)
    except Exception:
        pass

    try:
        element.click()
        logger.info("%s clicked with normal click", description)
        return True
    except Exception as exc:
        logger.info("%s normal click failed: %s", description, exc)

    try:
        driver.execute_script("arguments[0].click();", element)
        logger.info("%s clicked with JavaScript click", description)
        return True
    except Exception as exc:
        logger.info("%s JavaScript click failed: %s", description, exc)

    return False


def _button_enabled(element) -> bool:
    disabled_attr = element.get_attribute("disabled")
    aria_disabled = element.get_attribute("aria-disabled")
    class_attr = (element.get_attribute("class") or "").lower()

    return (
        disabled_attr is None
        and not (aria_disabled and aria_disabled.lower() == "true")
        and "disabled" not in class_attr
        and element.is_enabled()
    )


def find_iframe_containing_visible_xpath(driver: WebDriver, xpath: str, logger, timeout: float = 3):
    end_time = time.time() + timeout

    while time.time() < end_time:
        iframes = get_iframes(driver)
        logger.info("Searching %s iframes for visible xpath: %s", len(iframes), xpath)

        for idx, iframe in enumerate(iframes):
            try:
                with switch_to_frame(driver, iframe, logger):
                    elements = driver.find_elements(By.XPATH, xpath)
                    for el in elements:
                        try:
                            if el.is_displayed():
                                logger.info("Found visible xpath in iframe %s", idx)
                                return iframe
                        except StaleElementReferenceException:
                            continue

            except (NoSuchFrameException, StaleElementReferenceException) as exc:
                logger.info("Iframe %s became unavailable while searching: %s", idx, exc)
            except Exception as exc:
                logger.info("Error searching iframe %s: %s", idx, exc)

        time.sleep(0.1)

    driver.switch_to.default_content()
    logger.info("Did not find visible xpath in any iframe: %s", xpath)
    return None


def find_visible_element_default_or_iframes(driver: WebDriver, xpath: str, logger, timeout: float = 3):
    end_time = time.time() + timeout

    while time.time() < end_time:
        try:
            driver.switch_to.default_content()
            elements = driver.find_elements(By.XPATH, xpath)
            for el in elements:
                try:
                    if el.is_displayed():
                        logger.info("Found visible element in default content for xpath: %s", xpath)
                        return None, "default_content"
                except StaleElementReferenceException:
                    continue
        except Exception as exc:
            logger.info("Error searching default content for xpath %s: %s", xpath, exc)

        iframe = find_iframe_containing_visible_xpath(driver, xpath, logger, timeout=0.75)
        if iframe is not None:
            return iframe, "iframe"

        time.sleep(0.1)

    driver.switch_to.default_content()
    logger.info("Did not find visible element in default content or any iframe: %s", xpath)
    return None, None


def is_xpath_visible_default_or_iframes(driver: WebDriver, xpath: str, logger, timeout: float = 1.0) -> bool:
    _, location = find_visible_element_default_or_iframes(driver, xpath, logger, timeout=timeout)
    return location is not None


def click_close_button(driver, logger, iframe_index: int | None = None, timeout: int = 10) -> bool:
    if iframe_index is not None:
        try:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if 0 <= iframe_index < len(iframes):
                with switch_to_frame(driver, iframes[iframe_index], logger):
                    close_button = WebDriverWait(driver, timeout).until(
                        EC.presence_of_element_located((By.XPATH, CLOSE_BUTTON_XPATH))
                    )
                    if _safe_click(driver, close_button, logger, f"Close button in iframe {iframe_index}"):
                        return True
        except TimeoutException:
            logger.info("Close button was not found or not clickable in iframe %s", iframe_index)
        except Exception as exc:
            logger.info("Error clicking Close button in iframe %s: %s", iframe_index, exc)

    iframe = find_iframe_containing_visible_xpath(driver, CLOSE_BUTTON_XPATH, logger, timeout=timeout)
    if iframe is None:
        logger.info("Close button was not found in any iframe")
        return False

    try:
        with switch_to_frame(driver, iframe, logger):
            close_button = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, CLOSE_BUTTON_XPATH))
            )
            if _safe_click(driver, close_button, logger, "Close button"):
                logger.info("Close button clicked successfully")
                return True

        return False

    except TimeoutException:
        logger.info("Close button was not clickable")
        return False
    except Exception as exc:
        logger.info("Error clicking Close button: %s", exc)
        return False


def click_redeem_code_button(driver, logger, timeout: int = 15) -> bool:
    try:
        logger.info("Waiting for modal overlay to disappear")

        WebDriverWait(driver, timeout).until(
            EC.invisibility_of_element_located((By.XPATH, OVERLAY_XPATH))
        )

        logger.info("Overlay is gone, proceeding to click Redeem")

        redeem_button = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, REDEEM_BUTTON_XPATH))
        )

        if _safe_click(driver, redeem_button, logger, "'Redeem a code' button"):
            logger.info("'Redeem a code' button clicked successfully")
            return True

        return False

    except TimeoutException:
        logger.info("Overlay did not disappear or redeem button not clickable")
        return False
    except Exception as exc:
        logger.exception("Error clicking redeem button: %s", exc)
        return False


def enter_gift_card_code(
    driver,
    gift_card_code: str,
    logger,
    timeout: int = 10,
    max_attempts: int = 3,
) -> bool:
    for attempt in range(1, max_attempts + 1):
        logger.info("Attempt %s/%s to enter gift card code", attempt, max_attempts)

        iframe = find_iframe_containing_visible_xpath(
            driver,
            REDEEM_INPUT_XPATH,
            logger,
            timeout=timeout,
        )
        if iframe is None:
            logger.info("Could not find redeem input iframe")
            return False

        try:
            with switch_to_frame(driver, iframe, logger):
                code_input = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, REDEEM_INPUT_XPATH))
                )

                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", code_input)
                time.sleep(0.1)

                try:
                    code_input.click()
                except Exception:
                    pass

                clear_input_robustly(driver, code_input, logger)
                time.sleep(0.2)

                type_text_slowly(code_input, gift_card_code, delay=0.03)
                time.sleep(0.35)

                entered_value = get_input_value(code_input)
                logger.info("Gift card input value after typing: %r", entered_value)

                if normalize_code(entered_value) != normalize_code(gift_card_code):
                    logger.info(
                        "Gift card input value mismatch after typing. Expected %r, got %r",
                        gift_card_code,
                        entered_value,
                    )
                    continue

                code_input.send_keys(Keys.TAB)
                time.sleep(0.6)

                final_value = get_input_value(code_input)
                logger.info("Gift card input value after TAB/commit: %r", final_value)

                if normalize_code(final_value) == normalize_code(gift_card_code):
                    logger.info("Gift card code entered successfully and value persisted")
                    return True

                logger.info(
                    "Gift card code did not persist after commit. Expected %r, got %r",
                    gift_card_code,
                    final_value,
                )

        except TimeoutException:
            logger.info("Gift card redeem input was not found or not ready")
        except StaleElementReferenceException as exc:
            logger.info("Redeem input became stale while entering code: %s", exc)
        except Exception as exc:
            logger.info("Error entering gift card code: %s", exc)

        time.sleep(0.5)

    logger.info("Failed to enter gift card code after %s attempts", max_attempts)
    return False


def click_button_across_iframes(
    driver,
    logger,
    xpath: str,
    button_name: str,
    timeout: int = 10,
    max_attempts: int = 3,
) -> bool:
    for attempt in range(1, max_attempts + 1):
        logger.info("Attempt %s/%s to click %s", attempt, max_attempts, button_name)

        try:
            driver.switch_to.default_content()
            buttons = driver.find_elements(By.XPATH, xpath)
            for button in buttons:
                try:
                    if button.is_displayed():
                        if _safe_click(driver, button, logger, f"{button_name} in default content"):
                            logger.info("%s clicked successfully in default content", button_name)
                            return True
                except StaleElementReferenceException:
                    continue
        except Exception as exc:
            logger.info("Error clicking %s in default content: %s", button_name, exc)

        iframe = find_iframe_containing_visible_xpath(driver, xpath, logger, timeout=timeout)
        if iframe is None:
            logger.info("Could not find %s in any iframe", button_name)
            return False

        try:
            with switch_to_frame(driver, iframe, logger):
                button = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                if _safe_click(driver, button, logger, button_name):
                    logger.info("%s clicked successfully", button_name)
                    return True

        except TimeoutException:
            logger.info("%s was not clickable", button_name)
        except StaleElementReferenceException as exc:
            logger.info("%s became stale: %s", button_name, exc)
        except Exception as exc:
            logger.info("Error clicking %s: %s", button_name, exc)

        time.sleep(0.25)

    logger.info("Failed to click %s after %s attempts", button_name, max_attempts)
    return False


def click_button_default_or_iframes(
    driver,
    logger,
    xpath: str,
    button_name: str,
    timeout: int = 10,
    max_attempts: int = 3,
) -> bool:
    for attempt in range(1, max_attempts + 1):
        logger.info("Attempt %s/%s to click %s", attempt, max_attempts, button_name)

        target, location = find_visible_element_default_or_iframes(
            driver,
            xpath,
            logger,
            timeout=timeout,
        )

        if location is None:
            logger.info("Could not find %s in default content or any iframe", button_name)
            return False

        try:
            if location == "default_content":
                driver.switch_to.default_content()
                button = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                if _safe_click(driver, button, logger, f"{button_name} in default content"):
                    logger.info("%s clicked successfully in default content", button_name)
                    return True

            with switch_to_frame(driver, target, logger):
                button = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                if _safe_click(driver, button, logger, f"{button_name} in iframe"):
                    logger.info("%s clicked successfully in iframe", button_name)
                    return True

        except TimeoutException:
            logger.info("%s was not clickable", button_name)
        except StaleElementReferenceException as exc:
            logger.info("%s became stale: %s", button_name, exc)
        except Exception as exc:
            logger.info("Error clicking %s: %s", button_name, exc)

        time.sleep(0.25)

    logger.info("Failed to click %s after %s attempts", button_name, max_attempts)
    return False


def wait_for_next_enabled(driver, logger, timeout: float = 6.0, poll_interval: float = 0.15) -> bool:
    """
    Wait until the visible Next button becomes enabled.
    Checks state while still inside the frame where the button exists.
    """
    end_time = time.time() + timeout

    while time.time() < end_time:
        try:
            driver.switch_to.default_content()
            buttons = driver.find_elements(By.XPATH, NEXT_BUTTON_XPATH)

            for button in buttons:
                try:
                    if not button.is_displayed():
                        continue

                    enabled = _button_enabled(button)
                    logger.info("Next button seen in default content | enabled=%s", enabled)

                    if enabled:
                        logger.info("Next button is ENABLED in default content")
                        return True
                except StaleElementReferenceException:
                    continue

            iframes = get_iframes(driver)
            for idx, iframe in enumerate(iframes):
                try:
                    with switch_to_frame(driver, iframe, logger):
                        buttons = driver.find_elements(By.XPATH, NEXT_BUTTON_XPATH)

                        for button in buttons:
                            try:
                                if not button.is_displayed():
                                    continue

                                enabled = _button_enabled(button)
                                logger.info("Next button seen in iframe %s | enabled=%s", idx, enabled)

                                if enabled:
                                    logger.info("Next button is ENABLED in iframe %s", idx)
                                    return True
                            except StaleElementReferenceException:
                                continue

                except Exception as exc:
                    logger.info("Error checking iframe %s for Next enabled state: %s", idx, exc)

        except Exception as exc:
            logger.info("Error during Next enabled wait: %s", exc)
        finally:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass

        time.sleep(poll_interval)

    logger.info("Next did not become enabled within timeout")
    return False


def wait_for_confirm_visible(driver, logger, timeout: float = 8.0, poll_interval: float = 0.15) -> bool:
    end_time = time.time() + timeout

    while time.time() < end_time:
        if is_xpath_visible_default_or_iframes(driver, CONFIRM_BUTTON_XPATH, logger, timeout=0.4):
            logger.info("Confirm button became visible")
            return True

        time.sleep(poll_interval)

    logger.info("Confirm button did not become visible within timeout")
    return False


def wait_for_post_confirm_success(driver, logger, timeout: float = 10.0, poll_interval: float = 0.2) -> str:
    """
    Returns:
        'thank_you_close'     -> thank-you Close button appeared
        'confirm_disappeared' -> Confirm button disappeared after click
        'timeout'             -> no success condition observed
    """
    end_time = time.time() + timeout
    confirm_seen = False

    while time.time() < end_time:
        for xpath in THANK_YOU_CLOSE_XPATHS:
            if is_xpath_visible_default_or_iframes(driver, xpath, logger, timeout=0.35):
                logger.info("Thank-you Close button detected after Confirm")
                return "thank_you_close"

        if is_xpath_visible_default_or_iframes(driver, CONFIRM_BUTTON_XPATH, logger, timeout=0.35):
            confirm_seen = True
        elif confirm_seen:
            logger.info("Confirm button disappeared after Confirm click")
            return "confirm_disappeared"

        time.sleep(poll_interval)

    logger.info("Timed out waiting for thank-you Close or confirm disappearance")
    return "timeout"


def click_any_thank_you_close_button(driver, logger) -> bool:
    for xpath in THANK_YOU_CLOSE_XPATHS:
        if click_button_default_or_iframes(
            driver,
            logger,
            xpath,
            "Thank-you Close button",
            timeout=3,
            max_attempts=2,
        ):
            return True
    return False


def redeem_first_available_code(driver, logger, email) -> bool:
    gift_card_data = load_gift_card_data(logger)
    if not gift_card_data:
        return False

    while True:
        available_card = find_first_available_gift_card(gift_card_data)

        if not available_card:
            logger.info("No available gift cards remain for %s", email)
            return False

        gift_card_code = available_card["code"]
        logger.info("Selected gift card code: %s", gift_card_code)

        if not enter_gift_card_code(driver, gift_card_code, logger):
            logger.info("Failed to enter gift card code, marking as used and moving on: %s", gift_card_code)
            if not mark_code_as_used(gift_card_data, gift_card_code, logger):
                return False
            gift_card_data = load_gift_card_data(logger)
            if not gift_card_data:
                return False
            continue

        next_enabled = wait_for_next_enabled(
            driver,
            logger,
            timeout=6.0,
            poll_interval=0.15,
        )

        if not next_enabled:
            logger.info("Next did not become enabled after first entry, retrying same code once: %s", gift_card_code)

            if not enter_gift_card_code(driver, gift_card_code, logger, max_attempts=2):
                logger.info("Retry entry failed, marking code as used and trying next: %s", gift_card_code)
                if not mark_code_as_used(gift_card_data, gift_card_code, logger):
                    return False
                gift_card_data = load_gift_card_data(logger)
                if not gift_card_data:
                    return False
                continue

            next_enabled = wait_for_next_enabled(
                driver,
                logger,
                timeout=6.0,
                poll_interval=0.15,
            )

        if not next_enabled:
            logger.info(
                "Next still did not become enabled after retry. Marking code as used and trying next: %s",
                gift_card_code,
            )
            if not mark_code_as_used(gift_card_data, gift_card_code, logger):
                return False
            gift_card_data = load_gift_card_data(logger)
            if not gift_card_data:
                return False
            continue

        next_clicked = click_button_across_iframes(
            driver,
            logger,
            NEXT_BUTTON_XPATH,
            "Next button",
            timeout=8,
            max_attempts=4,
        )
        if not next_clicked:
            logger.info("Enabled Next was detected but click failed. Leaving code available and failing flow: %s", gift_card_code)
            return False

        if not wait_for_confirm_visible(driver, logger, timeout=8.0, poll_interval=0.15):
            logger.info("Confirm button did not appear after clicking Next for code: %s", gift_card_code)
            return False

        confirm_clicked = click_button_across_iframes(
            driver,
            logger,
            CONFIRM_BUTTON_XPATH,
            "Confirm button",
            timeout=8,
            max_attempts=5,
        )
        if not confirm_clicked:
            logger.info("Confirm button did not click successfully for code: %s", gift_card_code)
            return False

        post_confirm_state = wait_for_post_confirm_success(
            driver,
            logger,
            timeout=10.0,
            poll_interval=0.2,
        )

        if post_confirm_state == "thank_you_close":
            close_clicked = click_any_thank_you_close_button(driver, logger)
            if not close_clicked:
                logger.info(
                    "Thank-you Close button was detected but click failed; treating redemption as failed for code: %s",
                    gift_card_code,
                )
                return False

            if not mark_code_as_used(gift_card_data, gift_card_code, logger):
                logger.info("Code was redeemed but could not be marked as used: %s", gift_card_code)
                return False

            logger.info("Gift card redeemed successfully and thank-you page closed: %s", gift_card_code)
            return True

        if post_confirm_state == "confirm_disappeared":
            if not mark_code_as_used(gift_card_data, gift_card_code, logger):
                logger.info("Code was redeemed but could not be marked as used: %s", gift_card_code)
                return False

            logger.info(
                "Gift card redemption treated as successful because Confirm UI disappeared: %s",
                gift_card_code,
            )
            return True

        logger.info("No success condition was detected after Confirm for code: %s", gift_card_code)
        return False