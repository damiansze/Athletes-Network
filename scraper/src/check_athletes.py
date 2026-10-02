import os
import time
import random
import sys
import logging
from urllib.parse import urlparse, parse_qs

from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    WebDriverException,
    TimeoutException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Paths relative to this file: logs and tmp in scraper/, data in <project>/data
SCRAPER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(SCRAPER_DIR)
LOG_DIR = os.path.join(SCRAPER_DIR, "logs")
TMP_DIR = os.path.join(SCRAPER_DIR, "tmp")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(LOG_DIR, "check_athletes_debug.log"),
            mode="w",
            encoding="utf-8"
        ),
    ],
)

DATA_DIR = os.path.join(PROJECT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)


class BlockDetectedException(Exception):
    """Signals a soft block or critical fetch failure."""
    pass


def setup_driver():
    """
    Create and return a headless Chrome WebDriver with randomized options.

    Returns:
        selenium.webdriver.Chrome: Configured WebDriver instance.
    """
    user_agents = [
        ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
         "Chrome/115.0.0.0 Safari/537.36"),
        (
            (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 Safari/605.1.15"
            )
        ),
        ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
         "Chrome/115.0.0.0 Safari/537.36"),
    ]
    ua = random.choice(user_agents)
    logging.info("Setting up WebDriver with UA: %s", ua)

    tmp_dir = os.path.join(TMP_DIR, str(random.randint(1000, 9999)))
    os.makedirs(tmp_dir, exist_ok=True)

    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={tmp_dir}")
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


def extract_nation_options(driver, base_url):
    """
    Extract available nation options from a selection page.

    Args:
        driver (selenium.webdriver.Chrome): A configured WebDriver instance.
        base_url (str): The URL where the nation <select> is located.

    Returns:
        list of dict: Each dict has 'nation_id' and 'nation_name'.
    """
    logging.info("Extracting nation options from: %s", base_url)
    driver.get(base_url)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "nationId"))
    )
    nations = []
    try:
        select_elem = driver.find_element(By.NAME, "nationId")
        options = select_elem.find_elements(By.TAG_NAME, "option")
        for option in options:
            value = option.get_attribute("value")
            if value == "-1":
                continue
            nation_name = option.text.strip()
            nations.append({"nation_id": value, "nation_name": nation_name})
    except Exception as e:
        logging.error("Error extracting nation options: %s", e)
    return nations


def safe_get_single_attempt(driver, url, wait_condition=None, wait_timeout=10):
    """
    Perform a single attempt to load a URL, optionally waiting on a condition.

    Args:
        driver (selenium.webdriver.Chrome): WebDriver instance.
        url (str): The URL to load.
        wait_condition (EC condition, optional):
            Expected condition to wait for.
        wait_timeout (int, optional): How long (seconds) to wait.

    Raises:
        BlockDetectedException: If fetching or waiting times out.
    """
    try:
        driver.get(url)
        if wait_condition:
            WebDriverWait(driver, wait_timeout).until(wait_condition)
        WebDriverWait(driver, wait_timeout).until(
            lambda d: d.execute_script("return document.readyState")
            == "complete"
        )
    except (WebDriverException, TimeoutException) as e:
        logging.error("Single-attempt fetch failed for %s: %s", url, e)
        raise BlockDetectedException("Single-attempt fetch failed.")


def check_athlete_records(driver, athlete):
    """
    Check whether an athlete has any records by loading their RECORD page.

    Args:
        driver (selenium.webdriver.Chrome): WebDriver instance.
        athlete (dict): Info about the athlete, including 'athlete_link'.

    Returns:
        bool: True if the athlete has records, False otherwise.
    """
    records_url = f"{athlete['athlete_link']}&athletePage=RECORD"
    logging.info(
        "Checking records for athlete: %s (ID: %s)",
        athlete["athlete_name"],
        athlete["athlete_id"],
    )
    safe_get_single_attempt(
        driver,
        records_url,
        EC.presence_of_element_located((By.TAG_NAME, "body")),
        8,
    )

    page_source = driver.page_source
    if "There are no records registered for this athlete" in page_source:
        logging.info("No records for athlete %s.", athlete["athlete_id"])
        return False
    if len(page_source.strip()) < 200:
        logging.error(
            "Likely softblock or empty page for athlete %s.",
            athlete["athlete_id"],
        )
        sys.exit(1)
    try:
        table = driver.find_element(By.CLASS_NAME, "athleteRecord")
        record_rows = table.find_elements(
            By.XPATH, ".//tr[contains(@class, 'athleteRecord0')]"
        )
        return len(record_rows) > 0
    except Exception:
        return False


def scrape_main_page(driver, main_url):
    """
    Scrape the main page for athlete info.

    Args:
        driver (selenium.webdriver.Chrome): WebDriver instance.
        main_url (str): URL to a page listing athletes.

    Returns:
        list of dict: Each dict has athlete data like ID, name, link,
        date, and code.

    Raises:
        BlockDetectedException: If the page load fails or is blocked.
    """
    safe_get_single_attempt(
        driver,
        main_url,
        EC.presence_of_element_located((By.CLASS_NAME, "athleteList")),
        8,
    )
    time.sleep(1)
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
            parsed = urlparse(athlete_link)
            athlete_id = parse_qs(parsed.query).get("athleteId", [""])[0]
            athlete_date = row.find_element(
                By.CLASS_NAME, "date"
            ).text.strip()
            athlete_code = row.find_element(
                By.CLASS_NAME, "code"
            ).text.strip()

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
            logging.warning("Could not parse row: %s", e)
    return athletes


def main():
    """
    Main entry point for scraping and checking athletes.

    Collects nations for men and women, scrapes athletes for each,
    and logs how many have records.
    """
    base_urls = {
        "male": (
            "https://www.swimrankings.net/index.php?page=athleteSelect"
            "&selectPage=TOP100_MEN_ALL&nationId="
        ),
        "female": (
            "https://www.swimrankings.net/index.php?page=athleteSelect"
            "&selectPage=TOP100_WOMEN_ALL&nationId="
        ),
    }
    driver = setup_driver()
    nations_men = extract_nation_options(driver, base_urls["male"])
    nations_women = extract_nation_options(driver, base_urls["female"])
    driver.quit()

    all_tasks = [
        ("male", base_urls["male"], nation) for nation in nations_men
    ] + [
        ("female", base_urls["female"], nation) for nation in nations_women
    ]

    for gender, base_url, nation in tqdm(all_tasks, desc="Processing Nations"):
        driver = setup_driver()
        logging.info(
            "Fetching athletes for %s %s  -  %s",
            gender,
            nation["nation_id"],
            nation["nation_name"],
        )
        try:
            athletes = scrape_main_page(driver, base_url + nation["nation_id"])
        except BlockDetectedException as e:
            logging.error("Softblock or major error on main page: %s", e)
            sys.exit(1)

        count_with_records = 0
        for athlete in athletes:
            try:
                delay = random.uniform(0.1, 0.5)
                time.sleep(delay)
                if check_athlete_records(driver, athlete):
                    count_with_records += 1
            except BlockDetectedException:
                logging.error(
                    "Blocked while checking athlete: %s",
                    athlete["athlete_id"],
                )
                sys.exit(1)
        logging.info(
            "%s - %s: %d athletes, %d with records.",
            gender,
            nation["nation_name"],
            len(athletes),
            count_with_records,
        )
        driver.quit()


if __name__ == "__main__":
    main()
