import logging
import time
from selenium.webdriver.common.by import By
from app.core.settings import settings
from app.infrastructure.automation.web.base_browser import BaseBrowser

logger = logging.getLogger(__name__)


class AhgoraBrowser(BaseBrowser):
    def __init__(self):
        super().__init__(url=settings.AHGORA_URL)

    def download_employees(self):
        logger.info("Starting employees download from Ahgora")
        try:
            self._login()
            self.driver.get(self.driver.current_url.replace("home", "funcionarios"))
            self._show_dismissed_employees()
            self._click_plus_button()
            self._export_to_csv()
            logger.info("Download of employees from Ahgora completed")
        finally:
            self.close_driver()

    def _login(self) -> None:
        user = settings.AHGORA_USER
        psw = settings.AHGORA_PASSWORD
        company = settings.AHGORA_COMPANY

        if not all([user, psw, company]):
            raise ValueError(
                "Ahgora credentials not set in environment variables (AHGORA_USER, AHGORA_PASSWORD, AHGORA_COMPANY)"
            )

        self._enter_username("email", user)
        self._click_enter_button()
        self._enter_password("password", psw)
        self._click_enter_button()
        self._select_company(company)
        self._close_banner()
        time.sleep(self.DELAY)

    def _enter_username(self, selector: str, user: str) -> None:
        self.send_keys(selector, user, selector_type=By.NAME)

    def _enter_password(self, selector: str, password: str) -> None:
        self.send_keys(selector, password, selector_type=By.NAME)

    def _click_enter_button(self) -> None:
        self.click_element("//*[contains(text(), 'Entrar')]")

    def _select_company(self, company: str) -> None:
        self.click_element(f"//*[contains(text(), '{company}')]")

    def _close_banner(self) -> None:
        try:
            # max_tries is handled by BaseBrowser's wait or click_element if specified,
            # but BaseBrowser usually has its own retry logic.
            self.click_element("buttonAdjustPunch", selector_type=By.ID)
        except Exception:
            time.sleep(self.DELAY)

    def _show_dismissed_employees(self) -> None:
        self.click_element("filtro_demitido", selector_type=By.ID)

    def _click_plus_button(self) -> None:
        self.click_element("mais", selector_type=By.ID)

    def _export_to_csv(self) -> None:
        self.click_element("arquivo_csv", selector_type=By.ID)
        # Give some time for the download to start/finish
        time.sleep(10)
