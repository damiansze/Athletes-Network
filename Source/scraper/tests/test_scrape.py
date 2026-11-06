#!/usr/bin/env python3
"""
Tests for scrape.py functionality (test_scrape.py).

Includes setup_driver, safe_get, extract_nation_options, scrape_main_page,
scrape_athlete_details, and combine_csv tests, using dummy classes to simulate
Selenium behavior.
"""

import time
from urllib.parse import urlparse, parse_qs
from selenium.webdriver.common.by import By
from scripts.scrape import (
    setup_driver,
    safe_get,
    extract_nation_options,
    scrape_main_page,
    scrape_athlete_details,
    combine_csv,
)


class DummyElement:
    """
    Simulates a Selenium WebElement, supporting text, attributes, and children.
    """

    def __init__(self, text="", attributes=None, children=None):
        """
        Initialize a DummyElement.

        Args:
            text (str, optional): The text content of the element.
            attributes (dict, optional): HTML attributes (e.g., href).
            children (dict, optional): A dict for nested child elements.
        """
        self._text = text
        self._attributes = attributes or {}
        self._children = children or {}

    @property
    def text(self):
        """
        str: The text of this element.
        """
        return self._text

    def get_attribute(self, key):
        """
        Retrieve a specific attribute from this element.

        Args:
            key (str): The attribute name.

        Returns:
            str: The attribute value, or an empty string if not found.
        """
        return self._attributes.get(key, "")

    def find_element(self, by, value):
        """
        Simulate finding a single child element.

        Args:
            by (selenium.webdriver.common.by.By): The location strategy.
            value (str): The locator string.

        Returns:
            DummyElement: The child element if found.

        Raises:
            Exception: If no matching child element is found.
        """
        if by == By.TAG_NAME and value == "a" and "a" in self._children:
            return self._children["a"][0]
        raise Exception("Element not found")

    def find_elements(self, by, value):
        """
        Simulate finding multiple child elements.

        Args:
            by (selenium.webdriver.common.by.By): The location strategy.
            value (str): The locator string.

        Returns:
            list of DummyElement: The matching child elements.
        """
        if by == By.TAG_NAME and value == "a":
            return self._children.get("a", [])
        return []


class DummyRowValid:
    """
    Represents a row with valid athlete data: name, href, date, code.
    """

    def find_elements(self, by, value):
        """
        Simulate finding multiple elements in this row.

        Args:
            by (selenium.webdriver.common.by.By): Locator strategy.
            value (str): Selector value.

        Returns:
            list of DummyElement: The anchor(s) if found.
        """
        if by == By.TAG_NAME and value == "a":
            anchor = DummyElement(
                text="Jane Doe",
                attributes={"href": "http://example.com/?athleteId=456"},
            )
            return [anchor]
        return []

    def find_element(self, by, value):
        """
        Simulate finding a single element in this row.

        Args:
            by (selenium.webdriver.common.by.By): Locator strategy.
            value (str): Selector value.

        Returns:
            DummyElement: The matching element if found.

        Raises:
            Exception: If no element is found for the given strategy.
        """
        if by == By.CLASS_NAME and value == "name":
            anchor = DummyElement(
                text="Jane Doe",
                attributes={"href": "http://example.com/?athleteId=456"},
            )
            return DummyElement(children={"a": [anchor]})
        elif by == By.CLASS_NAME and value == "date":
            return DummyElement(text="2021-02-01")
        elif by == By.CLASS_NAME and value == "code":
            return DummyElement(text="DEF")
        raise Exception("Element not found")


class DummyBestRow:
    """
    Represents a row in the athleteBest table, containing best-record columns.
    """

    def find_elements(self, by, value):
        """
        Simulate finding multiple columns (<td> elements) in this row.

        Args:
            by (selenium.webdriver.common.by.By): Locator strategy.
            value (str): Selector value.

        Returns:
            list of DummyElement: The columns if 'td' is requested.
        """
        if by == By.TAG_NAME and value == "td":
            return [
                DummyElement(text="50m Freestyle"),
                DummyElement(text="Short Course"),
                DummyElement(text="23.45"),
                DummyElement(text="BC456"),
                DummyElement(text="2021-03-01"),
                DummyElement(text="Toronto"),
                DummyElement(text="Record Holder"),
            ]
        return []


class DummyBestTable:
    """
    Represents a table containing athleteBest rows.
    """

    def find_elements(self, by, value):
        """
        Simulate finding rows within the best-record table.

        Args:
            by (selenium.webdriver.common.by.By): Locator strategy.
            value (str): Selector value.

        Returns:
            list of DummyBestRow: The dummy rows if matched.
        """
        if by == By.XPATH and "athleteBest" in value:
            return [DummyBestRow()]
        return []


class DummyTable:
    """
    Represents a table containing athleteSearch rows.
    """

    def __init__(self, rows):
        """
        Initialize a dummy table with specific row objects.

        Args:
            rows (list): The row objects for this table.
        """
        self.rows = rows

    def find_elements(self, by, value):
        """
        Simulate finding rows in this table.

        Args:
            by (selenium.webdriver.common.by.By): Locator strategy.
            value (str): Selector value.

        Returns:
            list: The matching rows if 'athleteSearch' is in the XPath.
        """
        if by == By.XPATH and "athleteSearch" in value:
            return self.rows
        return []


