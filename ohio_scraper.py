import json
import sys
import time
from seleniumbase import SB
from bs4 import BeautifulSoup

def scrape_business_info(control_number):
    with SB(uc=True, test=True, locale="en", maximize=True) as sb:
        url = "https://businesssearch.ohiosos.gov/#DocidDiv"
        sb.activate_cdp_mode(url)

        sb.cdp.sleep(5)

        input_selector = '#idSrch'
        search_button = '#DocidDiv input.srchBtn[value="SEARCH"]'

        # Handle captcha
        start_time = time.time()
        timeout_seconds = 30
        while not sb.cdp.is_element_visible(search_button):
            if time.time() - start_time > timeout_seconds:
                print(f"Captcha handling exceeded {timeout_seconds} seconds - exiting")
                sys.exit(1)
            try:
                sb.cdp.scroll_into_view('div[id*="AwTSQ5"]')
                rect = sb.cdp.get_gui_element_rect('div[id*="AwTSQ5"]')
                x = rect['x'] + 35
                y = rect['y'] + 20
                sb.cdp.gui_click_x_y(x, y)
                sb.cdp.sleep(1)
            except Exception as e:
                print(f"Captcha attempt failed: {e}")
                sb.cdp.sleep(1)

        # Search by control number
        sb.cdp.click('#sos-entity-toggle')
        sb.cdp.sleep(2)
        sb.cdp.type(input_selector, control_number)
        sb.cdp.click(search_button)

        # Open details modal
        details_button = 'a.modalLinks.refLink[href="#busDialog"]'
        sb.cdp.click(details_button)
        sb.cdp.wait_for_element_visible("#businessDetails", timeout=20)
        sb.sleep(1)

        # === GROUPED: Business Details ===
        def get_input_val(field_id):
            try:
                return sb.get_attribute(f"#{field_id}", "value").strip()
            except:
                return ""

        business_details = {
            "Business Name": sb.get_text("#business_name").strip() if sb.is_element_present("#business_name") else "",
            "Entity Number": get_input_val("charter_num"),
            "Filing Type": get_input_val("business_type"),
            "Status": get_input_val("status"),
            "Original Filing Date": get_input_val("effect_date"),
            "Expiration Date": get_input_val("expiry_date"),
            "Location": get_input_val("business_locationcountystate"),
        }

        # === Registered Agent Info ===
        html = sb.get_page_source()
        soup = BeautifulSoup(html, "html.parser")

        registered_agent = {}
        agent_div = soup.find("div", {"id": "agentContent"})
        if agent_div:
            agent_lines = [p.get_text(strip=True) for p in agent_div.find_all("p")]
            if agent_lines:
                registered_agent = {
                    "Name": agent_lines[0],
                    "Address": " ".join(agent_lines[1:-2]),
                    "Appointed Date": agent_lines[-2] if len(agent_lines) >= 2 else "",
                    "Status": agent_lines[-1] if len(agent_lines) >= 1 else "",
                }

        # === Filings ===
        filings = []
        filings_table = soup.find("table", {"id": "filingsModal-table"})
        if filings_table:
            rows = filings_table.find("tbody").find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    filing = {
                        "Filing Type": cols[0].get_text(strip=True),
                        "Date of Filing": cols[1].get_text(strip=True),
                        "Document ID": cols[2].get_text(strip=True)
                    }
                    link_tag = cols[3].find("a")
                    if link_tag and link_tag.get("href"):
                        filing["Download Link"] = link_tag["href"]
                    filings.append(filing)

        # === Prior Business Names ===
        prior_names = []
        prior_table = soup.find("table", {"id": "prior-table"})
        if prior_table:
            rows = prior_table.find("tbody").find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 2:
                    prior_names.append({
                        "Prior Business Name": cols[0].get_text(strip=True),
                        "Effective Date": cols[1].get_text(strip=True)
                    })

        # === Final Structured Data ===
        data = {
            "Business Details": business_details
        }

        if registered_agent:
            data["Registered Agent"] = registered_agent

        if filings:
            data["Filings"] = filings

        if prior_names:
            data["Prior Business Names"] = prior_names

        # Save to JSON
        output_filename = f"business_info_{control_number}.json"
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"Successfully extracted data and saved to {output_filename}")
        print(f"Successfully processed control number {control_number}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tennessee_scraper_clean.py <control_number>")
        sys.exit(1)

    control_numbers = sys.argv[1:]
    for control_number in control_numbers:
        scrape_business_info(control_number)
