import time
from abc import ABC

from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    MoveTargetOutOfBoundsException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.utils.config import Config
from src.utils.constants import DOWNLOADS_DIR


class CoreBrowser(ABC):
    MAX_TRIES = 50
    DELAY = 0.5
    IGNORED_EXCEPTIONS = (
        ElementClickInterceptedException,
        ElementNotInteractableException,
        MoveTargetOutOfBoundsException,
        NoSuchElementException,
        StaleElementReferenceException,
    )

    def __init__(self, url: str):
        load_dotenv()
        self.driver = self._get_web_driver()
        self.driver.get(url)

    def _login(self) -> None:
        """Performs login into the system"""

    def _enter_username(self) -> None:
        """Enters the username into the login form"""

    def _enter_password(self) -> None:
        """Enters the password into the login form"""

    def _get_web_driver(self) -> webdriver.Firefox:
        """Configures and returns an instance of the Firefox WebDriver"""
        options = webdriver.FirefoxOptions()
        config = Config()
        if config.headless_mode:
            options.add_argument("-headless")
        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.dir", str(DOWNLOADS_DIR))

        driver = webdriver.Firefox(options=options)
        driver.implicitly_wait(self.DELAY)

        return driver

    def close_driver(self):
        """Closes the web driver"""
        self.driver.quit()

    def click_element(
        self,
        selector,
        selector_type=By.XPATH,
        delay=DELAY,
        ignored_exceptions=IGNORED_EXCEPTIONS,
        max_tries=MAX_TRIES,
    ):
        """Clicks on an element on the page"""
        self.retry_func(
            lambda: self._click_element_helper(
                selector, selector_type, delay, ignored_exceptions
            ),
            max_tries,
        )

    def _click_element_helper(
        self,
        selector,
        selector_type=By.XPATH,
        delay=DELAY,
        ignored_exceptions=IGNORED_EXCEPTIONS,
    ):
        """Helper method to click on an element, waiting for its presence"""
        WebDriverWait(self.driver, delay, ignored_exceptions=ignored_exceptions).until(
            EC.presence_of_element_located((selector_type, selector))
        ).click()

    def send_keys(
        self,
        selector,
        keys,
        selector_type=By.XPATH,
        delay=DELAY,
        ignored_exceptions=IGNORED_EXCEPTIONS,
        max_tries=MAX_TRIES,
    ):
        """Sends keys to an element on the page"""
        self.retry_func(
            lambda: self._send_keys_helper(
                selector, keys, selector_type, delay, ignored_exceptions
            ),
            max_tries,
        )

    def _send_keys_helper(
        self,
        selector,
        keys,
        selector_type=By.XPATH,
        delay=DELAY,
        ignored_exceptions=IGNORED_EXCEPTIONS,
    ):
        """Helper method to send keys to an element, waiting for its presence"""
        WebDriverWait(self.driver, delay, ignored_exceptions=ignored_exceptions).until(
            EC.presence_of_element_located((selector_type, selector))
        ).send_keys(keys)

    def right_click_element(
        self,
        selector,
        selector_type=By.XPATH,
        delay=DELAY,
        ignored_exceptions=IGNORED_EXCEPTIONS,
        max_tries=MAX_TRIES,
    ):
        """Right-clicks on an element on the page"""
        self.retry_func(
            lambda: self._right_click_element_helper(
                selector, selector_type, delay, ignored_exceptions
            ),
            max_tries,
        )

    def _right_click_element_helper(
        self,
        selector,
        selector_type=By.XPATH,
        delay=DELAY,
        ignored_exceptions=IGNORED_EXCEPTIONS,
    ):
        """Helper method to right-click on an element, waiting for its presence"""
        ActionChains(self.driver).context_click(
            WebDriverWait(
                self.driver, delay, ignored_exceptions=ignored_exceptions
            ).until(EC.presence_of_element_located((selector_type, selector)))
        ).perform()

    def select_and_send_keys(
        self,
        selector,
        keys,
        selector_type=By.XPATH,
        delay=DELAY,
        ignored_exceptions=IGNORED_EXCEPTIONS,
        max_tries=MAX_TRIES,
    ):
        """Selects and sends keys to an element on the page"""
        if isinstance(keys, list):
            for i, key in enumerate(keys):
                element_selector = f"({selector})[{i + 1}]"
                self.retry_func(
                    lambda: self._select_and_send_keys_helper(
                        element_selector,
                        key,
                        selector_type,
                        delay,
                        ignored_exceptions,
                    ),
                    max_tries,
                )
        else:
            self.retry_func(
                lambda: self._select_and_send_keys_helper(
                    selector,
                    keys,
                    selector_type,
                    delay,
                    ignored_exceptions,
                ),
                max_tries,
            )

    def _select_and_send_keys_helper(
        self,
        selector,
        keys,
        selector_type=By.XPATH,
        delay=DELAY,
        ignored_exceptions=IGNORED_EXCEPTIONS,
    ):
        """Helper method to select and send keys to an element, waiting for its presence"""
        ActionChains(self.driver).context_click(
            WebDriverWait(
                self.driver, delay, ignored_exceptions=ignored_exceptions
            ).until(EC.presence_of_element_located((selector_type, selector)))
        ).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).send_keys(
            keys
        ).perform()

    def wait_desappear(
        self,
        selector,
        selector_type=By.XPATH,
        delay=30,
        ignored_exceptions=IGNORED_EXCEPTIONS,
        max_tries=10,
    ):
        """Waits until an element disappears from the page"""
        return self.retry_func(
            lambda: self._wait_desappear_helper(
                selector, selector_type, delay, ignored_exceptions
            ),
            max_tries,
        )

    def _wait_desappear_helper(
        self,
        selector,
        selector_type=By.XPATH,
        delay=30,
        ignored_exceptions=IGNORED_EXCEPTIONS,
    ):
        """Helper method to wait until an element disappears from the page"""
        WebDriverWait(self.driver, delay).until(
            EC.invisibility_of_element_located((selector_type, selector))
        )

    def move_to_element(
        self,
        selector,
        selector_type=By.XPATH,
        delay=DELAY,
        ignored_exceptions=IGNORED_EXCEPTIONS,
        max_tries=MAX_TRIES,
    ):
        """Moves the mouse cursor to an element on the page"""
        self.retry_func(
            lambda: self._move_to_element_helper(
                selector, selector_type, delay, ignored_exceptions
            ),
            max_tries,
        )

    def _move_to_element_helper(
        self,
        selector,
        selector_type=By.XPATH,
        delay=DELAY,
        ignored_exceptions=IGNORED_EXCEPTIONS,
    ):
        """Helper method to move the mouse cursor to an element, waiting for its presence"""
        ActionChains(self.driver).move_to_element(
            WebDriverWait(
                self.driver, delay, ignored_exceptions=ignored_exceptions
            ).until(EC.presence_of_element_located((selector_type, selector)))
        ).perform()

    def retry_func(self, func, max_tries=MAX_TRIES):
        """Retries a function until it succeeds or reaches the maximum number of attempts"""
        for i in range(max_tries):
            try:
                time.sleep(self.DELAY)
                return func()
            except Exception:
                time.sleep(self.DELAY)
                if i >= max_tries - 1:
                    return
