#!/usr/bin/env python3
"""
Test suite for checking athlete data (test_check_athletes.py).

Contains various tests that simulate Selenium interactions and verify
functions from check_athletes.py.
"""

import pytest
import random
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.check_athletes import (
    setup_driver,
    extract_nation_options,
    safe_get_single_attempt,
    check_athlete_records,
    scrape_main_page,
    BlockDetectedException
)


class DummyElement:
    """
    Simulates a Selenium web element for text and attributes.

    Attributes:
        _text (str): The text contained by the element.
        _attrs (dict): The HTML attributes for this element.
    """

    def __init__(self, text="", attrs=None):
        """
        Initialize a DummyElement.

        Args:
            text (str, optional): Inner text of the element.
            attrs (dict, optional): HTML attributes of the element.
        """
        self._text = text
        self._attrs = attrs or {}

    @property
    def text(self):
        """
        str: The text of the element.
        """
        return self._text

    def get_attribute(self, attr):
        """
        Get the specified HTML attribute value.

        Args:
            attr (str): The name of the attribute.

        Returns:
            str: The value of the attribute, if found.
            Otherwise, an empty string.
        """
        if attr in self._attrs:
            return self._attrs[attr]
        if attr == "href" and "athlete" in self._text.lower():
            return ("https://www.swimrankings.net/index.php?"
                    "page=athleteDetail&athleteId=123")
        if attr == "value" and self._text != "All Nations":
            return str(random.randint(1, 100))
        return ""


class DummyOption(DummyElement):
    """
    Simulates an <option> element in a select dropdown.

    Inherits from DummyElement to store both text and value attributes.
    """

    def __init__(self, value, text):
        """
        Initialize a DummyOption.

        Args:
            value (str): The 'value' attribute for the option.
            text (str): The display text for the option element.
        """
        super().__init__(text=text, attrs={"value": value})


class DummyAthleteRow:
    """
    Simulates a row in the athlete table.

    Contains an <a> tag with athlete data, and placeholders for date and code.
    """

    def __init__(self, athlete_name="John Doe", athlete_id="123"):
        """
        Initialize a DummyAthleteRow.

        Args:
            athlete_name (str, optional): Display name for the athlete.
            athlete_id (str, optional): ID value appended to the athlete's
                link.
        """
        self.athlete_name = athlete_name
        self.athlete_id = athlete_id

    def find_elements(self, by, value):
        """
        Simulates finding all matching elements within this row.

        Args:
            by (selenium.webdriver.common.by.By): The method of location
                (TAG_NAME, CLASS_NAME, etc.).
            value (str): The selector value.

        Returns:
            list: A list of DummyElements that match the requested criteria.
        """
        if by == By.TAG_NAME and value == "a":
            return [
                DummyElement(
                    text=self.athlete_name,
                    attrs={
                        "href": (f"https://www.swimrankings.net/index.php?"
                                 f"page=athleteDetail&"
                                 f"athleteId={self.athlete_id}")
                    },
                )
            ]
        elif by == By.CLASS_NAME and value == "date":
            # Expected value updated to match assertions in scrape_main_page
            return [DummyElement(text="2023-01-01")]
        elif by == By.CLASS_NAME and value == "code":
            return [DummyElement(text="ABC123")]
        return []

    def find_element(self, by, value):
        """
        Simulates finding a single element within this row.

        Args:
            by (selenium.webdriver.common.by.By): The method of location.
            value (str): The selector value.

        Returns:
            DummyElement: The first matching element.

        Raises:
            Exception: If the element is not found in this row.
        """
        elems = self.find_elements(by, value)
        if elems:
            return elems[0]
        raise Exception("Element not found in DummyAthleteRow")


class DummyTable:
    """
    Simulates a table containing a list of athlete rows.
    """

    def __init__(self, num_athletes=3):
        """
        Initialize a DummyTable.

        Args:
            num_athletes (int, optional): Number of athlete rows in the table.
        """
        self.num_athletes = num_athletes
        self.athlete_rows = [
            DummyAthleteRow(f"Athlete {i}", f"{100 + i}")
            for i in range(1, num_athletes + 1)
        ]

    def find_elements(self, by, value):
        """
        Simulate finding elements in the table by XPath.

        Args:
            by (selenium.webdriver.common.by.By): The method of location.
            value (str): The selector value.

        Returns:
            list: A list of DummyAthleteRow objects if the query matches
            'athleteSearch'.
        """
        if by == By.XPATH and "athleteSearch" in value:
            return self.athlete_rows
        return []


