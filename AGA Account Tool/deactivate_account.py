import time

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from login_account import login_full_flow


ACCOUNT_CHECKUP_URL_PART = "https://account.microsoft.com/account-checkup"
ACCOUNT_HOME_URL = "https://account.microsoft.com/"


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
    js_fallback: bool = True,
) -> bool:
    for attempt in range(1, retries + 1):
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )

            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                element,
            )
            time.sleep(0.3)

            element.click()
            log_step(logger, f"{step_name} clicked")
            return True

        except ElementClickInterceptedException:
            log_step(
                logger,
                f"{step_name} click intercepted on attempt {attempt}/{retries}",
            )

            if js_fallback:
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
                    logger.warning("JS fallback failed for %s: %s", step_name, js_exc)

            time.sleep(0.5)

        except StaleElementReferenceException:
            log_step(
                logger,
                f"{step_name} became stale on attempt {attempt}/{retries}, retrying",
            )
            time.sleep(0.5)

        except TimeoutException:
            log_step(logger, f"Timed out waiting for {step_name}")
            return False

        except Exception as exc:
            logger.exception("Failed clicking %s: %s", step_name, exc)
            print(f"Failed clicking {step_name}: {exc}")
            return False

    log_step(logger, f"Failed to click {step_name} after {retries} attempts")
    return False


def wait_for_visible_element(
    driver: WebDriver,
    by: By,
    value: str,
    timeout: int,
    logger,
    step_name: str,
):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, value))
        )
        log_step(logger, f"{step_name} detected")
        return element

    except TimeoutException:
        log_step(
            logger,
            f"Timed out waiting for {step_name}. Current URL: {driver.current_url}",
        )
        return None


def switch_to_new_window_if_opened(driver: WebDriver, old_handles: set[str], logger) -> None:
    new_handles = set(driver.window_handles) - old_handles
    if not new_handles:
        return

    new_handle = list(new_handles)[0]
    driver.switch_to.window(new_handle)
    log_step(logger, f"Switched to new window/tab. Current URL: {driver.current_url}")


