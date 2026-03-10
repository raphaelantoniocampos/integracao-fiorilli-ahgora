import logging
import time
from typing import Callable

from selenium.webdriver.common.by import By

from app.core.settings import settings
from app.infrastructure.automation.web.base_browser import BaseBrowser

logger = logging.getLogger(__name__)


class AhgoraBrowser(BaseBrowser):
    def __init__(
        self, log_callback: Callable[[str, str], None] = None, headless: bool = None, cancel_event=None
    ):
        super().__init__(
            url=settings.AHGORA_URL, log_callback=log_callback, headless=headless, cancel_event=cancel_event
        )
        self._login()

    def download_employees(self):
        self._log("INFO", "Starting employees download from Ahgora")
        try:
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
        self.wait(self.DELAY)

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
            self.click_element("buttonAdjustPunch", selector_type=By.ID)
        except Exception:
            self.wait(self.DELAY)

    def _show_dismissed_employees(self) -> None:
        self.click_element("filtro_demitido", selector_type=By.ID)

    def _click_plus_button(self) -> None:
        self.click_element("mais", selector_type=By.ID)

    def _export_to_csv(self) -> None:
        self.click_element("arquivo_csv", selector_type=By.ID)
        # Give some time for the download to start/finish
        self.wait(10)

    def add_employee(self, payload: dict) -> None:
        """
        Navigates to the employee page and adds a new employee.
        :param payload: Dictionary containing employee details (from Fiorilli)
        """
        name = payload.get("name", "")
        self._log("INFO", f"Adding employee to Ahgora: {name}")

        # Ensure we are on the employee page
        self.driver.get(self.driver.current_url.replace("home", "funcionarios"))
        self.wait(self.DELAY)

        # Click the 'Novo Funcionário' button
        self.click_element("//button[contains(text(), 'Novo Funcionário')]")
        self.wait(self.DELAY * 2)

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
            self._set_autocomplete_select("dados-departamento", departamento)

        # Click Save
        self.click_element("(//button[contains(text(), 'Salvar')])[last()]")

        # Small wait for the request to process
        self.wait(self.DELAY * 4)
        self._log("INFO", f"Finished adding employee: {name}")

    def update_employee(self, payload: dict) -> None:
        """
        Updates an existing employee.
        """
        name = payload.get("name_fiorilli", "")
        employee_id = str(payload.get("id", ""))
        self._log("INFO", f"Updating employee in Ahgora: {name}")

        # Navigate to employee page
        self.driver.get(
            self.driver.current_url.replace(
                "home", f"funcionarios/edita/?matric={employee_id}"
            )
        )
        self.wait(self.DELAY)

        try:
            # Note: payload columns are suffixed with _fiorilli and _ahgora
            # Only update if the normalized value has changed

            has_changes = False

            if payload.get("name_fiorilli_norm") != payload.get("name_ahgora_norm"):
                if payload.get("name_fiorilli"):
                    self.send_keys(
                        "dados-nome", payload["name_fiorilli"], By.ID, clear_first=True
                    )
                    has_changes = True

            if payload.get("position_fiorilli_norm") != payload.get(
                "position_ahgora_norm"
            ):
                if payload.get("position_fiorilli"):
                    self.send_keys(
                        "dados.cargo",
                        payload["position_fiorilli"],
                        By.ID,
                        clear_first=True,
                    )
                    has_changes = True

            if payload.get("admission_date_fiorilli_norm") != payload.get(
                "admission_date_ahgora_norm"
            ):
                if payload.get("admission_date_fiorilli"):
                    self.send_keys(
                        "dados-dt_admissao",
                        payload["admission_date_fiorilli"],
                        By.ID,
                        clear_first=True,
                    )
                    has_changes = True

            if payload.get("department_fiorilli_norm") != payload.get(
                "department_ahgora_norm"
            ):
                if payload.get("department_fiorilli"):
                    self._set_autocomplete_select(
                        "dados-departamento", payload["department_fiorilli"]
                    )
                    has_changes = True
                    try:
                        pass
                        # self._update_location_multiselect(payload["department_fiorilli"])
                    except Exception as e:
                        self._log(
                            "WARNING",
                            f"Could not update location multiselect automatically: {e}",
                        )

            if has_changes:
                # Click Save
                self.click_element("(//button[contains(text(), 'Salvar')])[last()]")
                self.wait(self.DELAY * 4)
                self._log("INFO", f"Finished updating employee: {name} ({employee_id})")
            else:
                self._log(
                    "INFO",
                    f"No specific fields were changed for {name} ({employee_id}), skipping save.",
                )
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

        self.driver.get(self.driver.current_url.replace("home", "funcionarios"))
        self.wait(self.DELAY)

        # Search for the employee
        self.send_keys("filtro_funcionarios", employee_id, By.ID)
        self.wait(self.DELAY)
        self.send_enter_key("filtro_funcionarios", By.ID)
        self.wait(self.DELAY)

        try:
            # Click to Delete/Dismiss
            self.click_element(
                f"//a[contains(@title, 'Demitir funcionario {name.upper()}') or contains(@class, 'icone_remover')]"
            )
            self.wait(self.DELAY)

            # Form field for dismissal date
            try:
                self.send_keys("dt_demissao", dismissal_date, By.ID, clear_first=True)
                self.wait(self.DELAY)
                self.click_element(
                    "(/html/body/div[1]/div/div/div[2]/div[1]/div[2]/table/tbody/tr[1]/td/div/div[2]/div/button[2])[1]"
                )
                self.wait(self.DELAY * 2)
            except Exception:
                self._log(
                    "INFO",
                    "No specific dismissal date field found, assumed standard removal",
                )

            self._log("INFO", f"Finished removing employee: {name}")
        except Exception as e:
            self._log("ERROR", f"Failed to remove employee {name} ({employee_id}): {e}")
            raise e

    def upload_leaves_file(self, file_path: str) -> None:
        """
        Uploads a CSV/TXT file of leaves to Ahgora for validation (step 1).
        Does NOT save the records.
        """
        self._log("INFO", "Starting leave upload to Ahgora")

        import_path = settings.AHGORA_URL.replace("home", "afastamentos/importa")
        if import_path == settings.AHGORA_URL:  # Defense if URL structure was weird
            import_path = "https://app.ahgora.com.br/afastamentos/importa"

        self.driver.get(import_path)
        self.wait(self.DELAY * 2)

        try:
            # Find the file input element and send the file path
            file_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
            file_input.send_keys(str(file_path))
            self.wait(self.DELAY)

            # Ensure the specific layout is selected (pw_afimport_01)
            try:
                self.click_element("pw_afimport_01", By.ID)
            except Exception:
                self._log("DEBUG", "Could not find layout selector, assuming default.")

            # Click the upload/process button
            # Button labeled 'Obter Registros'
            self.click_element("//*/form/div[6]/button[2]")

            self.wait(self.DELAY * 5)  # Let the upload process
            self._log("INFO", f"Finished uploading leaves file from {file_path}")
        except Exception as e:
            self._log("ERROR", f"Failed to upload leaves file: {e}")
            raise e

    def extract_import_errors(self) -> list[dict]:
        """
        Extracts errors from the Ahgora import validation screen.
        Expects errors in the format: '[10] Intersecção com afastamento existente'.
        Returns a list of dicts: [{'row': 10, 'error': 'Intersecção...'}]
        """
        import re

        errors = []
        try:
            # The validation screen displays a log of processing, usually inside the DOM.
            # A robust way is to pull all body text and search line by line.
            self.click_element(selector="obterErro", selector_type=By.ID,delay=1,max_tries=240)
            body_text = self.driver.find_element(By.ID, "obterErro").text

            # Match logs like "Intersecção com afastamento... [15]"
            lines = body_text.split("\n")
            regex = r"(.+?)\s*\[(\d+)\]$"

            for line in lines:
                line = line.strip()
                match = re.search(regex, line)
                if match:
                    error_msg = match.group(1).strip()
                    row_idx = int(match.group(2))
                    errors.append({"row": row_idx, "error": error_msg})

            self._log("INFO", f"Extracted {len(errors)} validation errors.")
            return errors
        except Exception as e:
            self._log(
                "WARNING", f"Failed to extract import errors (could be 0 errors): {e}"
            )
            return []

    def confirm_import(self) -> None:
        """
        Clicks the save/confirm button to finalize the import of valid records.
        """
        try:
            self.click_element(selector="sendLeave", selector_type=By.ID)
            self.wait(self.DELAY * 20)
            self._log("INFO", "Successfully confirmed and saved leaves import.")
        except Exception as e:
            self._log("ERROR", f"Failed to confirm leaves import: {e}")
            raise e

    def _set_autocomplete_select(self, element_id: str, value: str) -> None:
        """
        Handles <select> elements that are transformed into ui-autocomplete inputs.
        Directly setting the value via Javascript to bypass clear() errors on uneditable inputs.
        """
        try:
            # Locate the select element to check if it has the option
            script = f"""
                var select = document.getElementById('{element_id}');
                if (select) {{
                    // Try to find exact or partial match in options
                    var options = select.options;
                    var matchFound = false;
                    for (var i = 0; i < options.length; i++) {{
                        if (options[i].text.trim().toUpperCase() === '{value.upper()}') {{
                            select.selectedIndex = i;
                            matchFound = true;
                            break;
                        }}
                    }}
                    if (!matchFound) {{
                        for (var i = 0; i < options.length; i++) {{
                            if (options[i].text.trim().toUpperCase().includes('{value.upper()}')) {{
                                select.selectedIndex = i;
                                break;
                            }}
                        }}
                    }}
                    // Trigger change event for jQuery/React listeners
                    var event = new Event('change', {{ bubbles: true }});
                    select.dispatchEvent(event);
                    
                    // Also attempt to update the visible sibling input if it's a combobox
                    var siblingInput = select.nextElementSibling;
                    if (siblingInput && siblingInput.tagName.toLowerCase() === 'input') {{
                        siblingInput.value = '{value}';
                        siblingInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                }}
            """
            self.driver.execute_script(script)
            self.wait(1)
        except Exception as e:
            self._log(
                "WARNING", f"Failed to set autocomplete select '{element_id}': {e}"
            )
            # Fallback to standard send keys without clear
            self.send_keys(element_id, value, By.ID, clear_first=False)

    # def _update_location_multiselect(self, search_text: str) -> None:
    #     """
    #     Interacts with the Bootstrap multiselect to update the 'Localização' field.
    #     Employs intelligent token-based fuzzy matching.
    #     """
    #     # 1. Click the button to open the dropdown.
    #     dropdown_btn_xpath = "//*[@id='form_funcionario']/div/div[2]/div[1]/div[2]/div[8]/div[2]/div/div/div/button"
    #     try:
    #         self.click_element(dropdown_btn_xpath, max_tries=3)
    #     except Exception:
    #         # Fallback
    #         try:
    #             self.click_element("//button[contains(@class, 'multiselect dropdown-toggle')]", max_tries=3)
    #         except Exception as e:
    #             self._log("WARNING", f"Could not find multiselect button: {e}")
    #             return
    #
    #     self.wait(1)
    #
    #     # 2. Clear previous selections if 'Todas localizações selecionadas' is active or checked
    #     try:
    #         self.click_element("//li[contains(@class, 'multiselect-all')]//label", max_tries=1)
    #         self.wait(0.5)
    #     except Exception:
    #         pass
    #
    #     try:
    #         self.click_element("//button[contains(@class, 'multiselect-clear-filter')]", max_tries=1)
    #         self.wait(0.5)
    #     except Exception:
    #         pass
    #
    #     # 3. Type into the search input
    #     search_input_xpath = "//*[@id='form_funcionario']/div/div[2]/div[1]/div[2]/div[8]/div[2]/div/div/div/div/ul/li[1]/div/input"
    #     try:
    #         self.send_keys(search_input_xpath, search_text, By.XPATH, clear_first=True, max_tries=3)
    #     except Exception:
    #         # Fallback
    #         try:
    #             self.send_keys("//input[contains(@class, 'multiselect-search')]", search_text, By.XPATH, clear_first=True, max_tries=3)
    #         except Exception:
    #             pass
    #
    #     self.wait(1)
    #
    #     # 4. Use JS for tokenized substring match to find the actual checkbox
    #     script = f"""
    #         var searchTxt = "{search_text.upper()}";
    #         var searchWords = searchTxt.split(' ');
    #         var labels = document.querySelectorAll("ul.multiselect-container label.checkbox");
    #
    #         var bestMatch = null;
    #         var maxMatches = 0;
    #
    #         for (var i = 0; i < labels.length; i++) {{
    #             var labelText = labels[i].textContent || labels[i].innerText;
    #             var li = labels[i].closest('li');
    #
    #             if (li && !li.classList.contains('filter') && !li.classList.contains('multiselect-all')) {{
    #                 var upperLabel = labelText.toUpperCase();
    #                 var matches = 0;
    #                 // Exact match takes precedence
    #                 if (upperLabel.trim() === searchTxt.trim()) {{
    #                     bestMatch = labels[i];
    #                     break;
    #                 }}
    #                 for(var w = 0; w < searchWords.length; w++) {{
    #                     if (searchWords[w].length > 2 && upperLabel.includes(searchWords[w])) {{
    #                         matches++;
    #                     }}
    #                 }}
    #                 if (matches > maxMatches) {{
    #                     maxMatches = matches;
    #                     bestMatch = labels[i];
    #                 }}
    #             }}
    #         }}
    #         if (bestMatch) {{
    #             bestMatch.click();
    #         }}
    #     """
    #     try:
    #         self.driver.execute_script(script)
    #     except Exception as e:
    #         self._log("WARNING", f"Could not explicitly select the filtered location item via JS: {e}")
    #
    #     # 5. Close the dropdown
    #     try:
    #         self.click_element(dropdown_btn_xpath, max_tries=2)
    #     except Exception:
    #         try:
    #             self.click_element("//button[contains(@class, 'multiselect dropdown-toggle')]", max_tries=2)
    #         except Exception:
    #             pass
