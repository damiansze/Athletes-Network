#!/usr/bin/env python3
"""
Semi-automatic re-scraping of athletes whose detail page failed to load.

Athletes in data/raw/athlete_data_master.csv without best records AND without a
nation club were not loaded correctly during the original scrape. This script
re-scrapes exactly these athletes, reusing scrape_athlete_details from
scrape.py unchanged.

Because swimrankings.net is protected by Cloudflare, the script uses a
visible (non-headless) Chrome window. Whenever the Cloudflare challenge
appears, the script pauses until the user has solved it in the browser.

Results are appended to data/raw/athlete_data_rescrape.csv (same columns as
the master CSV). Already re-scraped athletes are skipped, so the script can
be stopped and resumed at any time.

Usage (from the project root):
    uv run python scraper/scripts/rescrape_missing.py
"""

import csv
import os
import sys

import pandas as pd
from selenium import webdriver

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.scrape import (  # noqa: E402
    DATA_DIR,
    scrape_athlete_details,
)

MASTER_CSV = os.path.join(DATA_DIR, "athlete_data_master.csv")
OUTPUT_CSV = os.path.join(DATA_DIR, "athlete_data_rescrape.csv")

FIELDNAMES = [
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
RECORD_FIELDS = FIELDNAMES[8:]
MAX_ATTEMPTS = 3


def setup_visible_driver():
    """
    Set up a visible Chrome WebDriver so the user can solve the
    Cloudflare challenge manually.

    Returns:
        selenium.webdriver.Chrome: A configured WebDriver instance.
    """
    # options = webdriver.ChromeOptions()
    # options.add_argument("--window-size=1200,900")
    # return webdriver.Chrome(options=options)
    options = webdriver.ChromeOptions()
    options.binary_location = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
    options.add_argument("--window-size=1200,900")
    return webdriver.Chrome(options=options)



def is_challenge_page(driver):
    """
    Check whether the current page is the Cloudflare challenge.

    Args:
        driver (selenium.webdriver.Chrome): A Selenium WebDriver instance.

    Returns:
        bool: True if the Cloudflare challenge is shown.
    """
    return "just a moment" in driver.title.lower()


def load_missing_athletes():
    """
    Load the athletes that failed during the original scrape
    (no best records and no nation club).

    Returns:
        list of dict: Athlete base data as stored in the master CSV.
    """
    df = pd.read_csv(MASTER_CSV, dtype=str)
    missing = df[df["event"].isna() & df["nactionclub"].isna()]
    missing = missing.drop_duplicates(["athlete_id", "gender"])
    return missing[FIELDNAMES[:8]].fillna("").to_dict("records")


def load_done_ids():
    """
    Load the athlete IDs that are already in the output CSV.

    Returns:
        set of str: Athlete IDs that were already re-scraped.
    """
    if not os.path.exists(OUTPUT_CSV):
        return set()
    return set(pd.read_csv(OUTPUT_CSV, dtype=str)["athlete_id"])


def scrape_with_challenge_handling(driver, athlete):
    """
    Scrape an athlete and pause for the user whenever the Cloudflare
    challenge appears.

    Args:
        driver (selenium.webdriver.Chrome): A Selenium WebDriver instance.
        athlete (dict): Athlete base data incl. 'athlete_link'.

    Returns:
        tuple: (details, best_records) as returned by
        scrape_athlete_details, or (None, None) if the page could not be
        loaded after MAX_ATTEMPTS attempts.
    """
    for _ in range(MAX_ATTEMPTS):
        details, best_records = scrape_athlete_details(driver, athlete)
        if is_challenge_page(driver):
            input(
                "\nCloudflare-Prüfung im Browser lösen, "
                "dann hier Enter drücken..."
            )
            continue
        if not details.get("nactionclub"):
            # Page loaded but athlete info missing: try again
            continue
        return details, best_records
    return None, None


def main():
    """
    Re-scrape all athletes that failed during the original scrape and
    write the results to OUTPUT_CSV.
    """
    athletes = load_missing_athletes()
    done_ids = load_done_ids()
    todo = [a for a in athletes if a["athlete_id"] not in done_ids]
    print(
        f"{len(athletes)} fehlgeschlagene Athleten, "
        f"{len(done_ids)} bereits erledigt, {len(todo)} offen."
    )
    if not todo:
        return

    driver = setup_visible_driver()
    driver.get(todo[0]["athlete_link"])
    input(
        "Falls eine Cloudflare-Prüfung angezeigt wird, diese im Browser "
        "lösen. Danach hier Enter drücken, um zu starten..."
    )

    write_header = not os.path.exists(OUTPUT_CSV)
    failed = []
    try:
        with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            if write_header:
                writer.writeheader()
            for i, athlete in enumerate(todo, start=1):
                details, best_records = scrape_with_challenge_handling(
                    driver, athlete
                )
                if details is None:
                    failed.append(athlete["athlete_id"])
                    print(f"[{i}/{len(todo)}] {athlete['athlete_id']}: "
                          "fehlgeschlagen")
                    continue
                base = {**athlete, "nactionclub": details["nactionclub"]}
                rows = best_records or [dict.fromkeys(RECORD_FIELDS, "")]
                for record in rows:
                    writer.writerow({**base, **record})
                f.flush()
                print(f"[{i}/{len(todo)}] {athlete['athlete_id']}: "
                      f"{len(best_records)} Bestzeiten")
    finally:
        driver.quit()

    print(f"\nFertig. Ergebnisse in {OUTPUT_CSV}")
    if failed:
        print(f"{len(failed)} Athleten fehlgeschlagen "
              f"(beim nächsten Lauf erneut versucht): {failed}")


if __name__ == "__main__":
    main()
