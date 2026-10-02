#!/usr/bin/env python3
"""
Web Scraping Script for Swimming Rankings

This script uses Selenium to scrape athlete information from a swim ranking
website and writes the results to CSV files. It processes data for multiple
nations, extracting athlete details and their best records. The script uses
parallel processing (currently restricted to a single worker), robust error
handling (including a soft-block detection), comprehensive logging, and a
retry mechanism for nations whose CSV file is suspiciously small.

Additionally, any nation that already has an existing CSV file that is
sufficiently large is skipped and not re-scraped.

Note:
    - Scraping the "RECORD" tab is currently disabled.
    - The safe_get function uses a small random delay (0.1 to 0.5 seconds)
      combined with WebDriverWait.
    - Parallel execution is restricted to a single worker.
"""

import csv
import time
import tempfile
import logging
import os
import sys
import random
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm

# Paths relative to this file: logs in scraper/logs, data in <project>/data
SCRAPER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(SCRAPER_DIR)
LOG_DIR = os.path.join(SCRAPER_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging (both console and file)
LOG_FILE = os.path.join(LOG_DIR, "scraper_debug.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8"),
    ],
)

DATA_DIR = os.path.join(PROJECT_DIR, "data", "raw")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Threshold (in bytes) to consider a CSV file acceptable.
CSV_SIZE_THRESHOLD = 1024


class SoftBlockException(Exception):
    """Custom exception for soft-block detection during scraping."""
    pass


def setup_driver():
    """
    Set up and return a Selenium WebDriver with headless Chrome.

    Returns:
        selenium.webdriver.Chrome: A configured WebDriver instance.
    """
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/15.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    ]
    ua = random.choice(USER_AGENTS)
    logging.info(
        "Setting up the WebDriver with proxy: None; using User-Agent: %s", ua
    )
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
                "{ get: () => undefined })"
            )
        },
    )
    return driver


def safe_get(driver, url):
    """
    Navigate to a URL safely by adding a small random delay and waiting for
    the page to load.

    Args:
        driver (selenium.webdriver.Chrome): A Selenium WebDriver instance.
        url (str): The URL to load.

    Raises:
        SoftBlockException: If the loaded page source is suspiciously short
            (indicative of a possible soft-block).
    """
    try:
        delay = random.uniform(0.1, 0.5)
        logging.info("Waiting %.3f seconds before loading %s", delay, url)
        time.sleep(delay)
        driver.get(url)
        # Wait until the <body> tag is present
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script(
                "return document.readyState"
            ) == "complete"
        )
        if len(driver.page_source.strip()) < 200:
            raise SoftBlockException(
                f"Page appears blank (soft-block) for {url}"
            )
    except (WebDriverException, TimeoutException) as e:
        logging.error("Fetch failed for %s: %s", url, e)
        raise SoftBlockException("Page load failed.") from e


def extract_nation_options(driver, url):
    """
    Extract nation options from a selection page.

    Args:
        driver (selenium.webdriver.Chrome): A Selenium WebDriver instance.
        url (str): The URL containing nation selection options.

    Returns:
        list of dict: A list of dictionaries with keys 'nation_id' and
        'nation_name'.
    """
    logging.info("Extracting nation options from: %s", url)
    safe_get(driver, url)
    time.sleep(3)
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
        logging.info("Found %d nation options.", len(nations))
    except Exception as e:
        logging.error("Error extracting nation options: %s", e)
    return nations


def scrape_main_page(driver, main_url):
    """
    Scrape the main page to extract athlete rows.

    Args:
        driver (selenium.webdriver.Chrome): A Selenium WebDriver instance.
        main_url (str): The URL of the main page that contains athlete data.

    Returns:
        tuple:
            athletes (list of dict): A list of athlete information
            dictionaries.
            is_empty (bool): True if no valid athlete data was found.
    """
    logging.info("Scraping main page: %s", main_url)
    safe_get(driver, main_url)
    time.sleep(5)
    tables = driver.find_elements(By.CLASS_NAME, "athleteList")
    athlete_rows = []
    for table in tables:
        rows = table.find_elements(
            By.XPATH, ".//tr[contains(@class, 'athleteSearch')]"
        )
        athlete_rows.extend(rows)
    athletes = []
    for row in athlete_rows:
        try:
            name_td = row.find_element(By.CLASS_NAME, "name")
            a_tags = name_td.find_elements(By.TAG_NAME, "a")
            if a_tags and a_tags[0].text.strip():
                a_tag = a_tags[0]
                athlete_name = a_tag.text.strip()
                athlete_link = a_tag.get_attribute("href")
                parsed_url = urlparse(athlete_link)
                athlete_id = parse_qs(parsed_url.query).get(
                    "athleteId", [""]
                )[0]
                athlete_date = row.find_element(By.CLASS_NAME, "date") \
                    .text.strip()
                athlete_code = row.find_element(
                    By.CLASS_NAME, "code"
                ).text.strip()
                athletes.append({
                    "athlete_id": athlete_id,
                    "athlete_name": athlete_name,
                    "athlete_link": athlete_link,
                    "athlete_date": athlete_date,
                    "athlete_code": athlete_code,
                })
        except Exception as e:
            logging.exception("Error processing row: %s", e)
            continue
    is_empty = (len(athletes) == 0)
    logging.info(
        "Collected %d athletes from the page (is_empty=%s).",
        len(athletes),
        is_empty,
    )
    return athletes, is_empty


