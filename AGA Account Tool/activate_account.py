from pathlib import Path
import re
import time

from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BALANCE_THRESHOLD = 17.95

MANAGE_BUTTON_XPATH = '//*[@id="PageContent"]/div/div[1]/div[1]/div[6]/div/div[1]/a'
MANAGE_SUBSCRIPTION_XPATH = "//*[contains(text(), 'MANAGE SUBSCRIPTION')]"
JOIN_BUTTON_XPATH = "//button[contains(@aria-label, 'Join')]"
SUBSCRIBE_BUTTON_XPATH = "//button[normalize-space()='Subscribe']"
XBOX_APP_TEXT_XPATH = "//p[text()='Launch or install Xbox PC app']"
BALANCE_XPATH = "//div[contains(text(), '$')]"

XBOX_APP_CONFIRMATION_XPATHS = [
    "//p[contains(normalize-space(.), 'Launch or install Xbox PC app')]",
    "//span[contains(normalize-space(.), 'Launch or install Xbox PC app')]",
    "//div[contains(normalize-space(.), 'Launch or install Xbox PC app')]",
    "//*[contains(normalize-space(.), 'Install Xbox PC app')]",
    "//*[contains(normalize-space(.), 'Launch Xbox PC app')]",
]

SUCCESS_STATE_XPATHS = [
    *XBOX_APP_CONFIRMATION_XPATHS,
    "//*[contains(normalize-space(.), 'Game Pass')]",
    "//*[contains(normalize-space(.), 'Manage')]",
    "//*[contains(normalize-space(.), 'Included with')]",
]

SELECT_PLAN_BUTTON_XPATH = (
    "//*[contains(normalize-space(.), 'Xbox Game Pass Premium 1 Month')]"
)

ORIGINAL_PRICE_XPATH = (
    "//span[normalize-space()='AU$17.95/month']"
)

def record_failed_account(run_entry, email, reason) -> None:
    run_entry["failed_accounts"].append({
        "email": email,
        "reason": reason,
    })


def find_manage_button(driver, logger, timeout: int = 5) -> bool:
    try:
        WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, MANAGE_BUTTON_XPATH))
        )
        logger.info("Manage button found. Account is already activated.")
        return True

    except TimeoutException:
        logger.info("Manage button not found. Account appears inactive.")
        return False

def select_original_plan(driver, logger, timeout: int = 8) -> bool:
    """
    If the Select Plan dropdown exists, choose the normal AU$17.95/month plan.
    If it doesn't exist, simply continue.
    """

    try:
        # Look for the dropdown
        plan_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, SELECT_PLAN_BUTTON_XPATH))
        )

        logger.info("Select Plan dropdown found. Opening plan list.")

        try:
            plan_button.click()
            logger.info("clicked plan_button")
        except Exception:
            logger.info("could not click plan button")
            driver.execute_script("arguments[0].click();", plan_button)


        # Wait for the normal price option
        original_plan = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, ORIGINAL_PRICE_XPATH))
        )

        logger.info("Selecting original AU$17.95/month plan.")

        try:
            original_plan.click()
        except Exception:
            driver.execute_script("arguments[0].click();", original_plan)

        time.sleep(1)
        return True

    except TimeoutException:
        logger.info("Select Plan dropdown not present. Continuing normally.")
        return False

    except Exception as exc:
        logger.info("Error selecting original plan: %s", exc)
        return False

def click_join_button(driver, logger, timeout: int = 30) -> bool:
    try:
        join_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, JOIN_BUTTON_XPATH))
        )
        time.sleep(10)
        join_button.send_keys(Keys.RETURN)
        logger.info("click_join_button completed. Join button appeared and was clicked.")
        return True

    except TimeoutException:
        logger.info("click_join_button completed. Join button was not found.")
        return False


