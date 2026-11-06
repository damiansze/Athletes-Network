#!/usr/bin/env python3
"""
Test suite for delaytest.py (test_delaytest.py).

Contains tests that verify functionality of get_athlete_list,
check_athlete_record, evaluate_delay_value, etc., including
soft-block detection and page structure.
"""

import time
import pytest
from selenium.webdriver.common.by import By

from src.delaytest import (
    get_athlete_list,
    check_athlete_record,
    evaluate_delay_value,
    SoftBlockException
)


class DummyElement:
    """
    Simulates a Selenium element with text and attributes.

    Attributes:
        _text (str): Inner text of the element.
    """

    def __init__(self, text=""):
        """
        Initialize a DummyElement.

        Args:
            text (str, optional): Text content for the element.
        """
        self._text = text

    @property
    def text(self):
        """
        str: The text of the element.
        """
        return self._text

    def get_attribute(self, attr):
        """
        Get a simulated attribute for this element.

        Args:
            attr (str): The attribute name.

        Returns:
            str: A dummy URL if 'href', otherwise empty string.
        """
        if attr == "href":
            return "http://example.com/?athleteId=123"
        return ""


class DummyAthleteRow:
    """
    Simulates an athlete row containing a link, date, and code cells.
    """

    def find_elements(self, by, value):
        """
        Simulate finding multiple elements within the row.

        Args:
            by (selenium.webdriver.common.by.By): Method of location.
            value (str): The selector value.

        Returns:
            list: Dummy elements matching the requested criteria.
        """
        if by == By.TAG_NAME and value == "a":
            return [DummyElement(text="John Doe")]
        elif by == By.CLASS_NAME and value == "date":
            return [DummyElement(text="2021-01-01")]
        elif by == By.CLASS_NAME and value == "code":
            return [DummyElement(text="ABC")]
        return []

    def find_element(self, by, value):
        """
        Simulate finding a single element within the row.

        Args:
            by (selenium.webdriver.common.by.By): Method of location.
            value (str): The selector value.

        Returns:
            DummyElement: The first matching dummy element if found.

        Raises:
            Exception: If nothing is found.
        """
        elems = self.find_elements(by, value)
        if elems:
            return elems[0]
        raise Exception("Element not found in DummyAthleteRow")


class DummyTable:
    """
    Simulates a table containing athlete rows.
    """

    def find_elements(self, by, value):
        """
        Simulate searching for rows within the table.

        Args:
            by (selenium.webdriver.common.by.By): Method of location.
            value (str): The selector value.

        Returns:
            list: A list of DummyAthleteRow if searching for athlete rows.
        """
        if by == By.XPATH and "athleteSearch" in value:
            return [DummyAthleteRow()]
        return []


class DummyDriverForAthleteList:
    """
    Dummy driver for testing get_athlete_list.

    Attributes:
        url (str): The current URL to which the driver navigated.
        page_source (str): Mock HTML content.
    """

    def __init__(self):
        """
        Initialize the dummy driver with valid page content.
        """
        self.url = ""
        self.page_source = (
            "Valid page content " * 11
        )  # Ensure length exceeds threshold.

    def get(self, url):
        """
        Simulate navigating to a URL.

        Args:
            url (str): The target URL.
        """
        self.url = url

    def find_elements(self, by, value):
        """
        Simulate finding elements on the page.

        Args:
            by (selenium.webdriver.common.by.By): Method of location.
            value (str): The selector value.

        Returns:
            list: A list of DummyTable if searching for 'athleteList'.
        """
        if by == By.CLASS_NAME and value == "athleteList":
            return [DummyTable()]
        return []

    def delete_all_cookies(self):
        """Simulate clearing cookies."""
        pass


class DummyDriverForCheckRecord:
    """
    Dummy driver for testing check_athlete_record.

    Attributes:
        page_source (str): HTML content to simulate presence/absence of
        records.
        url (str): Current URL after get() is called.
    """

    def __init__(self, page_source):
        """
        Initialize with a given page_source.

        Args:
            page_source (str): The simulated page content.
        """
        self.page_source = page_source
        self.url = ""

    def get(self, url):
        """
        Simulate navigating to a URL.

        Args:
            url (str): The target URL.
        """
        self.url = url

    def find_elements(self, by, value):
        """
        Dummy placeholder for searching.

        Args:
            by (selenium.webdriver.common.by.By): Method of location.
            value (str): The selector value.

        Returns:
            list: Always empty in this simulation.
        """
        return []

    def quit(self):
        """Simulate quitting the driver."""
        pass

    def delete_all_cookies(self):
        """Simulate clearing cookies."""
        pass


