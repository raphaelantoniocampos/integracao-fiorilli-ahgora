import logging
import time
from typing import Callable
from selenium.webdriver.common.by import By
from app.core.settings import settings
from app.infrastructure.automation.web.base_browser import BaseBrowser

logger = logging.getLogger(__name__)


class AhgoraBrowser(BaseBrowser):
    def __init__(self, log_callback: Callable[[str, str], None] = None):
        super().__init__(url=settings.AHGORA_URL, log_callback=log_callback)

    def download_employees(self):
        self._log("INFO", "Starting employees download from Ahgora")
        try:
            self._login()
            self.driver.get(self.driver.current_url.replace("home", "funcionarios"))
            self._show_dismissed_employees()
            self._click_plus_button()
            self._export_to_csv()
            self._log("INFO", "Download of employees from Ahgora completed")
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

    def add_employee(self, payload: dict) -> None:
        """
        Navigates to the employee page and adds a new employee.
        :param payload: Dictionary containing employee details (from Fiorilli)
        """
        name = payload.get("name", "")
        self._log("INFO", f"Adding employee to Ahgora: {name}")
        self._login()

        # Ensure we are on the employee page
        self.driver.get("https://app.ahgora.com.br/funcionarios")
        time.sleep(self.DELAY)

        # Click the 'Novo Funcionário' button
        self.click_element("//button[contains(text(), 'Novo Funcionário')]")
        time.sleep(self.DELAY * 2)

        # Fill General Data
        self.send_keys("dados-nome", name, By.ID)

        pis = str(payload.get("pis_pasep", ""))
        if pis == "0" or not pis:
            pis = "00000000000"
        self.send_keys("dados-pis", pis, By.ID)

        cpf = str(payload.get("cpf", ""))
        if cpf:
            self.send_keys("dados-cpf", cpf, By.ID)

        birth_date = str(payload.get("birth_date", ""))
        if birth_date:
            self.send_keys("dados-dt_nascimento", birth_date, By.ID)

        # Sex
        sexo = str(payload.get("sex", ""))
        if sexo:
            self.send_keys("dados-sexo", sexo, By.ID)

        # RegimeTrab
        self.send_keys("dados-regimetrab", "Estatutário", By.ID)

        # Company Relation
        matricula = str(payload.get("id", ""))
        self.send_keys("dados.matricula", matricula, By.ID)

        admission_date = str(payload.get("admission_date", ""))
        if admission_date:
            self.send_keys("dados-dt_admissao", admission_date, By.ID)

        # Password
        self.send_keys("dados-cod_cracha", "12345", By.ID)

        cargo = str(payload.get("position", ""))
        if cargo:
            self.send_keys("dados.cargo", cargo, By.ID)

        departamento = str(payload.get("department", ""))
        if departamento:
            self.send_keys("dados-departamento", departamento, By.ID)

        # Click Save
        self.click_element("(//button[contains(text(), 'Salvar')])[last()]")

        # Small wait for the request to process
        time.sleep(self.DELAY * 4)
        self._log("INFO", f"Finished adding employee: {name}")

    def update_employee(self, payload: dict) -> None:
        """
        Updates an existing employee.
        """
        name = payload.get("name", "")
        employee_id = str(payload.get("id", ""))
        self._log("INFO", f"Updating employee in Ahgora: {name}")
        self._login()

        # Navigate to employee page
        self.driver.get("https://app.ahgora.com.br/funcionarios")
        time.sleep(self.DELAY)

        # Search for the employee
        self.send_keys("filtro", employee_id, By.ID)
        self.click_element("buscar", By.ID)
        time.sleep(self.DELAY)

        # Click to Edit (assuming first row in table)
        # Assuming the row edit button has a specific class or icon
        try:
            self.click_element(
                "//table[@id='tbFuncionario']//tbody//tr[1]//td//a[contains(@class, 'editar') or contains(@class, 'btn')]"
            )
            time.sleep(self.DELAY)

            # Update fields if present in payload (using similar logic to add)
            if "name" in payload and payload["name"]:
                self.send_keys("dados-nome", payload["name"], By.ID, clear_first=True)

            if "position" in payload and payload["position"]:
                self.send_keys(
                    "dados.cargo", payload["position"], By.ID, clear_first=True
                )

            if "department" in payload and payload["department"]:
                self.send_keys(
                    "dados-departamento", payload["department"], By.ID, clear_first=True
                )

            if "admission_date" in payload and payload["admission_date"]:
                self.send_keys(
                    "dados-dt_admissao",
                    payload["admission_date"],
                    By.ID,
                    clear_first=True,
                )

            # Click Save
            self.click_element("(//button[contains(text(), 'Salvar')])[last()]")
            time.sleep(self.DELAY * 4)
            self._log("INFO", f"Finished updating employee: {name}")
        except Exception as e:
            self._log(
                "ERROR", f"Failed to find or edit employee {name} ({employee_id}): {e}"
            )
            raise e

    def remove_employee(self, payload: dict) -> None:
        """
        Marks an employee as dismissed.
        """
        name = payload.get("name", "")
        employee_id = str(payload.get("id", ""))
        dismissal_date = str(payload.get("dismissal_date", ""))

        self._log("INFO", f"Removing employee in Ahgora: {name}")
        self._login()

        self.driver.get("https://app.ahgora.com.br/funcionarios")
        time.sleep(self.DELAY)

        # Search for the employee
        self.send_keys("filtro_funcionarios", employee_id, By.ID)
        time.sleep(self.DELAY)
        self.send_enter_key("filtro_funcionarios", By.ID)
        time.sleep(self.DELAY)

        try:
            # Click to Delete/Dismiss
            self.click_element(
                f"//a[contains(@title, 'Demitir funcionario {name.upper()}') or contains(@class, 'icone_remover')]"
            )
            time.sleep(self.DELAY)

            # Handle dismissal alert/modal if it appears
            try:
                alert = self.driver.switch_to.alert
                # Some systems ask for date in prompt or simple confirm
                alert.accept()
                time.sleep(self.DELAY)
            except Exception:
                pass  # No browser alert

            # If there is a form field for dismissal date
            try:
                self.send_keys("dt_demissao", dismissal_date, By.ID, clear_first=True)
                time.sleep(self.DELAY)
                self.click_element("(//div[contains(@class, 'icone_confirmar')])[0]")
                time.sleep(self.DELAY * 2)
            except Exception:
                self._log(
                    "INFO",
                    "No specific dismissal date field found, assumed standard removal",
                )

            self._log("INFO", f"Finished removing employee: {name}")
        except Exception as e:
            self._log("ERROR", f"Failed to remove employee {name} ({employee_id}): {e}")
            raise e

    def add_leave(self, file_path: str) -> None:
        """
        Uploads a CSV/TXT file of leaves to Ahgora.
        """
        self._log("INFO", "Starting leave upload to Ahgora")
        self._login()

        import_path = settings.AHGORA_URL.replace("home", "afastamentos/importa")
        if import_path == settings.AHGORA_URL:  # Defense if URL structure was weird
            import_path = "https://app.ahgora.com.br/afastamentos/importa"

        self.driver.get(import_path)
        time.sleep(self.DELAY * 2)

        try:
            # Find the file input element and send the file path
            file_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
            file_input.send_keys(file_path)
            time.sleep(self.DELAY)

            # Ensure the specific layout is selected (pw_afimport_01)
            # Assuming there is a select dropdown or it defaults to the user's config
            try:
                self.send_keys("layout_id", "pw_afimport_01", By.ID)
            except Exception:
                self._log("DEBUG", "Could not find layout selector, assuming default.")

            # Click the upload/process button
            # Button might be labeled 'Obter Registros' or 'Importar'
            self.click_element(
                "//button[contains(text(), 'Obter Registros') or contains(text(), 'Importar') or contains(text(), 'Enviar')]"
            )

            time.sleep(self.DELAY * 5)  # Let the upload process
            self._log("INFO", f"Finished uploading leaves file from {file_path}")
        except Exception as e:
            self._log("ERROR", f"Failed to upload leaves file: {e}")
            raise e
