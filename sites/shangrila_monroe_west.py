# sites/shangrila_monroe_west.py

import time
import requests
import json

BASE_URL = "https://shangriladispensaries.com"
LISTING_URL = f"{BASE_URL}/stores/shangri-la-monroe-butler-county/products/flower"

def run(page, limit=None):
    print("🔎 Getting product links for Shangri-La Monroe...")
    links = get_product_links(page, limit=limit)
    print(f"🧾 Found {len(links)} product(s).")

    for link in links:
        print(f"➡️ Scraping {link}")
        try:
            data = scrape_product_details(page, link)

            payload = {
                "storeName": "Shangri-La Monroe",
                "strains": [data]
            }

            print("\n📤 Sending strain to backend:\n" + json.dumps(payload, indent=2))

            response = requests.post("http://localhost:4000/strains/create-strains", json=payload)
            print(f"📬 Server response: {response.status_code} {response.reason}")
            print(response.text)
        except Exception as e:
            print(f"⚠️ Error scraping {link}: {e}")
        time.sleep(2)

    print("\n✅ Done sending all strains to backend.")


def get_product_links(page, limit=None):
    page.goto(LISTING_URL, timeout=60000)
    page.wait_for_selector("div[data-testid='product-list-item'] a", timeout=10000)

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
            if href and "/stores/shangri-la-monroe-butler-county/product/" in href:
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
    return links[:limit] if limit else links


def scrape_product_details(page, url):
    page.goto(url, timeout=60000)
    page.wait_for_timeout(4000)

    # Name
    raw_name = page.locator("h1[data-testid='product-name']").text_content().strip()
    name = raw_name.split("(")[0].strip()
    weight = None

    # Brand
    brand = None
    try:
        brand_elem = page.locator("div[class*='Brand'] a")
        if brand_elem.count() > 0:
            brand = brand_elem.first.text_content().strip()
    except Exception as e:
        print("⚠️ Failed to get brand name:", e)

    # Prices and Weights
    prices = []
    weights = []
    try:
        price_buttons = page.locator("div[class*='Options'] button[data-testid='option-tile']")
        for i in range(price_buttons.count()):
            text = price_buttons.nth(i).text_content().strip()
            if "$" in text:
                parts = text.split("$")
                weights.append(parts[0].strip())
                prices.append(f"${parts[1].strip()}")
    except Exception as e:
        print("⚠️ Failed to get prices/weights:", e)

    # Strain type, THC, CBD
    strain_type = thc = cbd = None
    try:
        chips = page.locator("span[data-testid='info-chip']")
        for i in range(chips.count()):
            content = chips.nth(i).text_content().strip()
            if content.lower() in ["indica", "sativa", "hybrid"]:
                strain_type = content
            elif "THC:" in content:
                thc = content.replace("THC:", "").strip()
            elif "CBD:" in content:
                cbd = content.replace("CBD:", "").strip()
    except Exception as e:
        print("⚠️ Failed to get strain tags:", e)

    # Terpenes
    terpenes = {}
    try:
        terpene_containers = page.locator("div[class*='terpene__Container']")
        for i in range(terpene_containers.count()):
            terpene = terpene_containers.nth(i)
            name = terpene.locator("span[class*='terpene__Name']").text_content().strip()
            value = terpene.locator("span[class*='terpene__Value']").text_content().strip()
            terpenes[name] = value
    except Exception as e:
        print("⚠️ Failed to extract terpenes:", e)

    return {
        "url": url,
        "name": name,
        "strain_type": strain_type,
        "thc": thc,
        "cbd": cbd,
        "brand": brand,
        "prices": prices,
        "weights": weights,
        "terpenes": terpenes
    }
