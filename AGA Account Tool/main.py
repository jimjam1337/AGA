import inspect
import json
import logging
import os
import smtplib
import tempfile
import tkinter as tk
from datetime import datetime
from email.mime.text import MIMEText
from tkinter import simpledialog

from PIL import Image, ImageTk
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from activate_account import activate_account_flow
from add_gift_card import (
    click_close_button,
    click_redeem_code_button,
    redeem_first_available_code,
)
from deactivate_account import deactivate_account_flow
from login_account import login_full_flow


def build_chrome_driver():
    options = Options()

    user_data_dir = tempfile.mkdtemp(prefix="aga_chrome_profile_")
    options.add_argument(f"--user-data-dir={user_data_dir}")

    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.password_manager_leak_detection": False,
        "autofill.profile_enabled": False,
        "autofill.credit_card_enabled": False,
        "password_manager_enabled": False,
        "password_manager_leak_detection": False,
        "safebrowsing.enabled": False,
    }

    options.add_experimental_option("prefs", prefs)

    options.add_argument(
        "--disable-features="
        "PasswordManagerOnboarding,"
        "PasswordManagerRedesign,"
        "PasswordLeakDetection,"
        "AutofillServerCommunication,"
        "AutofillEnableAccountWalletStorage"
    )
    options.add_argument("--disable-password-generation")
    options.add_argument("--disable-autofill-keyboard-accessory-view")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)
    driver.maximize_window()
    return driver


def create_log():
    today_date = datetime.now().strftime("%Y-%m-%d")
    log_directory = r".\logs"
    os.makedirs(log_directory, exist_ok=True)

    log_filename = os.path.join(log_directory, f"selenium_{today_date}.log")
    logger = logging.getLogger("selenium")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        file_handler = logging.FileHandler(log_filename, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.info("Log has been created")
    return logger


def send_end_of_loop_email(email, email_body, operation_choice, logger) -> None:
    sender_email = "raxtech@activegamers.com.au"
    sender_password = ")_U+My@Q%4?*"
    recipient_email = "jim@activegamers.com.au"

    smtp_server = "activegamers.com.au"
    smtp_port = 587

    message = MIMEText(email_body)
    message["Subject"] = f"account management ({operation_choice}) process has completed for {email}"
    message["From"] = sender_email
    message["To"] = recipient_email

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, message.as_string())

    logger.info("Email sent at the end of the loop.")


def start_failed_accounts_log():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {"timestamp": timestamp, "failed_accounts": []}


def save_failed_accounts(entry, logger, file_path="failed_accounts.json"):
    if not entry["failed_accounts"]:
        logger.info("No failed accounts to save.")
        return

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                history = []
    else:
        history = []

    history.append(entry)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4)

    logger.info("Failed accounts saved to %s", file_path)


def parse_ranges(range_str):
    ranges = []
    if not range_str.strip():
        return ranges

    for part in range_str.split(","):
        part = part.strip()

        if "-" in part:
            try:
                start, end = map(int, part.split("-"))
                if 0 < start <= end:
                    ranges.append((start, end))
            except ValueError:
                continue
        else:
            try:
                n = int(part)
                if n > 0:
                    ranges.append((n, n))
            except ValueError:
                continue

    return ranges


def define_base_credentials():
    email_bases = ["aga", "agapc", "wanxb", "wanpc", "wodxb", "wodpc"]
    ranges_dict = {}

    root = tk.Tk()
    root.withdraw()

    password = "AGA111222"
    alternate_password = "activegamers111222"





    for base in email_bases:
        user_input = simpledialog.askstring(
            "Input",
            f"Enter ranges for {base} (e.g. 1-3,7-10 or 0 to skip):",
            parent=root,
        )
        if user_input is None:
            user_input = "0"

        ranges_dict[base] = parse_ranges(user_input)

    root.destroy()
    return email_bases, password, alternate_password, ranges_dict