class DummyDriver:
    """
    A base dummy Selenium driver with common methods to simulate
    get, quit, etc.

    Attributes:
        url (str): The current URL loaded in the driver.
        page_source (str): The simulated HTML of the page.
        options (dict): Misc options or configurations.
        cdp_commands (list): Tracks any executed CDP commands.
    """

    def __init__(self):
        """Initialize a DummyDriver with default values."""
        self.url = ""
        self.page_source = ""
        self.options = {}
        self.cdp_commands = []

    def get(self, url):
        """
        Simulate navigating to a URL.

        Args:
            url (str): The URL to "navigate" to.
        """
        self.url = url

    def quit(self):
        """Simulate quitting the driver."""
        pass

    def execute_script(self, script):
        """
        Simulate executing a JavaScript snippet.

        Args:
            script (str): The JS code to run.

        Returns:
            str or None: Returns "complete" if checking document readiness,
            else None.
        """
        if script == "return document.readyState":
            return "complete"
        return None

    def execute_cdp_cmd(self, command, params):
        """
        Simulate executing a Chrome DevTools Protocol command.

        Args:
            command (str): The CDP command name.
            params (dict): Parameters for the CDP command.
        """
        self.cdp_commands.append((command, params))

    def find_elements(self, by, value):
        """
        Default empty search method.

        Args:
            by (selenium.webdriver.common.by.By): The method of location.
            value (str): The selector value.

        Returns:
            list: Empty list by default, can be overridden in subclasses.
        """
        return []


class DummyDriverForNations(DummyDriver):
    """
    Simulates a Selenium driver for extracting nation options.

    Attributes:
        num_nations (int): Number of nations to simulate.
    """

    def __init__(self, num_nations=5):
        """
        Initialize a dummy driver for nation options.

        Args:
            num_nations (int, optional): Number of test nations to generate.
        """
        super().__init__()
        self.num_nations = num_nations

    def find_element(self, by, value):
        """
        Simulate finding a single element by name.

        Args:
            by (selenium.webdriver.common.by.By): The method of location.
            value (str): The selector value.

        Returns:
            DummyDriverForNations: Returns self if simulating a select element,
            else None.
        """
        if by == By.NAME and value == "nationId":
            return self
        return None

    def find_elements(self, by, value):
        """
        Simulate finding multiple elements.

        Args:
            by (selenium.webdriver.common.by.By): The method of location.
            value (str): The selector value.

        Returns:
            list: A list of DummyOption objects if searching for "option".
        """
        if by == By.TAG_NAME and value == "option":
            options = [DummyOption("-1", "All Nations")]
            options.extend(
                [
                    DummyOption(str(i), f"Nation {i}")
                    for i in range(1, self.num_nations + 1)
                ]
            )
            return options
        return []


class DummyDriverForMainPage(DummyDriver):
    """
    Simulates a Selenium driver for testing scrape_main_page.

    Attributes:
        num_tables (int): Number of athlete tables on the page.
        athletes_per_table (int): Number of athletes in each table.
        tables (list): Stored dummy tables containing athlete rows.
    """

    def __init__(self, num_tables=1, athletes_per_table=3):
        """
        Initialize a dummy driver with simulated athlete tables.

        Args:
            num_tables (int, optional): Number of tables to simulate.
            athletes_per_table (int, optional): Athletes per table.
        """
        super().__init__()
        self.num_tables = num_tables
        self.athletes_per_table = athletes_per_table
        self.tables = [
            DummyTable(athletes_per_table) for _ in range(num_tables)
        ]

    def find_elements(self, by, value):
        """
        Override find_elements to return dummy athlete tables.

        Args:
            by (selenium.webdriver.common.by.By): The method of location.
            value (str): The selector value.

        Returns:
            list: Returns the dummy tables if matching 'athleteList'.
        """
        if by == By.CLASS_NAME and value == "athleteList":
            return self.tables
        return []


class DummyDriverForRecords(DummyDriver):
    """
    Simulates a Selenium driver for checking athlete records.

    Attributes:
        has_records (bool): Whether the page source indicates records
            are present.
    """

    def __init__(self, has_records=True, page_length=1000):
        """
        Initialize the dummy driver for checking athlete records.

        Args:
            has_records (bool, optional): If False, page simulates no records.
            page_length (int, optional): Length of the page_source string.
        """
        super().__init__()
        self.has_records = has_records
        if not has_records:
            self.page_source = (
                "X" * page_length
                + "There are no records registered for this athlete"
                + "X" * page_length
            )
        else:
            self.page_source = (
                "X" * page_length
                + "<table class='athleteRecord'></table>"
                + "X" * page_length
            )

    def find_element(self, by, value):
        """
        Simulate finding a single element.

        Args:
            by (selenium.webdriver.common.by.By): The method of location.
            value (str): The selector value.

        Returns:
            DummyElement or self: The requested simulated element or
            self if found.

        Raises:
            Exception: If 'athleteRecord' is not found when has_records=False.
        """
        if by == By.CLASS_NAME and value == "athleteRecord":
            if not self.has_records:
                raise Exception("No athlete record table found")
            return self
        if by == By.TAG_NAME and value == "body":
            return DummyElement(text="body")
        raise Exception(
            f"Element not found in DummyDriverForRecords: {by}, {value}"
        )

    def find_elements(self, by, value):
        """
        Simulate finding multiple elements.

        Args:
            by (selenium.webdriver.common.by.By): The method of location.
            value (str): The selector value.

        Returns:
            list: A list with one DummyElement if has_records is True,
            else an empty list.
        """
        if by == By.XPATH and "athleteRecord0" in value:
            return [DummyElement()] if self.has_records else []
        return []


