from playwright.sync_api import sync_playwright, Page
from playwright._impl._errors import TimeoutError
import logging
from playwright_stealth import stealth_sync
from typing import Optional, List, Dict, Any


def _extract_problem_data(page: Page, table_id: str) -> List[Dict[str, Any]]:
    """Helper function to extract problem data from a table."""
    problems = []
    table = page.query_selector(f"#{table_id}")
    if not table:
        return []

    rows = table.query_selector_all("tbody tr")
    for row in rows:
        cols = row.query_selector_all("td")
        if len(cols) >= 2:
            problem_name = cols[0].inner_text().strip()
            # The count can have commas, so we remove them before converting to int
            count = int(cols[1].inner_text().strip().replace(",", ""))
            
            maude_link_element = cols[0].query_selector("a")
            maude_link = maude_link_element.get_attribute("href") if maude_link_element else None

            problems.append({"problem_name": problem_name, "count": count, "maude_link": maude_link})
    return problems

def scrape_fda_website(device_name: str, product_code: Optional[str] = None, min_year: int = 2020):
    """
    Main function to scrape the FDA website using Playwright.
    """
    print("Starting scraper...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        )

        # Apply stealth measures
        stealth_sync(page)

        try:
            # Navigate to the search page with an increased timeout
            page.goto("https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfTPLC/tplc.cfm", timeout=60000)
            print("Navigated to search page.")

            try:
                # --- Search for the device ---
                print("Searching for device...")
                # Use a more robust waiting strategy. Wait for the network to be idle,
                # then explicitly wait for the input field to be visible.
                page.wait_for_load_state("networkidle")
                device_input = page.locator("input[name=devicename]")
                device_input.wait_for(state="visible", timeout=30000)
                device_input.fill(device_name)
            except TimeoutError:
                logging.error("Timeout while trying to fill the device name. The page might not have loaded correctly.")
                logging.error("Current page content:\n" + page.content())
                # Re-raise the exception or return an error state
                raise

            # If product_code is provided, find the product code input and enter it
            if product_code:
                page.fill("input[name=productcode]", product_code)

            # Select the minimum year from the dropdown if it's not the default
            if min_year is not None and min_year != 2020:
                page.select_option("select[name=min_report_year]", str(min_year))

            # Click the search button
            page.click("input[name=search]")

            # Wait for the results to load by waiting for the next page's content
            print("Waiting for search results...")
            page.wait_for_load_state("networkidle")

            # Check if there are no results
            no_results_element = page.query_selector("#eir-results-number")
            if no_results_element and "0 results" in no_results_element.inner_text():
                print("No results found.")
                return {"status": "success", "message": "No results found for the given criteria.", "data": []}

            # --- Collect device detail links ---
            all_links = []
            print("Collecting device links...")
            while True:
                # Find the results table using a more robust selector. This targets the specific table
                # containing the device list by looking for the "Device Name" header.
                # The `..` then selects the parent `table` element.
                results_table_locator = page.locator('th:has-text("Device Name")').locator("..").locator("..")

                # Check if the table exists before proceeding
                if results_table_locator.count() == 0:
                    print("Warning: Results table not found on this page.")
                    break

                # Use the locator to find all link locators within the table, then get all of them
                device_link_locators = results_table_locator.locator("a[href*='tplc.cfm?id=']").all()
 
                base_url = "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfTPLC/"
                # Get the relative href and combine it with the base_url to create a full link
                for link_locator in device_link_locators:
                    href = link_locator.get_attribute("href")
                    if href:
                        full_link = base_url + href
                        all_links.append(full_link)

                # Check for a "Next" button to go to the next page
                next_button = page.query_selector("a[title=Next]")
                if next_button:
                    print("Navigating to next page...")
                    next_button.click()
                    page.wait_for_load_state("networkidle")
                else:
                    break

            # --- Scrape each device detail page ---
            scraped_data = []
            print(f"Found {len(all_links)} device links. Scraping each page...")

            for i, link in enumerate(all_links):
                print(f"Scraping page {i+1}/{len(all_links)}: {link}")
                page.goto(link, timeout=60000)

                # Wait for a stable element on the detail page (the 'Device' table header)
                # to ensure the content has loaded before scraping.
                page.wait_for_selector("th:has-text('Device')", state="visible", timeout=30000)

                # Extract the device name from the detail page's summary table
                # Use a more specific locator to get the `td` that is a sibling of the `th`
                # The regex '^Device$' ensures an exact match on the text "Device".
                device_name_locator = page.locator("th:text-matches('^Device$') + td")
                device_name_on_page = device_name_locator.inner_text().strip() if device_name_locator.count() > 0 else "Unknown Device Name"

                # device_problems = _extract_problem_data(page, "dataTableDevice")
                # patient_problems = _extract_problem_data(page, "dataTablePatient")

                scraped_data.append({
                    "device_name": device_name_on_page,
                    # "detail_page_link": link,
                    # "device_problems": device_problems,
                    # "patient_problems": patient_problems
                })

            return {"status": "success", "data": scraped_data}

        finally:
            print("Closing browser.")
            browser.close()

if __name__ == '__main__':
    # Example usage for testing the scraper directly
    results = scrape_fda_website("syringe")
    print(results)
