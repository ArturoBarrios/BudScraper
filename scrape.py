from playwright.sync_api import sync_playwright
import time
import requests
import json

BASE_URL = "https://monroe-menu.thelandingdispensaries.com"
LISTING_URL = "https://monroe-menu.thelandingdispensaries.com/stores/monroe-ohio/products/flower"

def get_product_links(page, limit=None):    
    page.goto(LISTING_URL, timeout=60000)
    page.wait_for_selector("div[data-testid='product-list-item'] a", timeout=10000)

    # Get total number of pages from pagination nav
    page.wait_for_selector("nav[aria-label='pagination navigation']", timeout=10000)
    pagination_buttons = page.locator("nav[aria-label='pagination navigation'] button[aria-label^='go to page']")
    total_pages = pagination_buttons.count()

    print(f"📘 Total pages detected: {total_pages}")

    links = []
    page_number = 1

    while page_number <= total_pages:
        product_anchors = page.locator("div[data-testid='product-list-item'] a").all()
        for a in product_anchors:
            href = a.get_attribute("href")
            if href and href.startswith("/stores/monroe-ohio/product/"):
                links.append(BASE_URL + href)

        print(f"📄 Page {page_number}: Collected {len(links)} links so far")

        if page_number == total_pages:
            break

        next_button = page.locator("button[aria-label='go to next page']")
        try:
            next_button.click(force=True)
            page.wait_for_selector("div[data-testid='product-list-item'] a", timeout=10000)
            page_number += 1
        except Exception as e:
            print(f"⚠️ Failed to go to next page: {e}")
            break

    print(f"🧮 Total products found across all pages: {len(links)}")

    if limit and limit > 0:
        return links[:limit]
    return links





def scrape_product_details(page, url):
    page.goto(url, timeout=60000)
    page.wait_for_timeout(4000)

    # Get product name and weight
    product_name_raw = page.locator("h1[data-testid='product-name']").text_content().strip()
    if "|" in product_name_raw:
        name, weight = [part.strip() for part in product_name_raw.split("|", 1)]
    else:
        name = product_name_raw
        weight = None

    print("product_name_raw:", product_name_raw)
    print("name:", name)
    
    offer = None
    try:
        offer_elem = page.locator("div.product-specials-carousel-card__Container-sc-19b4u4b-0 p span").first
        if offer_elem:
            offer = offer_elem.text_content().strip()
    except Exception as e:
        print("Failed to get special offer:", e)

    # Get strain type
    strain_type = None
    strain_chip = page.locator("span[data-testid='info-chip']").first

    print("strain_chip:", strain_chip)
    if strain_chip:
        strain_type = strain_chip.text_content().strip()
        print("strain_type:", strain_type)
        
    # Get brand name
    brand_name = None
    try:
        brand_elem = page.locator("div[class*='Brand'] a")
        if brand_elem.count() > 0:
            brand_name = brand_elem.first.text_content().strip()
            print("brand_name:", brand_name)
    except Exception as e:
        print("Failed to get brand name:", e)

    # Get THC percentage
    thc_text = None
    try:
        thc_chip = page.locator("span[data-testid='info-chip']").nth(1)
        if thc_chip:
            content = thc_chip.text_content().strip()
            print("thc_chip content:", content)
            if "THC:" in content:
                thc_text = content.replace("THC:", "").strip()
    except Exception as e:
        print("Failed to get THC value:", e)

    # Get terpene data (normalize to %)
    terpene_containers = page.locator("div.terpene__Container-sc-s9pry-0")
    terpenes = {}
    for i in range(terpene_containers.count()):
        container = terpene_containers.nth(i)
        name_terp = container.locator("span.terpene__Name-sc-s9pry-3").text_content().strip()
        value_raw = container.locator("span.terpene__Value-sc-s9pry-4").text_content().strip()

        if value_raw.endswith("mg/g"):
            try:
                mg_value = float(value_raw.replace("mg/g", "").strip())
                percent = round(mg_value / 10, 2)
                value = f"{percent}%"
            except:
                value = value_raw
        else:
            value = value_raw

        terpenes[name_terp] = value

    # Get price
    price = None
    try:
        price_button = page.locator("div[data-testid='options-list'] button[data-testid='option-tile']").first
        price_text = price_button.text_content().strip()
        if "$" in price_text:
            price = f"${price_text.split('$')[1].strip()}"
    except:
        pass

    return {
        "url": url,
        "name": name,
        "strain_type": strain_type,
        "thc": thc_text,
        "terpenes": terpenes,
        "weight": weight,
        "price": price,
        "brand": brand_name,
        "offer": offer
    }

def main():
    max_items = input("How many products do you want to scrape? (default: 5, use 0 for all): ")
    max_items = int(max_items.strip()) if max_items.strip().isdigit() else 5
    max_items = None if max_items == 0 else max_items

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"🔎 Getting product links...")
        links = get_product_links(page, limit=max_items)
        print(f"🧾 Found {len(links)} product(s).")

        all_data = []
        for link in links:
            print(f"➡️ Scraping {link}")
            try:
                data = scrape_product_details(page, link)
                all_data.append(data)
            except Exception as e:
                print(f"⚠️ Error scraping {link}: {e}")
            time.sleep(2)

        browser.close()

        print("\n✅ Scraping complete. Sending data to backend...")

        payload = {
            "storeName": "Monroe Ohio",
            "strains": all_data
        }

        print("\n🔍 Payload being sent to backend:\n" + json.dumps(payload, indent=2))

        try:
            response = requests.post("http://localhost:4000/strains/create-strains", json=payload)
            print(f"📬 Server response: {response.status_code} {response.reason}")
            print(response.text)
        except Exception as e:
            print(f"❌ Failed to send data to backend: {e}")

if __name__ == "__main__":
    main()