@pytest.fixture
def mock_chrome_options():
    """
    Provide a mock ChromeOptions class for testing setup_driver.
    """
    class MockChromeOptions:
        """
        A mock replacement for selenium.webdriver.ChromeOptions.
        """

        def __init__(self):
            self.arguments = []
            self.experimental_options = {}

        def add_argument(self, arg):
            """
            Simulate adding a command-line argument to Chrome.

            Args:
                arg (str): The argument to add (e.g. '--headless').
            """
            self.arguments.append(arg)

        def add_experimental_option(self, name, value):
            """
            Simulate adding an experimental option to Chrome.

            Args:
                name (str): The option name.
                value (any): The option value.
            """
            self.experimental_options[name] = value

    return MockChromeOptions()


@pytest.fixture
def dummy_driver_nations():
    """
    Pytest fixture providing a DummyDriverForNations.

    Returns:
        DummyDriverForNations: A dummy driver with a default number of nations.
    """
    return DummyDriverForNations()


@pytest.fixture
def dummy_driver_main_page():
    """
    Pytest fixture providing a DummyDriverForMainPage.

    Returns:
        DummyDriverForMainPage: A dummy driver with one table and three
        athletes by default.
    """
    return DummyDriverForMainPage()


@pytest.fixture
def dummy_driver_records_yes():
    """
    Pytest fixture for a driver indicating the athlete has records.

    Returns:
        DummyDriverForRecords: A driver with has_records=True.
    """
    return DummyDriverForRecords(has_records=True)


@pytest.fixture
def dummy_driver_records_no():
    """
    Pytest fixture for a driver indicating the athlete has no records.

    Returns:
        DummyDriverForRecords: A driver with has_records=False.
    """
    return DummyDriverForRecords(has_records=False)


@pytest.fixture
def dummy_driver_records_error():
    """
    Pytest fixture for a driver that simulates an error page.

    Returns:
        DummyDriverForRecords: A driver with has_records=False and shorter
        page source.
    """
    return DummyDriverForRecords(has_records=False, page_length=100)


def test_setup_driver(monkeypatch, mock_chrome_options):
    """
    Test setup_driver with mocked Chrome options.

    Checks that a driver is returned with the expected arguments and options.
    """
    monkeypatch.setattr(
        "src.check_athletes.webdriver.ChromeOptions",
        lambda: mock_chrome_options
    )
    monkeypatch.setattr(
        "src.check_athletes.webdriver.Chrome", lambda options: DummyDriver()
    )
    monkeypatch.setattr("src.check_athletes.random.choice", lambda lst: lst[0])
    driver = setup_driver()
    assert isinstance(driver, DummyDriver)
    assert any("--headless" in arg for arg in mock_chrome_options.arguments)
    assert any("--no-sandbox" in arg for arg in mock_chrome_options.arguments)
    assert any("user-agent=" in arg for arg in mock_chrome_options.arguments)
    assert "excludeSwitches" in mock_chrome_options.experimental_options
    assert mock_chrome_options.experimental_options["excludeSwitches"] == [
        "enable-automation"
    ]


def test_extract_nation_options(monkeypatch, dummy_driver_nations):
    """
    Test extract_nation_options with a dummy driver.

    Verifies that the correct number of nations is parsed.
    """
    monkeypatch.setattr(WebDriverWait, "until", lambda self, method: True)
    base_url = "https://www.swimrankings.net/index.php?page=athleteSelect"
    nations = extract_nation_options(dummy_driver_nations, base_url)
    assert isinstance(nations, list)
    assert len(nations) == dummy_driver_nations.num_nations
    for nation in nations:
        assert "nation_id" in nation
        assert "nation_name" in nation
        assert nation["nation_name"].startswith("Nation ")


def test_safe_get_single_attempt_success(monkeypatch, dummy_driver_nations):
    """
    Test safe_get_single_attempt for a successful page load scenario.

    Checks that the driver's URL is updated.
    """
    monkeypatch.setattr(WebDriverWait, "until", lambda self, method: True)
    safe_get_single_attempt(
        dummy_driver_nations,
        "https://example.com",
        EC.presence_of_element_located((By.TAG_NAME, "body")),
    )
    assert dummy_driver_nations.url == "https://example.com"