def _find_visible_element_default_or_iframes(driver, xpath: str, logger, timeout: float = 5.0):
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

        try:
            driver.switch_to.default_content()
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            logger.info("Searching %s iframes for visible xpath: %s", len(iframes), xpath)

            for idx, iframe in enumerate(iframes):
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame(iframe)

                    elements = driver.find_elements(By.XPATH, xpath)
                    for el in elements:
                        try:
                            if el.is_displayed():
                                logger.info("Found visible xpath in iframe %s", idx)
                                driver.switch_to.default_content()
                                return iframe, "iframe"
                        except StaleElementReferenceException:
                            continue
                except Exception as exc:
                    logger.info("Error searching iframe %s for xpath %s: %s", idx, xpath, exc)
                    continue
        except Exception as exc:
            logger.info("Error enumerating iframes for xpath %s: %s", xpath, exc)

        time.sleep(0.1)

    try:
        driver.switch_to.default_content()
    except Exception:
        pass

    logger.info("Did not find visible element in default content or any iframe: %s", xpath)
    return None, None


def click_subscribe_button(driver, logger, timeout: int = 12, max_attempts: int = 3) -> bool:
    for attempt in range(1, max_attempts + 1):
        logger.info("Attempt %s/%s to click Subscribe button", attempt, max_attempts)

        target, location = _find_visible_element_default_or_iframes(
            driver,
            SUBSCRIBE_BUTTON_XPATH,
            logger,
            timeout=timeout,
        )

        if location is None:
            logger.info("Could not find Subscribe button in default content or any iframe")
            return False

        try:
            if location == "default_content":
                driver.switch_to.default_content()
                button = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, SUBSCRIBE_BUTTON_XPATH))
                )
            else:
                driver.switch_to.default_content()
                driver.switch_to.frame(target)
                button = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, SUBSCRIBE_BUTTON_XPATH))
                )

            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
            time.sleep(0.15)

            try:
                button.click()
            except Exception:
                driver.execute_script("arguments[0].click();", button)

            logger.info("Subscribe button clicked successfully")
            driver.switch_to.default_content()
            return True

        except TimeoutException:
            logger.info("Subscribe button was found but not clickable")
        except StaleElementReferenceException as exc:
            logger.info("Subscribe button became stale: %s", exc)
        except Exception as exc:
            logger.info("Error clicking Subscribe button: %s", exc)
        finally:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass

        time.sleep(0.3)

    logger.info("Failed to click Subscribe button after %s attempts", max_attempts)
    return False


def _is_any_success_indicator_visible(driver, logger) -> tuple[bool, str | None]:
    search_contexts = [("default content", None)]

    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for idx, iframe in enumerate(iframes):
            search_contexts.append((f"iframe {idx}", iframe))
    except Exception as exc:
        logger.info("Could not enumerate iframes while checking success state: %s", exc)

    for context_name, iframe in search_contexts:
        try:
            driver.switch_to.default_content()
            if iframe is not None:
                driver.switch_to.frame(iframe)

            for xpath in SUCCESS_STATE_XPATHS:
                elements = driver.find_elements(By.XPATH, xpath)
                for el in elements:
                    try:
                        if el.is_displayed():
                            logger.info(
                                "Success indicator found in %s using xpath: %s | text: %s",
                                context_name,
                                xpath,
                                el.text.strip()[:200],
                            )
                            return True, xpath
                    except StaleElementReferenceException:
                        continue
                    except Exception as exc:
                        logger.info(
                            "Error reading candidate success element in %s: %s",
                            context_name,
                            exc,
                        )
        except Exception as exc:
            logger.info("Error checking %s for success state: %s", context_name, exc)

    try:
        driver.switch_to.default_content()
    except Exception:
        pass

    return False, None


def wait_for_xbox_app_confirmation(
    driver,
    email: str,
    logger,
    timeout: int = 45,
    poll_interval: float = 1.0,
) -> bool:
    end_time = time.time() + timeout
    attempt = 0

    while time.time() < end_time:
        attempt += 1

        found, matched_xpath = _is_any_success_indicator_visible(driver, logger)
        if found:
            logger.info(
                "Account reactivation is complete for %s. "
                "Success state detected on attempt %s using xpath: %s",
                email,
                attempt,
                matched_xpath,
            )
            return True

        try:
            driver.switch_to.default_content()
            manage_buttons = driver.find_elements(By.XPATH, MANAGE_BUTTON_XPATH)
            for btn in manage_buttons:
                try:
                    if btn.is_displayed():
                        logger.info(
                            "Manage button became visible after subscribe for %s. "
                            "Treating as successful activation.",
                            email,
                        )
                        return True
                except StaleElementReferenceException:
                    continue
        except Exception as exc:
            logger.info("Error checking Manage button during success wait: %s", exc)

        try:
            current_url = driver.current_url
        except Exception:
            current_url = "<unavailable>"

        logger.info(
            "Success state not detected yet for %s on attempt %s. Current URL: %s",
            email,
            attempt,
            current_url,
        )
        time.sleep(poll_interval)

    try:
        driver.switch_to.default_content()
    except Exception:
        pass

    logger.info(
        "Xbox success state was not detected for %s after %s seconds. "
        "Check whether the account has a valid payment method or whether the "
        "success UI changed.",
        email,
        timeout,
    )
    return False


