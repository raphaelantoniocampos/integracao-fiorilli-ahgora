import time
import logging
from abc import ABC
from typing import Callable, Any, Union, List

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

from app.core.config import settings

logger = logging.getLogger(__name__)


class BaseBrowser(ABC):
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
        self.driver = self._get_web_driver()
        if url:
            self.driver.get(url)

    def _get_web_driver(self) -> webdriver.Firefox:
        options = webdriver.FirefoxOptions()
        if settings.HEADLESS_MODE:
            options.add_argument("-headless")

        # Ensure download directory exists
        settings.DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.dir", str(settings.DOWNLOADS_DIR))

        driver = webdriver.Firefox(options=options)
        driver.implicitly_wait(self.DELAY)
        return driver

    def close_driver(self):
        try:
            self.driver.quit()
        except Exception:
            pass

    def retry_func(self, func: Callable[[], Any], max_tries: int = MAX_TRIES) -> Any:
        error = None
        for i in range(max_tries):
            try:
                time.sleep(self.DELAY)
                return func()
            except Exception as e:
                error = e
                if i >= max_tries - 1:
                    logger.error(f"Failed after {max_tries} attempts: {e}")
                    raise e
                time.sleep(self.DELAY)
        if error:
            raise error

    def click_element(
        self,
        selector: str,
        selector_type=By.XPATH,
        delay=DELAY,
        ignored_exceptions=IGNORED_EXCEPTIONS,
        max_tries=MAX_TRIES,
    ):
        self.retry_func(
            lambda: self._click_element_helper(
                selector, selector_type, delay, ignored_exceptions
            ),
            max_tries,
        )

    def _click_element_helper(
        self,
        selector,
        selector_type,
        delay,
        ignored_exceptions,
    ):
        WebDriverWait(self.driver, delay, ignored_exceptions=ignored_exceptions).until(
            EC.presence_of_element_located((selector_type, selector))
        ).click()

    def send_keys(
        self,
        selector: str,
        keys: str,
        selector_type=By.XPATH,
        delay=DELAY,
        ignored_exceptions=IGNORED_EXCEPTIONS,
        max_tries=MAX_TRIES,
    ):
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
        selector_type,
        delay,
        ignored_exceptions,
    ):
        WebDriverWait(self.driver, delay, ignored_exceptions=ignored_exceptions).until(
            EC.presence_of_element_located((selector_type, selector))
        ).send_keys(keys)

    def right_click_element(
        self,
        selector: str,
        selector_type=By.XPATH,
        delay=DELAY,
        ignored_exceptions=IGNORED_EXCEPTIONS,
        max_tries=MAX_TRIES,
    ):
        self.retry_func(
            lambda: self._right_click_element_helper(
                selector, selector_type, delay, ignored_exceptions
            ),
            max_tries,
        )

    def _right_click_element_helper(
        self,
        selector,
        selector_type,
        delay,
        ignored_exceptions,
    ):
        ActionChains(self.driver).context_click(
            WebDriverWait(
                self.driver, delay, ignored_exceptions=ignored_exceptions
            ).until(EC.presence_of_element_located((selector_type, selector)))
        ).perform()

    def select_and_send_keys(
        self,
        selector: str,
        keys: Union[str, List[str]],
        selector_type=By.XPATH,
        delay=DELAY,
        ignored_exceptions=IGNORED_EXCEPTIONS,
        max_tries=MAX_TRIES,
    ):
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
        selector_type,
        delay,
        ignored_exceptions,
    ):
        element = WebDriverWait(
            self.driver, delay, ignored_exceptions=ignored_exceptions
        ).until(EC.presence_of_element_located((selector_type, selector)))

        ActionChains(self.driver).click(element).key_down(Keys.CONTROL).send_keys(
            "a"
        ).key_up(Keys.CONTROL).send_keys(keys).perform()

    def wait_desappear(
        self,
        selector: str,
        selector_type=By.XPATH,
        delay=30,
        ignored_exceptions=IGNORED_EXCEPTIONS,
        max_tries=10,
    ):
        return self.retry_func(
            lambda: self._wait_desappear_helper(
                selector, selector_type, delay, ignored_exceptions
            ),
            max_tries,
        )

    def _wait_desappear_helper(
        self,
        selector,
        selector_type,
        delay,
        ignored_exceptions,
    ):
        WebDriverWait(self.driver, delay).until(
            EC.invisibility_of_element_located((selector_type, selector))
        )

    def move_to_element(
        self,
        selector: str,
        selector_type=By.XPATH,
        delay=DELAY,
        ignored_exceptions=IGNORED_EXCEPTIONS,
        max_tries=MAX_TRIES,
    ):
        self.retry_func(
            lambda: self._move_to_element_helper(
                selector, selector_type, delay, ignored_exceptions
            ),
            max_tries,
        )

    def _move_to_element_helper(
        self,
        selector,
        selector_type,
        delay,
        ignored_exceptions,
    ):
        ActionChains(self.driver).move_to_element(
            WebDriverWait(
                self.driver, delay, ignored_exceptions=ignored_exceptions
            ).until(EC.presence_of_element_located((selector_type, selector)))
        ).perform()