class DummyDriver:
    """
    A mock Selenium driver for testing scraping functions.
    """

    def __init__(self):
        """
        Initialize the dummy driver with a preset page_source.
        """
        self.url = None
        self.page_source = "Valid page content " * 11

    def delete_all_cookies(self):
        """Simulate clearing cookies."""
        pass

    def get(self, url):
        """
        Simulate navigating to a URL.

        Args:
            url (str): The target URL.
        """
        self.url = url

    def find_elements(self, by, value):
        """
        Simulate finding elements by class name.

        Args:
            by (selenium.webdriver.common.by.By): Locator strategy.
            value (str): Selector value.

        Returns:
            list: A list of dummy objects if matched.
        """
        if by == By.CLASS_NAME and value == "athleteList":
            return [DummyTable([DummyRowValid()])]
        if by == By.CLASS_NAME and value == "athleteBest":
            return [DummyBestTable()]
        return []

    def find_element(self, by, value):
        """
        Simulate finding a single element by tag name or other strategies.

        Args:
            by (selenium.webdriver.common.by.By): Locator strategy.
            value (str): Selector value.

        Returns:
            DummyElement or a nested dummy class instance, if matched.

        Raises:
            Exception: If no element matches the request.
        """
        if by == By.TAG_NAME and value == "body":
            return DummyElement(text="body")
        if by == By.NAME and value == "nationId":

            class DummySelect:
                """
                A select element with two option elements (Worldwide, Canada).
                """

                def __init__(self):
                    self.options = [
                        DummyElement(
                            text="Worldwide",
                            attributes={"value": "-1"}
                        ),
                        DummyElement(
                            text="Canada",
                            attributes={"value": "501"}
                        ),
                    ]

                def find_elements(self, by, value):
                    if by == By.TAG_NAME and value == "option":
                        return self.options
                    return []

            return DummySelect()
        if by == By.ID and value == "athleteinfo":

            class DummyInfo:
                """
                A dummy athlete info div containing a nationclub element.
                """

                def find_element(self, by, value):
                    if by == By.ID and value == "nationclub":
                        return DummyElement(text="Canada Club")
                    raise Exception("Element not found")

            return DummyInfo()
        if by == By.CLASS_NAME and value == "athleteBest":
            return DummyBestTable()
        raise Exception("Element not found")

    def execute_script(self, script):
        """
        Simulate executing JS code, e.g., checking document.readyState.

        Args:
            script (str): The JavaScript snippet.

        Returns:
            str or None: "complete" if checking the ready state, else None.
        """
        if script == "return document.readyState":
            return "complete"
        return None

    def quit(self):
        """Simulate closing the driver."""
        pass


def test_setup_driver_scrape():
    """
    Test that setup_driver returns a valid driver instance
    and can be quit cleanly.
    """
    driver = setup_driver()
    assert driver is not None
    try:
        driver.quit()
    except Exception:
        pass


def test_safe_get_scrape(monkeypatch):
    """
    Test safe_get to ensure it loads the expected URL and
    doesn't raise exceptions.
    """
    dummy = DummyDriver()
    monkeypatch.setattr(time, "sleep", lambda x: None)
    safe_get(dummy, "http://dummy_url")
    assert dummy.url == "http://dummy_url"


def test_extract_nation_options_scrape():
    """
    Test extract_nation_options to confirm it detects one valid nation
    (Canada) from the dummy driver.
    """
    dummy_driver = DummyDriver()
    nations = extract_nation_options(dummy_driver, "http://dummy_nation_url")
    # Expect one valid nation (Canada).
    assert len(nations) == 1
    nation = nations[0]
    assert nation["nation_id"] == "501"
    assert nation["nation_name"] == "Canada"


def test_scrape_main_page_scrape():
    """
    Test scrape_main_page to ensure it returns one athlete with ID=456
    from the dummy driver.
    """
    dummy_driver = DummyDriver()
    athletes, is_empty = scrape_main_page(
        dummy_driver, "http://dummy_main_url"
    )
    assert len(athletes) == 1
    athlete = athletes[0]
    parsed = urlparse(athlete["athlete_link"])
    qs = parse_qs(parsed.query)
    assert qs.get("athleteId", [""])[0] == "456"
    assert not is_empty


def test_scrape_athlete_details_scrape():
    """
    Test scrape_athlete_details to confirm best records and
    club info are extracted.
    """
    dummy_driver = DummyDriver()
    athlete = {
        "athlete_id": "456",
        "athlete_name": "Jane Doe",
        "athlete_link": "http://example.com/?athleteId=456",
    }
    details, best_records = scrape_athlete_details(dummy_driver, athlete)
    assert details.get("nactionclub") == "Canada Club"
    assert len(best_records) == 1
    record = best_records[0]
    assert record["event"] == "50m Freestyle"
    assert record["course"] == "Short Course"
    assert record["time"] == "23.45"


def test_combine_csv(tmp_path):
    """
    Test combine_csv to verify it merges multiple CSV files
    into a single master CSV.
    """
    file1 = tmp_path / "file1.csv"
    file2 = tmp_path / "file2.csv"
    fieldnames = ["col1", "col2"]
    data1 = [{"col1": "A", "col2": "1"}]
    data2 = [{"col1": "B", "col2": "2"}]
    for f, data in [(file1, data1), (file2, data2)]:
        with open(f, "w", newline="", encoding="utf-8") as wf:
            import csv

            writer = csv.DictWriter(wf, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    master_csv = tmp_path / "master.csv"
    combine_csv(str(master_csv), [str(file1), str(file2)], fieldnames)

    with open(master_csv, "r", newline="", encoding="utf-8") as mf:
        import csv
        reader = csv.DictReader(mf)
        rows = list(reader)
    assert len(rows) == 2
