import logging
from typing import Optional, List, Dict, Any

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def _extract_problem_data(driver: webdriver.Chrome, header_text: str) -> List[Dict[str, Any]]:
    """Helper function to extract problem data from a table identified by its header text."""
    problems = []
    try:
        # Find the table by locating its specific header text.
        table = driver.find_element(By.XPATH, f"//th[normalize-space()='{header_text}']/ancestor::table[1]")
        # Find all data rows within that specific table.
        rows = table.find_elements(By.XPATH, ".//tbody/tr[td]")

        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 3:
                try:
                    link_element = cols[0].find_element(By.TAG_NAME, "a")
                    problem_name = link_element.text.strip()
                    maude_link = link_element.get_attribute("href")
                except NoSuchElementException:
                    problem_name = cols[0].text.strip()
                    maude_link = None

                mdr_count_text = cols[1].text.strip().replace(",", "")
                mdr_count = int(mdr_count_text) if mdr_count_text.isdigit() else None

                event_count_text = cols[2].text.strip().replace(",", "")
                event_count = int(event_count_text) if event_count_text.isdigit() else None

                problems.append({
                    "problem_name": problem_name,
                    "mdr_count": mdr_count,
                    "event_count": event_count,
                    "maude_link": maude_link,
                })
    except NoSuchElementException:
        # This is expected if a problem table doesn't exist.
        pass
    return problems


def scrape_fda_website(device_name: str, product_code: Optional[str] = None, since: int = 2020):
    """
    Main function to scrape the FDA website using Selenium.
    """
    print("Starting scraper with Selenium...")
    
    # Setup Chrome options for headless mode, which is required for an API.
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    # These arguments are recommended for running in a server/container environment.
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # Suppress verbose browser logging to keep the console clean.
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")

    # Use webdriver-manager to automatically handle the chromedriver.
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        # Navigate to the search page
        driver.get("https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfTPLC/tplc.cfm")
        print("Navigated to search page.")

        # Use WebDriverWait for reliable interaction.
        wait = WebDriverWait(driver, 45)

        # --- Search for the device ---
        print("Searching for device...")
        try:
            device_input = wait.until(EC.visibility_of_element_located((By.NAME, "devicename")))
            device_input.send_keys(device_name)
        except TimeoutException:
            logging.error("Timeout while trying to find the device name input. The page might not have loaded correctly.")
            logging.error("Current page content:\n" + driver.page_source)
            raise

        if product_code:
            driver.find_element(By.NAME, "productcode").send_keys(product_code)

        if since is not None:
            Select(driver.find_element(By.NAME, "min_report_year")).select_by_value(str(since))

        driver.find_element(By.NAME, "search").click()

        # --- Collect device detail links ---
        print("Waiting for search results...")
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//th[contains(., 'Device Name')]")))
        except TimeoutException:
            print("No results found for the given criteria.")
            return {"status": "success", "message": "No results found for the given criteria.", "data": []}

        all_links = []
        print("Collecting device links...")
        while True:
            # Find all links in the results table
            device_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'tplc.cfm?id=')]")
            for link in device_links:
                href = link.get_attribute("href")
                if href and href not in all_links:
                    all_links.append(href)

            # Check for a "Next" button
            try:
                next_button = driver.find_element(By.XPATH, "//a[@title='Next']")
                print("Navigating to next page...")
                next_button.click()
                wait.until(EC.staleness_of(next_button)) # Wait for the old button to disappear
            except NoSuchElementException:
                break # No more pages

        # --- Scrape each device detail page ---
        scraped_data = []
        print(f"Found {len(all_links)} device links. Scraping each page...")

        for i, link in enumerate(all_links):
            print(f"Scraping page {i+1}/{len(all_links)}: {link}")
            driver.get(link)
            
            try:
                wait.until(EC.visibility_of_element_located((By.XPATH, "//th[normalize-space()='Device']")))
            except TimeoutException:
                print(f"Warning: Could not find device details on page {link}. Skipping.")
                continue

            device_name_element = driver.find_element(By.XPATH, "//th[normalize-space()='Device']/following-sibling::td")
            device_name_on_page = device_name_element.text.strip()

            device_problems = _extract_problem_data(driver, "Device Problems")
            patient_problems = _extract_problem_data(driver, "Patient Problems")

            if device_problems or patient_problems:
                scraped_data.append({
                    "device_name": device_name_on_page,
                    "device_problems": device_problems,
                    "patient_problems": patient_problems
                })

        return {"status": "success", "data": scraped_data}

    finally:
        print("Closing browser.")
        driver.quit()

if __name__ == '__main__':
    results = scrape_fda_website("syringe")
    import json
    print(json.dumps(results, indent=2))
