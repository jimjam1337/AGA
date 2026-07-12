import re
import csv
from pathlib import Path

log_path = Path(r"C:\Users\james\Documents\GitHub\AGA\AGA Account Tool\logs\selenium_2026-04-07.log")
output_csv = Path(r"C:\Users\james\Documents\GitHub\AGA\AGA Account Tool\logs\summary.csv")

text = log_path.read_text(encoding="utf-8", errors="ignore")

email_pattern = r'\b[a-zA-Z0-9._%+-]+@activegamers\.com\.au\b'
processing_pattern = re.compile(r"Processing account:\s*(" + email_pattern + r")")
action_success_pattern = re.compile(r"Action completed successfully(?: for (" + email_pattern + r"))?")
action_fail_pattern = re.compile(r"Action failed(?: for (" + email_pattern + r"))?")
already_active_pattern = re.compile(r"Account (" + email_pattern + r") is already active\. Skipping subscription flow\.")

NO_AVAILABLE_CODES_LOG = "No available gift cards remain for"
NO_ACCOUNT_LOG = "Microsoft account does not exist error detected"

# Success markers
success_markers = [
    "Action completed successfully",
    "is already active. Skipping subscription flow",
    "Manage button found. Account is already activated"
]


# Failure markers
specific_failure_markers = [
    "Login flow did not complete successfully.",
    "Subscribe button not found or could not be clicked.",
    "Launch or install Xbox PC app element did not appear.",
    "Balance below threshold but Close button could not be clicked.",
    "Balance below threshold but 'Redeem a code' button could not be clicked.",
    "Balance below threshold but gift card code could not be redeemed.",
    "Unhandled activation flow error:",
    "Could not click 'Use your password' after password",
    "Post-password FIDO page appeared but passkey cancel could not be clicked",
    "Timed out waiting for final Xbox page after password.",
    "Subscription flow failed for",
    "No Microsoft account does not exist error detected",
    "Microsoft account does not exist error detected",
]

results = {}
current_email = None
last_meaningful_reason = {}


def ensure_account(email):
    if email not in results:
        results[email] = {
            "status": "UNKNOWN",
            "type": "",
            "reason": "",
        }


for raw_line in text.splitlines():
    line = raw_line.strip()

    match = processing_pattern.search(line)
    if match:
        current_email = match.group(1)
        ensure_account(current_email)
        continue

    if NO_ACCOUNT_LOG in line:
        if current_email:
            ensure_account(current_email)
            results[current_email]["status"] = "FAIL"
            results[current_email]["type"] = "No Account"
            results[current_email]["reason"] = "Account does not exist"
        continue

    if NO_AVAILABLE_CODES_LOG in line:
        if current_email:
            ensure_account(current_email)
            results[current_email]["status"] = "FAIL"
            results[current_email]["type"] = "No Codes"
            results[current_email]["reason"] = "No available gift card codes remaining"
        continue

    match = already_active_pattern.search(line)
    if match:
        email = match.group(1)
        ensure_account(email)
        results[email]["status"] = "SUCCESS"
        results[email]["type"] = "Already Active"
        results[email]["reason"] = "Skipped subscription (already active)"
        current_email = email
        continue

    # SUCCESS
    if any(marker in line for marker in success_markers):
        if current_email:
            ensure_account(current_email)
            results[current_email]["status"] = "SUCCESS"

            if "already active" in line or "Manage button found" in line:
                results[current_email]["type"] = "Already Active"
                results[current_email]["reason"] = "Already active (manage detected)"
            else:
                results[current_email]["type"] = "Activated"
                results[current_email]["reason"] = "Completed successfully"
        continue

    # Track failure reasons
    if current_email:
        ensure_account(current_email)
        for marker in specific_failure_markers:
            if marker in line:
                last_meaningful_reason[current_email] = line
                break

    # FAIL
    match = action_fail_pattern.search(line)
    if match:
        email = match.group(1) or current_email
        if email:
            ensure_account(email)
            if results[email]["status"] != "SUCCESS":
                results[email]["status"] = "FAIL"
                results[email]["type"] = "Failed"
                results[email]["reason"] = last_meaningful_reason.get(email, line)
        continue


# Resolve UNKNOWN → FAIL if reason exists
for email, data in results.items():
    if data["status"] == "UNKNOWN" and email in last_meaningful_reason:
        data["status"] = "FAIL"
        data["type"] = "Failed"
        data["reason"] = last_meaningful_reason[email]

# Write CSV
with output_csv.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Email", "Status", "Type", "Reason"])

    for email in sorted(results):
        writer.writerow([
            email,
            results[email]["status"],
            results[email]["type"],
            results[email]["reason"],
        ])

# Summary
success_count = sum(1 for r in results.values() if r["status"] == "SUCCESS")
fail_count = sum(1 for r in results.values() if r["status"] == "FAIL")
unknown_count = sum(1 for r in results.values() if r["status"] == "UNKNOWN")

print(f"CSV exported to: {output_csv}")
print("\n=== SUMMARY ===")
print(f"Success: {success_count}")
print(f"Fail: {fail_count}")
print(f"Unknown: {unknown_count}")
print(f"Total processed: {len(results)}")