def scrape_athlete_details(driver, athlete):
    """
    Scrape detailed information from an athlete's page.

    Args:
        driver (selenium.webdriver.Chrome): A Selenium WebDriver instance.
        athlete (dict): Dictionary containing keys like 'athlete_name',
            'athlete_id', 'athlete_link'.

    Returns:
        tuple:
            details (dict): Dictionary with additional athlete details
                (e.g., 'nactionclub').
            best_records (list of dict): List of records such as 'event',
                'course', 'time', etc.
    """
    logging.info("Scraping details for athlete: %s (ID: %s)",
                 athlete["athlete_name"], athlete["athlete_id"])
    safe_get(driver, athlete["athlete_link"])
    time.sleep(5)
    details = {}
    try:
        time.sleep(1)
        athlete_info_div = driver.find_element(By.ID, "athleteinfo")
        try:
            nactionclub = athlete_info_div.find_element(By.ID, "nationclub") \
                .text.strip().replace("\n", " ")
            details["nactionclub"] = nactionclub
        except Exception as e:
            logging.warning(
                "Nation club not found for athlete %s: %s",
                athlete["athlete_id"],
                e,
            )
            details["nactionclub"] = ""
    except Exception:
        logging.error(
            "Element with ID 'athleteinfo' not found for athlete %s",
            athlete["athlete_id"]
        )
        details["nactionclub"] = ""

    best_records = []
    try:
        time.sleep(1)
        best_tables = driver.find_elements(By.CLASS_NAME, "athleteBest")
        if not best_tables:
            logging.info(
                ("No 'athleteBest' table found for athlete %s; "
                 "skipping best records."),
                athlete["athlete_id"]
            )
            return details, best_records

        athlete_best_table = best_tables[0]
        best_rows = athlete_best_table.find_elements(
            By.XPATH, ".//tr[contains(@class, 'athleteBest')]"
        )
        for row in best_rows:
            try:
                tds = row.find_elements(By.TAG_NAME, "td")
                if len(tds) >= 7:
                    record = {
                        "event": tds[0].text.strip(),
                        "course": tds[1].text.strip(),
                        "time": tds[2].text.strip(),
                        "best_code": tds[3].text.strip(),
                        "best_date": tds[4].text.strip(),
                        "city": tds[5].text.strip(),
                        "best_name": tds[6].text.strip(),
                    }
                    best_records.append(record)
                else:
                    logging.warning(
                        ("Unexpected number of columns in athleteBest row "
                         "for athlete %s"),
                        athlete["athlete_id"]
                    )
            except Exception as e:
                logging.exception(
                    "Error processing athleteBest row for athlete %s: %s",
                    athlete["athlete_id"],
                    e,
                )
                continue
    except Exception as e:
        logging.exception(
            "Error retrieving athleteBest table for athlete %s: %s",
            athlete["athlete_id"],
            e,
        )
    return details, best_records