@pytest.fixture
def dummy_driver_athlete_list():
    """
    Pytest fixture that returns a DummyDriverForAthleteList for tests.

    Returns:
        DummyDriverForAthleteList: A driver preloaded with valid page content.
    """
    return DummyDriverForAthleteList()


def test_get_athlete_list(monkeypatch, dummy_driver_athlete_list):
    """
    Test get_athlete_list to ensure it correctly parses a single athlete row.

    Mocks WebDriverWait.until to return True, skipping real waits.
    """
    from selenium.webdriver.support.ui import WebDriverWait

    monkeypatch.setattr(WebDriverWait, "until", lambda self, method: True)
    athletes = get_athlete_list(dummy_driver_athlete_list)
    assert isinstance(athletes, list)
    # Expect one athlete.
    assert len(athletes) == 1
    athlete = athletes[0]
    assert athlete["athlete_id"] == "123"
    assert athlete["athlete_name"] == "John Doe"
    assert "http://example.com/" in athlete["athlete_link"]
    assert athlete["athlete_date"] == "2021-01-01"
    assert athlete["athlete_code"] == "ABC"


def test_check_athlete_record_safe(monkeypatch):
    """
    Test check_athlete_record with a page that safely indicates content is
    present, which should return True.
    """
    safe_page = "Safe content " * 20
    dummy_driver = DummyDriverForCheckRecord(safe_page)
    athlete = {
        "athlete_id": "123",
        "athlete_name": "John Doe",
        "athlete_link": "http://example.com/?athleteId=123",
    }
    monkeypatch.setattr(time, "sleep", lambda x: None)
    result = check_athlete_record(
        dummy_driver,
        athlete,
        delay=0,
        use_wait=False
    )
    assert result is True


def test_check_athlete_record_no_records(monkeypatch):
    """
    Test check_athlete_record with a page that indicates no records are found,
    which should return False.
    """
    no_records_page = (
        "Header text\nThere are no records "
        "registered for this athlete\nFooter text"
    ) * 10
    dummy_driver = DummyDriverForCheckRecord(no_records_page)
    athlete = {
        "athlete_id": "123",
        "athlete_name": "John Doe",
        "athlete_link": "http://example.com/?athleteId=123",
    }
    monkeypatch.setattr(time, "sleep", lambda x: None)
    result = check_athlete_record(
        dummy_driver,
        athlete,
        delay=0,
        use_wait=False
    )
    assert result is False


def test_check_athlete_record_softblock(monkeypatch):
    """
    Test check_athlete_record with a short page source simulating a soft block.

    Expects a SoftBlockException.
    """
    short_page = "Short content"
    dummy_driver = DummyDriverForCheckRecord(short_page)
    athlete = {
        "athlete_id": "123",
        "athlete_name": "John Doe",
        "athlete_link": "http://example.com/?athleteId=123",
    }
    monkeypatch.setattr(time, "sleep", lambda x: None)
    with pytest.raises(SoftBlockException):
        check_athlete_record(dummy_driver, athlete, delay=0, use_wait=False)


def test_evaluate_delay_value(monkeypatch):
    """
    Test evaluate_delay_value ensuring it runs driver setup, attempts
    to fetch athlete data, and returns True if no soft block occurs.
    """
    dummy_athlete = {
        "athlete_id": "123",
        "athlete_name": "John Doe",
        "athlete_link": "http://example.com/?athleteId=123",
    }
    monkeypatch.setattr(
        "src.delaytest.get_athlete_list", lambda driver: [dummy_athlete]
    )
    monkeypatch.setattr(
        "src.delaytest.check_athlete_record",
        lambda driver, athlete, delay, use_wait: True,
    )
    monkeypatch.setattr(time, "sleep", lambda x: None)

    class DummyDriver:
        """Minimal driver stub to avoid actual browser calls."""
        def quit(self):
            pass

        def delete_all_cookies(self):
            pass

    dummy_driver = DummyDriver()
    monkeypatch.setattr("src.delaytest.setup_driver", lambda: dummy_driver)
    result = evaluate_delay_value(delay=0.1, use_wait=False, test_duration=0.1)
    assert result is True
