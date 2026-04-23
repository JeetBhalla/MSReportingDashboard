"""
auth_browser.py
---------------
OKTA / SSO browser-based authentication for Agility VersionOne.

Uses Selenium (Edge or Chrome -- both pre-installed on Windows) to open a
real browser window. Credentials are auto-filled; user completes MFA/push
in the browser. Session cookies are saved to .auth_session.json.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

SESSION_FILE = Path(__file__).parent / ".auth_session.json"
SESSION_TTL_SECONDS = 8 * 60 * 60  # 8 hours


# ------------------------------------------------------------------------------
# Session persistence
# ------------------------------------------------------------------------------

def save_session(cookies: List[Dict], base_url: str) -> None:
    data = {"cookies": cookies, "base_url": base_url, "saved_at": time.time()}
    SESSION_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("Session saved to %s", SESSION_FILE)


def load_saved_session() -> Optional[List[Dict]]:
    if not SESSION_FILE.exists():
        return None
    try:
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        if time.time() - data.get("saved_at", 0) > SESSION_TTL_SECONDS:
            logger.info("Session expired")
            return None
        return data.get("cookies", [])
    except Exception:
        return None


def clear_session() -> None:
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()


def get_auth_token_from_cookies(cookies: List[Dict]) -> Optional[str]:
    token_names = {"versionone", "v1token", "authtoken", "token",
                   "accesstoken", "auth", "session", ".versionone", "v1session"}
    for c in cookies:
        if c.get("name", "").lower() in token_names:
            return c["value"]
    if cookies:
        return max(cookies, key=lambda c: len(c.get("value", "")))["value"]
    return None


# ------------------------------------------------------------------------------
# Selenium driver factory
# ------------------------------------------------------------------------------

def _build_driver():
    """Launch Edge (primary) or Chrome (fallback), auto-managing the driver."""

    # -- Try Edge ----------------------------------------------------------
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.service import Service as EdgeService
        from selenium.webdriver.edge.options import Options as EdgeOptions
        from webdriver_manager.microsoft import EdgeChromiumDriverManager

        opts = EdgeOptions()
        opts.add_argument("--start-maximized")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        opts.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0"
        )
        service = EdgeService(EdgeChromiumDriverManager().install())
        driver = webdriver.Edge(service=service, options=opts)
        print("  [OK] Browser: Microsoft Edge")
        return driver
    except Exception as e:
        print(f"  [Edge unavailable: {e}] -> trying Chrome ...")

    # -- Try Chrome --------------------------------------------------------
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service as ChromeService
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        from webdriver_manager.chrome import ChromeDriverManager

        opts = ChromeOptions()
        opts.add_argument("--start-maximized")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opts)
        print("  [OK] Browser: Google Chrome")
        return driver
    except Exception as e:
        raise RuntimeError(
            f"Could not launch Edge or Chrome via Selenium.\n"
            f"Last error: {e}\n"
            f"Make sure Edge or Chrome is installed on this machine."
        )


# ------------------------------------------------------------------------------
# Form helpers
# ------------------------------------------------------------------------------

def _find_element(driver, selectors: List[Tuple], timeout: int = 15):
    """Poll for any selector in the list; return first visible element."""
    from selenium.webdriver.common.by import By

    deadline = time.time() + timeout
    while time.time() < deadline:
        for by, val in selectors:
            try:
                el = driver.find_element(by, val)
                if el.is_displayed():
                    return el, (by, val)
            except Exception:
                pass
        time.sleep(0.5)
    return None, None


def _fill(driver, selectors: List[Tuple], value: str, label: str) -> bool:
    el, matched = _find_element(driver, selectors, timeout=15)
    if el is None:
        print(f"  [WARN] {label} field not found - please fill manually.")
        return False
    try:
        el.clear()
        # type character-by-character to avoid paste-block issues
        for ch in value:
            el.send_keys(ch)
            time.sleep(0.02)
        print(f"  [OK] {label} entered")
        return True
    except Exception as e:
        print(f"  [WARN] Could not type {label}: {e}")
        return False


def _click_next(driver, timeout: int = 5) -> bool:
    from selenium.webdriver.common.by import By

    candidates = [
        (By.ID,          "okta-signin-submit"),
        (By.CSS_SELECTOR,'input[type="submit"]'),
        (By.CSS_SELECTOR,'button[type="submit"]'),
        (By.XPATH,       '//button[contains(translate(text(),"SIGNIN","signin"),"sign in")]'),
        (By.XPATH,       '//button[contains(translate(text(),"LOGIN","login"),"log in")]'),
        (By.XPATH,       '//button[contains(text(),"Next")]'),
        (By.XPATH,       '//input[@value="Next"]'),
        (By.XPATH,       '//input[@value="Sign In"]'),
    ]
    el, matched = _find_element(driver, candidates, timeout=timeout)
    if el:
        try:
            el.click()
            print(f"  [OK] Form submitted")
            return True
        except Exception as e:
            print(f"  [WARN] Submit click failed: {e}")
    return False


# ------------------------------------------------------------------------------
# Core login flow
# ------------------------------------------------------------------------------

def browser_login(base_url: str, username: str = "", password: str = "") -> List[Dict]:
    """
    Open Edge/Chrome, navigate to Agility (which redirects to OKTA),
    auto-fill credentials, wait for MFA completion, capture cookies.
    """
    from selenium.webdriver.common.by import By

    agility_host = base_url.rstrip("/").split("/")[2]

    print("\n" + "=" * 60)
    print("  Agility OKTA Login")
    print("=" * 60)
    print(f"  URL  : {base_url}")
    if username:
        print(f"  User : {username}")
        print("  Password will be auto-filled.")
        print("  -> Complete MFA/push in the browser - closes automatically.")
    else:
        print("  -> Please sign in manually in the browser window.")
    print("=" * 60 + "\n")

    driver = _build_driver()

    try:
        # -- Navigate -------------------------------------------------------
        print(f"  -> Opening {base_url} ...")
        driver.get(base_url)
        time.sleep(3)
        print(f"  -> Current URL: {driver.current_url}")

        # -- Auto-fill ------------------------------------------------------
        if username and password:
            _fill_okta_form(driver, username, password)

        # -- Wait until we land back on Agility (post-MFA redirect) ---------
        print("\n  [wait] Waiting for MFA/OKTA to complete ...")
        print("     (Approve the push notification or enter OTP in the browser)")
        print("     Browser will close automatically once login is detected.\n")

        deadline = time.time() + 300  # 5 minutes
        landed = False
        while time.time() < deadline:
            try:
                cur = driver.current_url
                on_agility = agility_host in cur
                # identity.us.digital.ai and okta both contain recognisable tokens
                on_sso = any(x in cur.lower() for x in [
                    "okta", "login", "signin", "identity.", "auth/realms",
                    "saml", "sso", "idp", "sts", "keycloak",
                ])
                if on_agility and not on_sso:
                    print(f"  [OK] Landed on Agility: {cur}")
                    landed = True
                    break
                remaining = int(deadline - time.time())
                if remaining % 30 == 0 and remaining > 0:
                    print(f"  [wait] Still waiting ... ({remaining}s left) URL: {cur[:80]}")
            except Exception:
                pass
            time.sleep(1.5)

        if not landed:
            raise RuntimeError(
                "Login timed out: the browser did not redirect back to Agility "
                "within 5 minutes. Please try again and complete the MFA "
                "authentication more quickly."
            )

        # -- Re-navigate to Agility to ensure cookies are from the right domain
        # Selenium's get_cookies() only returns cookies for the current domain,
        # so we must be on www19.v1host.com when we call it.
        print("  -> Navigating to Agility to finalize cookie capture ...")
        driver.get(base_url)
        time.sleep(4)  # let page fully load and set all session cookies

        # -- Capture cookies ------------------------------------------------
        selenium_cookies = driver.get_cookies()
        # Convert to httpx-compatible format
        cookies = [
            {
                "name":   c["name"],
                "value":  c["value"],
                "domain": c.get("domain", ""),
                "path":   c.get("path", "/"),
            }
            for c in selenium_cookies
        ]
        # Warn if no cookies from the Agility domain
        agility_cookies = [c for c in cookies if agility_host.replace("www", "") in c.get("domain", "")]
        print(f"\n  [OK] {len(cookies)} cookies captured ({len(agility_cookies)} from Agility domain).")
        if not agility_cookies:
            print("  [WARN] No cookies from Agility domain - session may not authenticate correctly.")

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    if not cookies:
        raise RuntimeError(
            "No cookies were captured. The login may have failed or timed out. "
            "Please try again."
        )

    save_session(cookies, base_url)
    print("  [OK] Session saved.\n")
    return cookies


def _fill_okta_form(driver, username: str, password: str) -> None:
    """Fill OKTA username field -> submit -> password field -> submit."""
    from selenium.webdriver.common.by import By

    username_sels = [
        (By.ID,          "okta-signin-username"),
        (By.ID,          "username"),
        (By.ID,          "identifier"),
        (By.NAME,        "username"),
        (By.NAME,        "identifier"),
        (By.CSS_SELECTOR,'input[type="email"]'),
        (By.CSS_SELECTOR,'input[autocomplete="username"]'),
        (By.CSS_SELECTOR,'input[autocomplete="email"]'),
    ]
    password_sels = [
        (By.ID,          "okta-signin-password"),
        (By.ID,          "password"),
        (By.NAME,        "password"),
        (By.NAME,        "credentials.passcode"),
        (By.CSS_SELECTOR,'input[type="password"]'),
        (By.CSS_SELECTOR,'input[autocomplete="current-password"]'),
    ]

    ok_user = _fill(driver, username_sels, username, "Username")
    if not ok_user:
        return

    # Some OKTA flows: username -> Next (separate step) -> password
    _click_next(driver, timeout=3)
    time.sleep(2)

    ok_pass = _fill(driver, password_sels, password, "Password")
    if not ok_pass:
        print("  [INFO] If the password field didn't appear yet, "
              "it may show after the username step completes.")
        return

    time.sleep(0.5)
    _click_next(driver, timeout=5)
    time.sleep(2)
    print("  -> Sign-in submitted - MFA step should appear now ...")


# ------------------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from config import AGILITY_BASE_URL
    u  = sys.argv[1] if len(sys.argv) > 1 else ""
    pw = sys.argv[2] if len(sys.argv) > 2 else ""
    cookies = browser_login(AGILITY_BASE_URL, u, pw)
    print(f"\nCaptured {len(cookies)} cookies.")