def bypass_account_checkup_if_present(
    driver: WebDriver,
    logger,
    timeout: int = 8,
) -> bool:
    """
    Handles the intermittent account-checkup interruption after MANAGE SUBSCRIPTION.

    If Microsoft redirects to account-checkup, load account.microsoft.com directly
    and continue the normal deactivation flow.
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.url_contains(ACCOUNT_CHECKUP_URL_PART)
        )

        log_step(logger, "Account checkup interruption detected")
        driver.get(ACCOUNT_HOME_URL)
        log_step(logger, "Loaded account home page to bypass account checkup")
        return True

    except TimeoutException:
        log_step(logger, "Account checkup interruption not present")
        return True

    except Exception as exc:
        logger.exception("Failed while bypassing account checkup: %s", exc)
        print(f"Failed while bypassing account checkup: {exc}")
        return False


def click_manage_subscription_from_xbox(driver: WebDriver, logger, timeout: int = 8) -> bool:
    """
    First MANAGE SUBSCRIPTION button on the Xbox product/subscription page.

    Keep this timeout short because run_deactivation_steps checks the JOIN button
    separately to detect already-deactivated accounts.
    """
    old_handles = set(driver.window_handles)

    xpath_options = [
        (
            By.XPATH,
            "//div[contains(@class, 'typography-module__xdsButtonText') "
            "and normalize-space()='MANAGE SUBSCRIPTION']"
            "/ancestor::*[self::a or self::button][1]",
        ),
        (
            By.XPATH,
            "//div[contains(@class, 'typography-module__xdsButtonText') "
            "and normalize-space()='MANAGE SUBSCRIPTION']",
        ),
    ]

    for index, (by, value) in enumerate(xpath_options):
        current_timeout = timeout if index == 0 else 3

        if safe_click(
            driver=driver,
            by=by,
            value=value,
            timeout=current_timeout,
            logger=logger,
            step_name="'MANAGE SUBSCRIPTION' button",
        ):
            time.sleep(2)
            switch_to_new_window_if_opened(driver, old_handles, logger)
            return True

    return False


def click_subscriptions_left_nav(driver: WebDriver, logger, timeout: int = 30) -> bool:
    xpath = (
        "//a[@aria-label='Subscriptions' "
        "or @data-bi-id='leftnav.subscriptions-link' "
        "or .//span[normalize-space()='Subscriptions']]"
    )

    return safe_click(
        driver=driver,
        by=By.XPATH,
        value=xpath,
        timeout=timeout,
        logger=logger,
        step_name="'Subscriptions' left navigation link",
    )


def click_subscription_manage(driver: WebDriver, logger, timeout: int = 30) -> bool:
    xpath = (
        "//span[normalize-space()='Manage' and contains(@class, 'ms-Button-label')]"
        "/ancestor::*[self::button or self::a][1]"
    )

    fallback_xpath = "//span[normalize-space()='Manage']"

    if safe_click(
        driver=driver,
        by=By.XPATH,
        value=xpath,
        timeout=timeout,
        logger=logger,
        step_name="'Manage' subscription button",
    ):
        return True

    return safe_click(
        driver=driver,
        by=By.XPATH,
        value=fallback_xpath,
        timeout=5,
        logger=logger,
        step_name="'Manage' subscription text fallback",
    )


def click_cancel_subscription_link(driver: WebDriver, logger, timeout: int = 30) -> bool:
    """
    Clicks the visible 'Cancel subscription' entry after Manage.

    Microsoft often leaves hidden duplicate 'Cancel subscription' elements in the DOM.
    Normal element_to_be_clickable can grab a zero-size/hidden match, so this function
    filters candidates by displayed state and real bounding-box size before clicking.
    """
    xpath = (
        "//span[normalize-space()='Cancel subscription']"
        " | //*[normalize-space()='Cancel subscription']"
    )

    end_time = time.time() + timeout

    while time.time() < end_time:
        try:
            candidates = driver.find_elements(By.XPATH, xpath)

            for candidate in candidates:
                try:
                    rect = candidate.rect
                    if (
                        not candidate.is_displayed()
                        or rect.get("width", 0) <= 0
                        or rect.get("height", 0) <= 0
                    ):
                        continue

                    # Prefer a clickable ancestor if there is one.
                    clickable = candidate
                    ancestors = candidate.find_elements(
                        By.XPATH,
                        "./ancestor::*[self::button or self::a or @role='button'][1]",
                    )
                    if ancestors:
                        ancestor = ancestors[0]
                        ancestor_rect = ancestor.rect
                        if (
                            ancestor.is_displayed()
                            and ancestor_rect.get("width", 0) > 0
                            and ancestor_rect.get("height", 0) > 0
                        ):
                            clickable = ancestor

                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});",
                        clickable,
                    )
                    time.sleep(0.3)

                    try:
                        clickable.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", clickable)

                    log_step(logger, "'Cancel subscription' link clicked")
                    return True

                except StaleElementReferenceException:
                    continue

            time.sleep(0.5)

        except Exception as exc:
            logger.warning("Error while searching for visible Cancel subscription link: %s", exc)
            time.sleep(0.5)

    log_step(logger, "Timed out waiting for visible 'Cancel subscription' link")
    return False


def click_benefit_cancel_button(driver: WebDriver, logger, timeout: int = 30) -> bool:
    return safe_click(
        driver=driver,
        by=By.CSS_SELECTOR,
        value="button#benefit-cancel[data-bi-id='benefit-cancel']",
        timeout=timeout,
        logger=logger,
        step_name="'Cancel subscription' benefit button",
    )


def click_cancel_now_refund_radio(driver: WebDriver, logger, timeout: int = 30) -> bool:
    """
    Selects the 'Cancel now and get refund' radio option, verifies it is selected,
    then pauses for manual confirmation before continuing.

    Microsoft's Fabric radio controls are often styled, so the raw input can exist
    but not respond to a normal Selenium click. This function tries:
        1. Normal click on the real input
        2. JavaScript click on the real input
        3. JavaScript checked + input/change/click events
        4. Click visible label/container fallback
    """
    input_locators = [
        (By.CSS_SELECTOR, "input[data-bi-id='xbox-cancel-select-cancel-now-option']"),
        (By.CSS_SELECTOR, "input[aria-label*='Cancel now and get refund']"),
        (By.CSS_SELECTOR, "input[id*='cancel-now']"),
        (By.XPATH, "//input[contains(@aria-label, 'Cancel now and get refund')]"),
    ]

    def is_selected(element) -> bool:
        try:
            return bool(
                driver.execute_script(
                    "return arguments[0].checked === true || arguments[0].getAttribute('aria-checked') === 'true';",
                    element,
                )
            )
        except Exception:
            try:
                return element.is_selected()
            except Exception:
                return False

    def pause_after_success() -> None:
        log_step(logger, "Refund option appears selected. Continuing automatically.")

    def try_input_element(element) -> bool:
        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                element,
            )
            time.sleep(0.5)

            # Try normal click first.
            try:
                element.click()
                time.sleep(0.5)
                if is_selected(element):
                    log_step(logger, "'Cancel now and get refund' radio selected with normal click")
                    pause_after_success()
                    return True
            except Exception as click_exc:
                logger.warning("Normal refund radio click failed: %s", click_exc)

            # Try JS click.
            try:
                driver.execute_script("arguments[0].click();", element)
                time.sleep(0.5)
                if is_selected(element):
                    log_step(logger, "'Cancel now and get refund' radio selected with JS click")
                    pause_after_success()
                    return True
            except Exception as js_click_exc:
                logger.warning("JS refund radio click failed: %s", js_click_exc)

            # Try setting checked and firing all relevant events.
            try:
                driver.execute_script(
                    """
                    const el = arguments[0];
                    el.scrollIntoView({block: 'center'});
                    el.focus();
                    el.checked = true;
                    el.setAttribute('checked', 'checked');

                    for (const eventName of ['pointerdown', 'mousedown', 'mouseup', 'click', 'input', 'change']) {
                        el.dispatchEvent(new Event(eventName, { bubbles: true, cancelable: true }));
                    }
                    """,
                    element,
                )
                time.sleep(0.7)

                if is_selected(element):
                    log_step(logger, "'Cancel now and get refund' radio selected with JS checked/events")
                    pause_after_success()
                    return True

            except Exception as js_event_exc:
                logger.warning("JS refund radio checked/events failed: %s", js_event_exc)

        except StaleElementReferenceException:
            return False

        except Exception as exc:
            logger.warning("Refund radio input attempt failed: %s", exc)

        return False

    end_time = time.time() + timeout

    while time.time() < end_time:
        for by, value in input_locators:
            try:
                elements = driver.find_elements(by, value)

                for element in elements:
                    if try_input_element(element):
                        return True

            except Exception as exc:
                logger.warning("Error finding refund radio using %s=%s: %s", by, value, exc)

        # Visible fallback: click label/text/wrapper near the refund text.
        fallback_xpaths = [
            "//*[contains(normalize-space(), 'Cancel now and get refund')]",
            "//*[contains(normalize-space(), 'get refund')]",
            "//*[contains(normalize-space(), 'refund')]/ancestor::*[self::label or @role='radio' or contains(@class, 'ChoiceField')][1]",
            "//input[contains(@aria-label, 'Cancel now and get refund')]/ancestor::*[self::label or @role='radio' or contains(@class, 'ChoiceField')][1]",
        ]

        for xpath in fallback_xpaths:
            try:
                candidates = driver.find_elements(By.XPATH, xpath)

                for candidate in candidates:
                    try:
                        rect = candidate.rect
                        if (
                            not candidate.is_displayed()
                            or rect.get("width", 0) <= 0
                            or rect.get("height", 0) <= 0
                        ):
                            continue

                        driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});",
                            candidate,
                        )
                        time.sleep(0.5)

                        try:
                            candidate.click()
                        except Exception:
                            driver.execute_script("arguments[0].click();", candidate)

                        time.sleep(0.7)

                        # Re-check the real input after clicking the visible wrapper.
                        for by, value in input_locators:
                            for input_element in driver.find_elements(by, value):
                                if is_selected(input_element):
                                    log_step(
                                        logger,
                                        "'Cancel now and get refund' radio selected via visible fallback",
                                    )
                                    pause_after_success()
                                    return True

                    except StaleElementReferenceException:
                        continue

                    except Exception as fallback_exc:
                        logger.warning("Refund visible fallback candidate failed: %s", fallback_exc)

            except Exception as exc:
                logger.warning("Radio visible fallback search failed for %s: %s", xpath, exc)

        time.sleep(0.5)

    log_step(logger, "Timed out selecting 'Cancel now and get refund' radio option")
    return False


def click_final_cancel_subscription_button(driver: WebDriver, logger, timeout: int = 45) -> bool:
    """
    Clicks the final 'Cancel subscription' button.

    This is deliberately more aggressive because the refund radio step can be flaky.
    It tries stable IDs/data attributes first, then falls back to visible real-size
    buttons with aria-label/text matching Cancel subscription.
    """
    selectors = [
        (By.CSS_SELECTOR, "button#cancel-select-cancel"),
        (By.CSS_SELECTOR, "button[data-bi-id='xbox-cancel-select-cancel']"),
        (By.XPATH, "//button[@aria-label='Cancel subscription' and @id='cancel-select-cancel']"),
        (By.XPATH, "//button[@aria-label='Cancel subscription' and @data-bi-id='xbox-cancel-select-cancel']"),
    ]

    for by, value in selectors:
        if safe_click(
            driver=driver,
            by=by,
            value=value,
            timeout=10,
            logger=logger,
            step_name="Final 'Cancel subscription' button",
        ):
            return True

    xpath = (
        "//button[normalize-space()='Cancel subscription' "
        "or @aria-label='Cancel subscription' "
        "or .//*[normalize-space()='Cancel subscription']]"
    )

    end_time = time.time() + timeout

    while time.time() < end_time:
        try:
            buttons = driver.find_elements(By.XPATH, xpath)

            visible_buttons = []
            for button in buttons:
                try:
                    rect = button.rect
                    if (
                        button.is_displayed()
                        and rect.get("width", 0) > 0
                        and rect.get("height", 0) > 0
                    ):
                        visible_buttons.append(button)
                except StaleElementReferenceException:
                    continue

            for button in reversed(visible_buttons):
                try:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});",
                        button,
                    )
                    time.sleep(0.3)

                    try:
                        button.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", button)

                    log_step(logger, "Final 'Cancel subscription' button clicked")
                    return True

                except StaleElementReferenceException:
                    continue

                except Exception as exc:
                    logger.warning("Visible final cancel button click failed: %s", exc)

            time.sleep(0.5)

        except Exception as exc:
            logger.warning("Error while searching for final cancel button: %s", exc)
            time.sleep(0.5)

    log_step(logger, "Timed out waiting for final 'Cancel subscription' button")
    return False


def wait_for_completion_message(driver: WebDriver, logger, timeout: int = 45) -> str | None:
    """
    Waits for completion and extracts the specific completion/refund message.

    The previous broad XPath could match the whole page container. This version:
        1. waits until page text contains 'Your subscription will end on'
        2. scans visible elements for the smallest useful text containing that phrase
        3. falls back to document.body.innerText if needed
    """
    end_time = time.time() + timeout

    while time.time() < end_time:
        try:
            body_text = driver.execute_script(
                "return document.body ? document.body.innerText : '';"
            ) or ""

            normalised_body = " ".join(body_text.split())

            if "Your subscription will end on" not in normalised_body:
                time.sleep(0.5)
                continue

            candidates = driver.find_elements(
                By.XPATH,
                "//*[contains(normalize-space(), 'Your subscription will end on')]",
            )

            visible_texts = []

            for candidate in candidates:
                try:
                    if not candidate.is_displayed():
                        continue

                    text = " ".join(candidate.text.split())

                    if "Your subscription will end on" not in text:
                        continue

                    # Prefer the smallest matching element text, not the full page container.
                    visible_texts.append(text)

                except StaleElementReferenceException:
                    continue

            if visible_texts:
                visible_texts.sort(key=len)
                message_text = visible_texts[0]
                log_step(logger, f"Completion message found: {message_text}")
                return message_text

            log_step(logger, "Completion message found in page text")
            return normalised_body

        except Exception as exc:
            logger.warning("Error while checking completion message: %s", exc)
            time.sleep(0.5)

    log_step(
        logger,
        f"Timed out waiting for deactivation completion message. Current URL: {driver.current_url}",
    )
    return None


def classify_completion_message(message_text: str, email: str, logger) -> bool:
    """
    Logs deactivation/refund result.

    Refunded:
        message contains 'Your subscription will end on'
        and 'We refunded'
        and 'to the payment method we have on file'

    Deactivated, not refunded:
        message contains 'Your subscription will end on'
        but not the refund wording
    """
    normalised_message = " ".join(message_text.split())

    has_end_message = "Your subscription will end on" in normalised_message
    has_refund_message = (
        "We refunded" in normalised_message
        and "to the payment method we have on file" in normalised_message
    )

    if has_end_message and has_refund_message:
        log_step(logger, f"Account {email} has been deactivated and refunded.")
        return True

    if has_end_message:
        log_step(logger, f"Account {email} has been deactivated but no refund was detected.")
        return True

    log_step(logger, f"Account {email} completion message was not recognised: {message_text}")
    return False


def is_join_button_present(driver: WebDriver) -> bool:
    xpath = (
        "//button[.//div[normalize-space()='JOIN'] "
        "or contains(@aria-label, 'Join Xbox Game Pass')]"
    )

    elements = driver.find_elements(By.XPATH, xpath)

    for element in elements:
        try:
            rect = element.rect
            if (
                element.is_displayed()
                and rect.get("width", 0) > 0
                and rect.get("height", 0) > 0
            ):
                return True
        except StaleElementReferenceException:
            continue

    return False


def run_deactivation_steps(driver: WebDriver, email: str, logger) -> bool:
    # If JOIN is already visible on the Xbox page, there is no active subscription to deactivate.
    if is_join_button_present(driver):
        log_step(
            logger,
            f"Account {email} is already deactivated (JOIN button detected before MANAGE SUBSCRIPTION).",
        )
        return True

    # Try MANAGE SUBSCRIPTION.
    # If it is unavailable, check JOIN again before treating it as a failure.
    if not click_manage_subscription_from_xbox(driver, logger, timeout=8):
        if is_join_button_present(driver):
            log_step(
                logger,
                f"Account {email} is already deactivated (JOIN button detected after MANAGE SUBSCRIPTION was unavailable).",
            )
            return True

        log_step(logger, "Could not click MANAGE SUBSCRIPTION from Xbox page.")
        return False

    remaining_steps = [
        (
            bypass_account_checkup_if_present,
            "Could not bypass account checkup interruption.",
        ),
        (
            click_subscriptions_left_nav,
            "Could not click Subscriptions in account left navigation.",
        ),
        (
            click_subscription_manage,
            "Could not click Manage on the subscription page.",
        ),
        (
            click_cancel_subscription_link,
            "Could not click Cancel subscription link.",
        ),
        (
            click_benefit_cancel_button,
            "Could not click benefit-cancel Cancel subscription button.",
        ),
        (
            click_cancel_now_refund_radio,
            "Could not select Cancel now and get refund radio option.",
        ),
        (
            click_final_cancel_subscription_button,
            "Could not click final Cancel subscription button.",
        ),
    ]

    for step_function, failure_message in remaining_steps:
        if not step_function(driver, logger):
            log_step(logger, failure_message)
            return False

        time.sleep(1)

    completion_message = wait_for_completion_message(driver, logger, timeout=45)
    if completion_message is None:
        log_step(
            logger,
            f"Account {email} may not have completed deactivation. Completion message was not found.",
        )
        return False

    return classify_completion_message(completion_message, email, logger)


def deactivate_account_flow(
    driver: WebDriver,
    email: str,
    password: str,
    alternate_password: str,
    logger,
) -> bool:
    log_step(logger, f"Deactivate loop initiated for {email}")

    login_success = login_full_flow(driver, email, password, alternate_password, logger)
    if not login_success:
        log_step(logger, f"Login failed for {email}. Deactivation will not proceed.")
        return False

    return run_deactivation_steps(driver, email, logger)