def test_safe_get_single_attempt_failure(monkeypatch, dummy_driver_nations):
    """
    Test safe_get_single_attempt for a navigation failure scenario.

    Expects a BlockDetectedException due to a mock TimeoutException.
    """

    def mock_until_fail(self, method):
        raise TimeoutException("Timeout waiting for element")

    monkeypatch.setattr(WebDriverWait, "until", mock_until_fail)
    with pytest.raises(BlockDetectedException):
        safe_get_single_attempt(
            dummy_driver_nations,
            "https://example.com",
            EC.presence_of_element_located((By.TAG_NAME, "body")),
        )


def test_check_athlete_records_with_records(
    monkeypatch, dummy_driver_records_yes
):
    """
    Test check_athlete_records when the athlete has records.

    Expects True.
    """
    monkeypatch.setattr(
        "src.check_athletes.safe_get_single_attempt",
        lambda *args, **kwargs: None
    )
    athlete = {
        "athlete_id": "123",
        "athlete_name": "John Doe",
        "athlete_link": "https://www.swimrankings.net/index.php?"
                        "page=athleteDetail&athleteId=123",
    }
    result = check_athlete_records(dummy_driver_records_yes, athlete)
    assert result is True


def test_check_athlete_records_without_records(
    monkeypatch, dummy_driver_records_no
):
    """
    Test check_athlete_records when the athlete has no records.

    Expects False.
    """
    monkeypatch.setattr(
        "src.check_athletes.safe_get_single_attempt",
        lambda *args, **kwargs: None
    )
    athlete = {
        "athlete_id": "123",
        "athlete_name": "John Doe",
        "athlete_link": "https://www.swimrankings.net/index.php?"
                        "page=athleteDetail&athleteId=123",
    }
    result = check_athlete_records(dummy_driver_records_no, athlete)
    assert result is False


def test_check_athlete_records_error_page(
    monkeypatch, dummy_driver_records_error
):
    """
    Test check_athlete_records with a page that indicates a soft block
    or error.

    This test ensures it doesn't crash, but calls sys.exit (mocked).
    """
    monkeypatch.setattr(
        "src.check_athletes.safe_get_single_attempt",
        lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        "src.check_athletes.sys.exit", lambda code: None
    )  # Prevent exit
    athlete = {
        "athlete_id": "123",
        "athlete_name": "John Doe",
        "athlete_link": "https://www.swimrankings.net/index.php?"
                        "page=athleteDetail&athleteId=123",
    }
    check_athlete_records(dummy_driver_records_error, athlete)


def test_scrape_main_page(monkeypatch, dummy_driver_main_page):
    """
    Test scrape_main_page with a dummy driver to verify the correct
    athlete data is extracted.
    """
    monkeypatch.setattr(
        "src.check_athletes.safe_get_single_attempt",
        lambda *args, **kwargs: None
    )
    monkeypatch.setattr("src.check_athletes.time.sleep", lambda x: None)
    main_url = (
        "https://www.swimrankings.net/index.php?"
        "page=athleteSelect&selectPage=TOP100_MEN_ALL&nationId=1"
    )
    athletes = scrape_main_page(dummy_driver_main_page, main_url)
    assert isinstance(athletes, list)
    expected_count = (
        dummy_driver_main_page.num_tables
        * dummy_driver_main_page.athletes_per_table
    )
    assert len(athletes) == expected_count
    for athlete in athletes:
        assert "athlete_id" in athlete
        assert "athlete_name" in athlete
        assert "athlete_link" in athlete
        assert "athlete_date" in athlete
        assert "athlete_code" in athlete
        assert athlete["athlete_date"] == "2023-01-01"
        assert athlete["athlete_code"] == "ABC123"


def test_main_function(monkeypatch):
    """
    Test the main function in check_athletes.py with mocked dependencies.

    Ensures that it runs to completion without errors.
    """
    mock_driver = DummyDriver()
    mock_nations = [{"nation_id": "1", "nation_name": "Test Nation"}]
    monkeypatch.setattr("src.check_athletes.setup_driver", lambda: mock_driver)
    monkeypatch.setattr(
        "src.check_athletes.extract_nation_options", lambda *args: mock_nations
    )
    monkeypatch.setattr(
        "src.check_athletes.scrape_main_page",
        lambda *args: [
            {
                "athlete_id": "123",
                "athlete_name": "Test Athlete",
                "athlete_link": "https://example.com",
            }
        ],
    )
    monkeypatch.setattr(
        "src.check_athletes.check_athlete_records",
        lambda *args: True
    )
    monkeypatch.setattr(
        "src.check_athletes.time.sleep", lambda x: None
    )
    monkeypatch.setattr(
        "src.check_athletes.tqdm",
        lambda iterable, desc: iterable
    )
    from src.check_athletes import main

    main()  # Should run without errors