def create_dialogue_box(logger):
    result = {"value": None}

    def set_result(value):
        result["value"] = value
        root.destroy()

    image_path = os.path.join("icons", "aga_logo_600x345.png")

    root = tk.Tk()
    root.title("AGA GamePass Account Tool")

    image = Image.open(image_path)
    image = image.resize((600, 345), Image.LANCZOS)
    photo = ImageTk.PhotoImage(image)

    label = tk.Label(root, image=photo)
    label.image = photo
    label.place(x=0, y=0, relwidth=1, relheight=1)

    tk.Button(root, text="Activate", command=lambda: set_result("activate")).place(
        relx=0.1,
        rely=0.5,
        anchor="center",
    )
    tk.Button(root, text="Deactivate", command=lambda: set_result("deactivate")).place(
        relx=0.35,
        rely=0.5,
        anchor="center",
    )
    tk.Button(root, text="Add Gift Card", command=lambda: set_result("add_gift_card")).place(
        relx=0.6,
        rely=0.5,
        anchor="center",
    )
    tk.Button(root, text="Check Status", command=lambda: set_result("check_status")).place(
        relx=0.85,
        rely=0.5,
        anchor="center",
    )

    root.geometry("600x345")
    root.mainloop()

    if result["value"] is not None:
        logger.info("Returned result is %s", result["value"])
        return result["value"]

    logger.warning("Dialog closed without selection")
    return "cancel"


def build_email_address(email_base: str, number: int) -> str:
    if email_base in ["aga", "agapc"]:
        return f"{email_base}{number}@activegamers.com.au"

    return f"{email_base}{number:02}@activegamers.com.au"


def process_accounts_with_action(
    action_callback,
    *,
    logger,
    run_entry,
    user_choice,
):
    email_bases, password, alternate_password, ranges = define_base_credentials()
    callback_params = inspect.signature(action_callback).parameters

    for email_base in email_bases:
        base_ranges = ranges.get(email_base, [])
        if not base_ranges:
            logger.info("Skipping %s - no valid ranges", email_base)
            continue

        for start, end in base_ranges:
            for i in range(start, end + 1):
                email = build_email_address(email_base, i)

                logger.info("Processing account: %s", email)
                driver = build_chrome_driver()
                logger.info("Driver initialized")

                available_kwargs = {
                    "driver": driver,
                    "email": email,
                    "password": password,
                    "alternate_password": alternate_password,
                    "logger": logger,
                    "run_entry": run_entry,
                    "user_choice": user_choice,
                    "login_full_flow": login_full_flow,
                    "send_end_of_loop_email": (
                        lambda e, body, choice: send_end_of_loop_email(e, body, choice, logger)
                    ),
                    "add_gift_card": {
                        "click_close_button": click_close_button,
                        "click_redeem_code_button": click_redeem_code_button,
                        "redeem_first_available_code": redeem_first_available_code,
                    },
                }

                filtered_kwargs = {
                    key: value
                    for key, value in available_kwargs.items()
                    if key in callback_params
                }

                try:
                    success = action_callback(**filtered_kwargs)

                    if success:
                        logger.info("Action completed successfully for %s", email)
                    else:
                        logger.info("Action failed for %s", email)
                        run_entry["failed_accounts"].append(
                            {
                                "email": email,
                                "action": user_choice,
                                "reason": "Action callback returned False",
                            }
                        )

                except Exception as exc:
                    logger.exception("Unhandled error processing %s: %s", email, exc)
                    run_entry["failed_accounts"].append(
                        {
                            "email": email,
                            "action": user_choice,
                            "reason": str(exc),
                        }
                    )

                finally:
                    driver.quit()


def main():
    logger = create_log()
    run_entry = start_failed_accounts_log()

    logger.info("Main execution started")
    user_choice = create_dialogue_box(logger)


    if user_choice == "activate":
        process_accounts_with_action(
            activate_account_flow,
            logger=logger,
            run_entry=run_entry,
            user_choice=user_choice,
        )
        save_failed_accounts(run_entry, logger)

    elif user_choice == "deactivate":
        process_accounts_with_action(
            deactivate_account_flow,
            logger=logger,
            run_entry=run_entry,
            user_choice=user_choice,
        )
        save_failed_accounts(run_entry, logger)

    else:
        logger.info("No supported action selected: %s", user_choice)


if __name__ == "__main__":
    main()