def parse_balance_amount(balance_text: str) -> float | None:
    match = re.search(r"\$?\s*([0-9]+(?:\.[0-9]{1,2})?)", balance_text)
    if not match:
        return None
    return float(match.group(1))


def get_account_balance(
    driver,
    logger,
    timeout: int = 15,
    retry_interval: float = 1.0,
) -> tuple[float | None, int | None]:
    end_time = time.time() + timeout
    attempt = 0

    while time.time() < end_time:
        attempt += 1
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        logger.info(
            "Balance search attempt %s: searching %s iframes for account balance",
            attempt,
            len(iframes),
        )

        for idx, iframe in enumerate(iframes):
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(iframe)

                logger.info("Checking iframe %s for balance on attempt %s", idx, attempt)

                elements = driver.find_elements(
                    By.XPATH,
                    "//div[contains(@class, 'storedValueAmount')]"
                )

                for el in elements:
                    try:
                        if not el.is_displayed():
                            continue

                        raw_text = el.text.strip()
                        logger.info("Balance found in iframe %s: %s", idx, raw_text)

                        balance_value = parse_balance_amount(raw_text)
                        if balance_value is None:
                            logger.info("Could not parse balance from text: %s", raw_text)
                            driver.switch_to.default_content()
                            return None, None

                        logger.info("Parsed account balance: %.2f", balance_value)
                        driver.switch_to.default_content()
                        return balance_value, idx

                    except Exception as exc:
                        logger.info("Error reading balance element in iframe %s: %s", idx, exc)

            except Exception as exc:
                logger.info("Error checking iframe %s on attempt %s: %s", idx, attempt, exc)

        driver.switch_to.default_content()
        logger.info(
            "Balance not found on attempt %s. Waiting %.1f seconds before retrying.",
            attempt,
            retry_interval,
        )
        time.sleep(retry_interval)

    driver.switch_to.default_content()
    logger.info("Balance not found in any iframe after %s seconds", timeout)
    return None, None


def send_activation_success_email(email, user_choice, send_end_of_loop_email) -> None:
    email_body = f"Account {email} has been activated"
    send_end_of_loop_email(email, email_body, user_choice)


def handle_low_balance_and_redeem_code(
    driver,
    email,
    balance_iframe_index,
    *,
    logger,
    run_entry,
    add_gift_card,
) -> bool:
    logger.info(
        "Starting gift card top-up flow for %s using balance iframe %s",
        email,
        balance_iframe_index,
    )

    close_clicked = add_gift_card["click_close_button"](
        driver,
        logger,
        balance_iframe_index,
    )
    if not close_clicked:
        reason = "Balance below threshold but Close button could not be clicked."
        logger.info("%s Account: %s", reason, email)
        record_failed_account(run_entry, email, reason)
        return False

    time.sleep(2)
    logger.info("Waited 2 seconds after clicking Close")

    redeem_clicked = add_gift_card["click_redeem_code_button"](driver, logger)
    if not redeem_clicked:
        reason = "Balance below threshold but 'Redeem a code' button could not be clicked."
        logger.info("%s Account: %s", reason, email)
        record_failed_account(run_entry, email, reason)
        return False

    code_redeemed = add_gift_card["redeem_first_available_code"](driver, logger, email)
    if not code_redeemed:
        reason = "Balance below threshold but gift card code could not be redeemed."
        logger.info("%s Account: %s", reason, email)
        record_failed_account(run_entry, email, reason)
        return False

    logger.info("Gift card flow completed successfully for %s", email)
    return True


