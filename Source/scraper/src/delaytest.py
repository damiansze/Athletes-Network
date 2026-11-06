#!/usr/bin/env python3
"""
Script for testing various delay values to avoid triggering softblocks
while scraping a swim-ranking website. Contains logic to load athlete
RECORD pages, check page length, and interpret "no records" messages.
"""

import time
import logging
import argparse
import sys
import tempfile
import random
import itertools

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException

# URL for the main selection page
MAIN_URL = (
    "https://www.swimrankings.net/index.php?page=athleteSelect&nationId=0"
    "&selectPage=TOP100_MEN_ALL"
)
# Threshold to decide if a page is “empty”
MIN_PAGE_LENGTH = 200


class SoftBlockException(Exception):
    """Raised when a likely softblock is detected."""
    pass


def setup_driver():
    """
    Create and return a headless Chrome WebDriver configured
    to reduce detection.

    Returns:
        selenium.webdriver.Chrome: The configured driver instance.
    """
    user_agents = [
        ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"),
        ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
         "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 "
         "Safari/605.1.15"),
        ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"),
    ]
    ua = random.choice(user_agents)
    logging.info("Setting up WebDriver with UA: %s", ua)
    user_data_dir = tempfile.mkdtemp()
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"user-agent={ua}")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": (
                "Object.defineProperty(navigator, 'webdriver', "
                "{get: () => undefined})"
            )
        },
    )
    return driver


def get_athlete_list(driver):
    """
    Load the main selection page and extract a list of athlete dicts.

    Args:
        driver (selenium.webdriver.Chrome): The active WebDriver instance.

    Returns:
        list of dict: Each dict represents an athlete with keys like
            'athlete_id', 'athlete_name', 'athlete_link', etc.
    """
    logging.info("Loading main selection page: %s", MAIN_URL)
    try:
        driver.get(MAIN_URL)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "nationId"))
        )
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "athleteList"))
        )
    except (WebDriverException, TimeoutException) as e:
        logging.error("Error loading main page: %s", e)
        sys.exit(1)

    tables = driver.find_elements(By.CLASS_NAME, "athleteList")
    athlete_rows = []
    for table in tables:
        athlete_rows.extend(
            table.find_elements(
                By.XPATH, ".//tr[contains(@class, 'athleteSearch')]"
            )
        )

    athletes = []
    for row in athlete_rows:
        try:
            a_tags = row.find_elements(By.TAG_NAME, "a")
            if not a_tags:
                continue
            a_tag = a_tags[0]
            athlete_name = a_tag.text.strip()
            athlete_link = a_tag.get_attribute("href")
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(athlete_link)
            athlete_id = parse_qs(parsed.query).get("athleteId", [""])[0]
            has_date = row.find_elements(By.CLASS_NAME, "date")
            athlete_date = (
                has_date[0].text.strip() if has_date else ""
            )
            has_code = row.find_elements(By.CLASS_NAME, "code")
            athlete_code = (
                has_code[0].text.strip() if has_code else ""
            )
            athletes.append(
                {
                    "athlete_id": athlete_id,
                    "athlete_name": athlete_name,
                    "athlete_link": athlete_link,
                    "athlete_date": athlete_date,
                    "athlete_code": athlete_code,
                }
            )
        except Exception as e:
            logging.error("Error processing athlete row: %s", e)
    logging.info("Collected %d athletes from the main page.", len(athletes))
    return athletes


def check_athlete_record(driver, athlete, delay, use_wait):
    """
    Load the RECORD page for an athlete and determine if records exist.

    Args:
        driver (selenium.webdriver.Chrome): Active WebDriver instance.
        athlete (dict): Athlete info dict.
        delay (float): Delay in seconds before loading the record page.
        use_wait (bool): If True, use WebDriverWait on the body element.

    Returns:
        bool: True if the athlete has records, False if the
            "no records" message is found.

    Raises:
        SoftBlockException: If page content is below MIN_PAGE_LENGTH and not
            the explicit "no records" message.
    """
    records_url = f"{athlete['athlete_link']}&athletePage=RECORD"
    logging.info(
        "Checking records for athlete: %s (ID: %s)",
        athlete["athlete_name"],
        athlete["athlete_id"],
    )
    if delay > 0:
        logging.info(
            "Waiting %.2f seconds before loading athlete RECORD page.",
            delay
        )
        time.sleep(delay)
    try:
        driver.get(records_url)
        if use_wait:
            logging.info("Using WebDriverWait on athlete RECORD page.")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        time.sleep(2)  # Let dynamic content settle
    except (WebDriverException, TimeoutException) as e:
        logging.error(
            "Error loading RECORD page for athlete %s: %s",
            athlete["athlete_id"],
            e,
        )
        raise SoftBlockException("Failed to load RECORD page.")

    page_source = driver.page_source.strip()
    if "There are no records registered for this athlete" in page_source:
        logging.info(
            "Athlete %s shows no records (message found).",
            athlete["athlete_id"]
        )
        return False
    if len(page_source) < MIN_PAGE_LENGTH:
        logging.error(
            "Likely softblock for athlete %s: page content too short.",
            athlete["athlete_id"],
        )
        raise SoftBlockException("Softblocked: content too short.")
    logging.info(
        "Athlete %s: RECORD page loaded successfully.",
        athlete["athlete_id"]
    )
    return True


