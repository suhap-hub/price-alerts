"""
Price Drop Alert - NIFTY 50, NIFTY Bank, Gold
Sends independent email alerts via Gmail when any asset drops >1% from previous close.
"""

import yfinance as yf
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ── Configuration ─────────────────────────────────────────────────────────────
GMAIL_SENDER   = os.environ["GMAIL_SENDER"]    # your Gmail address
GMAIL_PASSWORD = os.environ["GMAIL_PASSWORD"]  # Gmail App Password (16 chars)
ALERT_RECEIVER = os.environ["ALERT_RECEIVER"]  # where to send alerts (can be same as sender)
DROP_THRESHOLD = 1.0  # percent

ASSETS = {
    "NIFTY 50":   "^NSEI",
    "NIFTY Bank": "^NSEBANK",
    "Gold":       "GC=F",
}
# ──────────────────────────────────────────────────────────────────────────────


def send_email(subject: str, body: str) -> bool:
    """Send an alert email via Gmail SMTP."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = GMAIL_SENDER
        msg["To"]      = ALERT_RECEIVER

        # Plain text version
        text_part = MIMEText(body, "plain")

        # HTML version (nicer formatting in email clients)
        html_body = body.replace("\n", "<br>")
        html_part = MIMEText(
            f"""
            <div style="font-family:sans-serif;max-width:480px;padding:24px;
                        border:1px solid #e0e0e0;border-radius:8px;">
              <h2 style="color:#c0392b;margin-top:0;">🔴 Price Drop Alert</h2>
              <p style="font-size:15px;line-height:1.7;color:#333;">{html_body}</p>
              <hr style="border:none;border-top:1px solid #eee;">
              <p style="font-size:12px;color:#999;">
                Sent by your automated price alert system
              </p>
            </div>
            """,
            "html"
        )

        msg.attach(text_part)
        msg.attach(html_part)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_SENDER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_SENDER, ALERT_RECEIVER, msg.as_string())

        print(f"  ✓ Email sent to {ALERT_RECEIVER}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("  ✗ Email failed: Authentication error. Check your App Password.")
        return False
    except Exception as e:
        print(f"  ✗ Email error: {e}")
        return False


def check_asset(name: str, ticker: str) -> dict | None:
    """
    Fetch the last 2 trading days for a ticker.
    Returns a result dict if the drop exceeds DROP_THRESHOLD, else None.
    """
    try:
        data = yf.download(ticker, period="5d", interval="1d", progress=False, auto_adjust=True)

        if len(data) < 2:
            print(f"  [{name}] Not enough data (got {len(data)} rows)")
            return None

        prev_close = float(data["Close"].iloc[-2])
        curr_price = float(data["Close"].iloc[-1])
        pct_change = ((curr_price - prev_close) / prev_close) * 100

        print(f"  [{name}] Prev close: {prev_close:.2f}  Current: {curr_price:.2f}  Change: {pct_change:+.2f}%")

        if pct_change <= -DROP_THRESHOLD:
            return {
                "name":       name,
                "ticker":     ticker,
                "prev_close": prev_close,
                "curr_price": curr_price,
                "pct_change": pct_change,
            }

    except Exception as e:
        print(f"  [{name}] Error fetching data: {e}")

    return None


def format_alert(result: dict) -> tuple[str, str]:
    """Returns (subject, body) for the alert email."""
    subject = f"🔴 Price Drop Alert: {result['name']} dropped {result['pct_change']:.2f}%"
    body = (
        f"Asset    : {result['name']} ({result['ticker']})\n"
        f"Prev close: {result['prev_close']:.2f}\n"
        f"Current  : {result['curr_price']:.2f}\n"
        f"Drop     : {result['pct_change']:.2f}%\n"
        f"Time     : {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    )
    return subject, body


def main():
    print(f"\n=== Price Alert Check @ {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} ===\n")

    alerts_sent = 0

    for name, ticker in ASSETS.items():
        print(f"Checking {name} ({ticker}) ...")
        result = check_asset(name, ticker)

        if result:
            subject, body = format_alert(result)
            print(f"  ⚠ Drop detected! Sending email alert ...")
            send_email(subject, body)
            alerts_sent += 1
        else:
            print(f"  ✓ No significant drop.")

    print(f"\nDone. {alerts_sent} alert(s) sent.\n")


if __name__ == "__main__":
    main()