def perform_subscription_flow(
    driver,
    email,
    *,
    logger,
    run_entry,
    user_choice,
    send_end_of_loop_email,
    add_gift_card,
    allow_gift_card_retry: bool = True,
) -> bool:
    # If a plan selector is shown, choose the normal monthly plan first.
    select_original_plan(driver, logger)
    join_clicked = click_join_button(driver, logger)
    if not join_clicked:
        reason = "Join button was not found."
        logger.info("%s Account: %s", reason, email)
        record_failed_account(run_entry, email, reason)
        return False

    logger.info("Waiting 4 seconds after Join before checking balance.")
    time.sleep(4)

    balance_value, balance_iframe_index = get_account_balance(
        driver,
        logger,
        timeout=15,
        retry_interval=1.0,
    )

    if balance_value is not None and balance_value < BALANCE_THRESHOLD:
        logger.info(
            "Balance %.2f is below threshold %.2f for %s",
            balance_value,
            BALANCE_THRESHOLD,
            email,
        )

        if not allow_gift_card_retry:
            reason = (
                f"Balance {balance_value:.2f} is still below threshold "
                f"{BALANCE_THRESHOLD:.2f} after gift card retry."
            )
            logger.info(reason)
            record_failed_account(run_entry, email, reason)
            return False

        gift_card_success = handle_low_balance_and_redeem_code(
            driver,
            email,
            balance_iframe_index,
            logger=logger,
            run_entry=run_entry,
            add_gift_card=add_gift_card,
        )
        if not gift_card_success:
            return False

        logger.info(
            "Gift card redeemed successfully for %s. Restarting activation flow from the beginning.",
            email,
        )
        return activate_account_flow(
            driver,
            email,
            password=None,
            alternate_password=None,
            logger=logger,
            run_entry=run_entry,
            user_choice=user_choice,
            login_full_flow=None,
            send_end_of_loop_email=send_end_of_loop_email,
            add_gift_card=add_gift_card,
            skip_login=True,
            allow_gift_card_retry=False,
        )

    if balance_value is not None:
        logger.info(
            "Balance %.2f is >= threshold %.2f. Continuing normal activation flow.",
            balance_value,
            BALANCE_THRESHOLD,
        )
    else:
        logger.info("Balance was not detected. Continuing normal activation flow.")

    logger.info("Waiting 6 seconds before looking for Subscribe button.")
    time.sleep(6)

    subscribe_clicked = click_subscribe_button(
        driver=driver,
        logger=logger,
        timeout=12,
        max_attempts=3,
    )

    if not subscribe_clicked:
        reason = "Subscribe button not found or could not be clicked."
        logger.info("%s Account: %s", reason, email)
        record_failed_account(run_entry, email, reason)
        return False

    logger.info("Subscribe button clicked. Waiting 4 seconds for post-subscribe UI transition.")
    time.sleep(4)

    activated = wait_for_xbox_app_confirmation(
        driver=driver,
        email=email,
        logger=logger,
        timeout=45,
    )

    if not activated and find_manage_button(driver, logger, timeout=5):
        logger.info(
            "Post-subscribe fallback detected Manage button for %s. "
            "Treating subscription flow as successful.",
            email,
        )
        activated = True

    if not activated:
        reason = (
            "Launch/install Xbox app success state did not appear. "
            "Check whether the account has a valid payment method or whether the success UI changed."
        )
        record_failed_account(run_entry, email, reason)
        return False

    send_activation_success_email(
        email=email,
        user_choice=user_choice,
        send_end_of_loop_email=send_end_of_loop_email,
    )
    time.sleep(10)
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
    add_gift_card,
    skip_login: bool = False,
    allow_gift_card_retry: bool = True,
) -> bool:
    logger.info("Activation loop initiated for %s", email)

    try:
        if not skip_login:
            login_success = login_full_flow(driver, email, password, alternate_password, logger)
            if not login_success:
                reason = "Login flow did not complete successfully."
                record_failed_account(run_entry, email, reason)
                return False
        else:
            logger.info("Skipping login because flow is restarting after successful gift card redemption.")

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
            add_gift_card=add_gift_card,
            allow_gift_card_retry=allow_gift_card_retry,
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