def process_nation(task):
    """
    Process scraping for a single nation.

    Uses a retry mechanism if the CSV file is suspiciously small, unless
    the table is truly empty. Skips scraping if a sufficiently large CSV
    already exists.

    Args:
        task (tuple): Contains:
            - nation (dict): e.g., {'nation_id': str, 'nation_name': str}.
            - base_url (str): The base URL for the scraping target.
            - gender (str): 'male' or 'female'.

    Returns:
        tuple:
            num_athletes (int): The number of athletes scraped for this nation.
            data_csv_path (str): Path to the CSV file with athlete data.
            records_csv_path (str): Path to the CSV file with athlete records.
    """
    nation, base_url, gender = task
    nation_url = base_url + nation["nation_id"]
    data_csv_path = os.path.join(
        DATA_DIR, f"athlete_data_{gender}_{nation['nation_id']}.csv"
    )
    # records_csv_path = os.path.join(
    #     DATA_DIR, f"athlete_records_{gender}_{nation['nation_id']}.csv"
    # )

    # Skip if CSV already exists and is of acceptable size
    if (
        os.path.exists(data_csv_path) and
        os.path.getsize(data_csv_path) > CSV_SIZE_THRESHOLD
    ):
        logging.info(
            "Nation %s already scraped (CSV size acceptable). Skipping.",
            nation["nation_name"]
        )
        return (0, data_csv_path, None)

    max_retries = 3
    attempt = 1
    num_athletes = 0
    while attempt <= max_retries:
        driver = setup_driver()
        try:
            logging.info(
                "Scraping %s athletes for nation: %s (%s) [Attempt %d]",
                gender,
                nation["nation_name"],
                nation_url,
                attempt,
            )
            safe_get(driver, nation_url)
            athletes, is_empty = scrape_main_page(driver, nation_url)
            for athlete in athletes:
                athlete["gender"] = gender
                athlete["nation"] = nation["nation_name"]
        except SoftBlockException as e:
            logging.error(
                "Soft-block detected in nation %s: %s",
                nation["nation_name"], e
            )
            driver.quit()
            raise
        except Exception as e:
            logging.error(
                "Error processing nation %s on attempt %d: %s",
                nation["nation_name"], attempt, e
            )
            driver.quit()
            attempt += 1
            continue

        # Write CSV files
        try:
            with open(
                data_csv_path, "w", newline="", encoding="utf-8"
            ) as f_data:

                data_fieldnames = [
                    "athlete_id",
                    "athlete_name",
                    "athlete_link",
                    "athlete_date",
                    "athlete_code",
                    "nactionclub",
                    "gender",
                    "nation",
                    "event",
                    "course",
                    "time",
                    "best_code",
                    "best_date",
                    "city",
                    "best_name",
                ]
                # records_fieldnames = [
                #    "athlete_id",
                #    "athlete_name",
                #    "record_category",
                #    "event",
                #    "course",
                #    "time",
                #    "club",
                #    "date",
                #    "city",
                #    "relay_names",
                # ]
                data_writer = csv.DictWriter(
                    f_data, fieldnames=data_fieldnames
                )
                # records_writer = csv.DictWriter(
                #     f_records, fieldnames=records_fieldnames
                # )
                data_writer.writeheader()
                # records_writer.writeheader()

                for athlete in athletes:
                    details, best_records = scrape_athlete_details(
                        driver, athlete
                    )
                    nactionclub = details.get("nactionclub", "")
                    if best_records:
                        for record in best_records:
                            row_data = {
                                "athlete_id": athlete["athlete_id"],
                                "athlete_name": athlete["athlete_name"],
                                "athlete_link": athlete["athlete_link"],
                                "athlete_date": athlete["athlete_date"],
                                "athlete_code": athlete["athlete_code"],
                                "nactionclub": nactionclub,
                                "gender": athlete["gender"],
                                "nation": athlete["nation"],
                                "event": record["event"],
                                "course": record["course"],
                                "time": record["time"],
                                "best_code": record["best_code"],
                                "best_date": record["best_date"],
                                "city": record["city"],
                                "best_name": record["best_name"],
                            }
                            data_writer.writerow(row_data)
                    else:
                        # If no best records, at least write the basic data
                        row_data = {
                            "athlete_id": athlete["athlete_id"],
                            "athlete_name": athlete["athlete_name"],
                            "athlete_link": athlete["athlete_link"],
                            "athlete_date": athlete["athlete_date"],
                            "athlete_code": athlete["athlete_code"],
                            "nactionclub": nactionclub,
                            "gender": athlete["gender"],
                            "nation": athlete["nation"],
                            "event": "",
                            "course": "",
                            "time": "",
                            "best_code": "",
                            "best_date": "",
                            "city": "",
                            "best_name": "",
                        }
                        data_writer.writerow(row_data)
            num_athletes = len(athletes)
        except Exception as e:
            logging.exception(
                "Error writing CSV for nation %s on attempt %d: %s",
                nation["nation_name"], attempt, e
            )
            driver.quit()
            attempt += 1
            continue

        driver.quit()

        # If the nation is truly empty, remove any CSV files and do not retry
        if is_empty:
            logging.info(
                ("Nation %s is flagged as empty. Deleting CSV files and "
                 "skipping further retries."),
                nation["nation_name"]
            )
            if os.path.exists(data_csv_path):
                os.remove(data_csv_path)
            # if os.path.exists(records_csv_path):
            #     os.remove(records_csv_path)
            break

        # Check if the CSV is large enough
        if os.path.exists(data_csv_path):
            current_size = os.path.getsize(data_csv_path)
        else:
            current_size = 0

        if current_size > CSV_SIZE_THRESHOLD:
            logging.info(
                "Nation %s CSV is acceptable (size: %d bytes).",
                nation["nation_name"],
                current_size,
            )
            break
        else:
            logging.warning(
                ("Nation %s CSV is too small (size: %d bytes). "
                 "Retrying (attempt %d)..."),
                nation["nation_name"], current_size, attempt
            )
            attempt += 1
            # Optionally remove the small CSV before retrying
            if os.path.exists(data_csv_path):
                os.remove(data_csv_path)
            # if os.path.exists(records_csv_path):
            #     os.remove(records_csv_path)

    return (num_athletes, data_csv_path, None)