def evaluate_delay_value(delay, use_wait, test_duration):
    """
    Repeatedly load athlete RECORD pages to test whether a delay is safe.

    Args:
        delay (float): Delay in seconds before loading each record page.
        use_wait (bool): Whether to use WebDriverWait on each page load.
        test_duration (float): Minimum time (seconds) to keep testing
            without a softblock.

    Returns:
        bool: True if the delay ran for at least 'test_duration'
            seconds without softblock, False otherwise.
    """
    logging.info(
        "Testing delay value: %.3f seconds with WebDriverWait = %s",
        delay,
        use_wait
    )
    driver = setup_driver()
    try:
        athletes = get_athlete_list(driver)
        if not athletes:
            logging.error("No athletes found. Aborting delay test.")
            driver.quit()
            sys.exit(1)
    except Exception as e:
        logging.error("Error extracting athlete list: %s", e)
        driver.quit()
        return False

    athlete_cycle = itertools.cycle(athletes)
    start_time = time.time()
    iterations = 0
    try:
        while time.time() - start_time < test_duration:
            athlete = next(athlete_cycle)
            iterations += 1
            logging.info(
                "Delay test iteration #%d for delay %.3f, athlete %s (ID: %s)",
                iterations,
                delay,
                athlete["athlete_name"],
                athlete["athlete_id"],
            )
            try:
                _ = check_athlete_record(driver, athlete, delay, use_wait)
            except SoftBlockException as sbe:
                logging.error(
                    "Softblock detected during delay test for athlete %s: %s",
                    athlete["athlete_id"],
                    sbe,
                )
                driver.quit()
                return False
    except KeyboardInterrupt:
        logging.info("Interrupted by user during delay test.")
        driver.quit()
        sys.exit(0)

    driver.quit()
    elapsed = time.time() - start_time
    logging.info(
        "Delay %.3f seconds ran safely for %.0f seconds over %d iterations.",
        delay,
        elapsed,
        iterations,
    )
    return True


def main():
    """
    Main entry for evaluating a range of delays, searching for the smallest
    safe delay that avoids softblocks for a given test duration.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Test a range of delay values (with optional WebDriverWait) "
            "in descending order to find a safe delay that runs without "
            "softblocks for at least a specified duration."
        )
    )
    parser.add_argument(
        "--min-delay",
        type=float,
        default=0.25,
        help="Minimum delay (seconds) to test.",
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=1.0,
        help="Maximum delay (seconds) to test.",
    )
    parser.add_argument(
        "--step",
        type=float,
        default=0.25,
        help="Step decrement (seconds) for each test iteration.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=60.0,
        help="Test duration (seconds) for each delay value.",
    )
    parser.add_argument(
        "--use-wait",
        action="store_true",
        help="Enable explicit WebDriverWait for the <body> element.",
    )
    args = parser.parse_args()

    safe_delay = None
    current_delay = args.max_delay
    while current_delay >= args.min_delay:
        logging.info("=============================================")
        logging.info("Testing delay value: %.3f seconds", current_delay)
        result = evaluate_delay_value(
            current_delay, args.use_wait, args.duration
        )
        if result:
            logging.info(
                "Delay %.3f is SAFE (ran for at least %.0f seconds).",
                current_delay,
                args.duration,
            )
            safe_delay = current_delay
        else:
            logging.info("Delay %.3f is NOT safe.", current_delay)
            if safe_delay is not None:
                break
        current_delay -= args.step

    logging.info("=============================================")
    if safe_delay is not None:
        logging.info(
            "Optimal (minimum safe) delay: %.3f seconds",
            safe_delay
        )
        print("Optimal (minimum safe) delay:", safe_delay)
    else:
        logging.info("No safe delay values found in the tested range.")
        print("No safe delay values found.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    main()
