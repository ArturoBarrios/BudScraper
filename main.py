import sys
from playwright.sync_api import sync_playwright
from sites.the_landing_monroe import run as landing_run
from sites.shangrila_monroe_west import run as shangrila_run

SCRAPERS = {
    "the_landing_monroe": landing_run,
    "shangrila_monroe_west": shangrila_run,
}

def main():
    if len(sys.argv) < 2:
        print("❌ Please specify a site (e.g. `python main.py the-landing-monroe`)")
        return

    site_key = sys.argv[1]
    scraper_fn = SCRAPERS.get(site_key)

    if not scraper_fn:
        print(f"❌ Unknown site: {site_key}")
        return

    max_items = input("How many products to scrape? (default: 5, use 0 for all): ")
    max_items = int(max_items.strip()) if max_items.strip().isdigit() else 5
    max_items = None if max_items == 0 else max_items

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        scraper_fn(page, limit=max_items)

        browser.close()

if __name__ == "__main__":
    main()