def combine_csv(master_path, csv_files, fieldnames):
    """
    Combine multiple CSV files into one master CSV file and delete
    the individual files afterward.

    Args:
        master_path (str): Path to the master CSV file.
        csv_files (list of str): List of file paths to be combined.
        fieldnames (list of str): The CSV fieldnames.
    """
    with open(master_path, "w", newline="", encoding="utf-8") as master_file:
        writer = csv.DictWriter(master_file, fieldnames=fieldnames)
        writer.writeheader()
        for file in csv_files:
            if file is None:
                continue
            try:
                with open(file, "r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        writer.writerow(row)
            except Exception as e:
                logging.exception("Error combining file %s: %s", file, e)
    for file in csv_files:
        if file and os.path.exists(file):
            try:
                os.remove(file)
                logging.info("Deleted file %s", file)
            except Exception as e:
                logging.exception("Error deleting file %s: %s", file, e)


def main():
    """
    Main function orchestrating the scraping process:

    Steps:
        1. Extract nations for men and women.
        2. Create tasks for each nation with a retry mechanism.
        3. Combine the resulting CSVs into master CSV files.

    Raises:
        SystemExit: On soft-block detection or manual interruption.
    """
    base_url_men = (
        "https://www.swimrankings.net/index.php?page=athleteSelect"
        "&selectPage=TOP100_MEN_ALL&nationId="
    )
    base_url_women = (
        "https://www.swimrankings.net/index.php?page=athleteSelect"
        "&selectPage=TOP100_WOMEN_ALL&nationId="
    )

    # Use a single driver to extract nation options, then quit
    driver = setup_driver()
    nations_men = extract_nation_options(driver, base_url_men)
    nations_women = extract_nation_options(driver, base_url_women)
    driver.quit()

    tasks = [(nation, base_url_men, "male") for nation in nations_men] + \
            [(nation, base_url_women, "female") for nation in nations_women]
    total_nations = len(tasks)
    logging.info("Processing %d nation tasks in parallel.", total_nations)

    data_files = []
    # records_files = []
    total_athletes = 0

    # Due to performance considerations, use only 1 worker
    with ProcessPoolExecutor(max_workers=1) as executor:
        futures = {
            executor.submit(process_nation, task): task
            for task in tasks
        }
        try:
            for future in tqdm(
                as_completed(futures),
                total=total_nations,
                desc="Nations Processed"
            ):
                try:
                    num, data_file, rec_file = future.result()
                    total_athletes += num
                    if data_file:
                        data_files.append(data_file)
                    # if rec_file:
                    #     records_files.append(rec_file)
                except SoftBlockException as e:
                    logging.error(
                        "Soft-block detected; shutting down all tasks: %s", e
                    )
                    executor.shutdown(wait=False)
                    sys.exit(1)
                except Exception as e:
                    logging.exception(
                        "Exception processing a nation task: %s", e
                    )
        except KeyboardInterrupt:
            logging.info("KeyboardInterrupt caught. Shutting down executor...")
            executor.shutdown(wait=False)
            sys.exit(1)

    logging.info("Total athletes scraped: %d", total_athletes)
    master_data_csv = os.path.join(DATA_DIR, "athlete_data_master.csv")
    # master_records_csv = os.path.join(DATA_DIR, "athlete_records_master.csv")
    data_fieldnames = [
        "athlete_id",
        "athlete_name",
        "athlete_link",
        "athlete_date",
        "athlete_code",
        "nactionclub",
        "gender",
        "nation",
        "event",
        "course",
        "time",
        "best_code",
        "best_date",
        "city",
        "best_name",
    ]
    # records_fieldnames = [
    #    "athlete_id",
    #    "athlete_name",
    #    "record_category",
    #    "event",
    #    "course",
    #    "time",
    #    "club",
    #    "date",
    #    "city",
    #    "relay_names",
    # ]
    combine_csv(master_data_csv, data_files, data_fieldnames)
    # combine_csv(master_records_csv, records_files, records_fieldnames)
    logging.info("Master athlete data CSV saved to %s", master_data_csv)
    # logging.info(
    #     "Master athlete records CSV saved to %s", master_records_csv
    # )


if __name__ == "__main__":
    main()
