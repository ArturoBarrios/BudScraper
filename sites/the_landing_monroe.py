import time
import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()


BASE_URL = "https://monroe-menu.thelandingdispensaries.com"
LISTING_URL = f"{BASE_URL}/stores/monroe-ohio/products/flower"

def run(page, limit=None):
    print(f"🔎 Getting product links for Monroe...")
    links = get_product_links(page, limit=limit)
    print(f"🧾 Found {len(links)} product(s).")

    for link in links:
        print(f"➡️ Scraping {link}")
        try:
            data = scrape_product_details(page, "https://monroe-menu.thelandingdispensaries.com/stores/monroe-ohio/product/cap-junk-2-83g")

            payload = {
                "storeName": "Monroe Ohio",
                "strains": [data]  # one strain at a time
            }

            print("\n📤 Sending strain to backend:\n" + json.dumps(payload, indent=2))

            response = response = requests.post(
    os.getenv("BUDRECOMMENDER_BE_URL") + "/strains/create-strains",
    json=payload
)   
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
    return links[:limit] if limit else links


def scrape_product_details(page, url):
    page.goto(url, timeout=60000)
    page.wait_for_timeout(4000)

    # Product name and weight
    product_name_raw = page.locator("h1[data-testid='product-name']").text_content().strip()
    name, weight = (product_name_raw.split("|", 1) if "|" in product_name_raw else (product_name_raw, None))
    name = name.strip()
    weight = weight.strip() if weight else None

    # Offer
    offer = None
    try:
        offer_elem = page.locator("div.product-specials-carousel-card__Container-sc-19b4u4b-0 p span").first
        if offer_elem:
            offer = offer_elem.text_content().strip()
    except Exception as e:
        print("Failed to get special offer:", e)

    # Strain type
    strain_type = None
    strain_chip = page.locator("span[data-testid='info-chip']").first
    if strain_chip:
        strain_type = strain_chip.text_content().strip()

    # Brand
    brand_name = None
    try:
        brand_elem = page.locator("div[class*='Brand'] a")
        if brand_elem.count() > 0:
            brand_name = brand_elem.first.text_content().strip()
    except Exception as e:
        print("Failed to get brand name:", e)

    # THC %
    thc_text = None
    try:
        thc_chip = page.locator("span[data-testid='info-chip']").nth(1)
        if thc_chip:
            content = thc_chip.text_content().strip()
            if "THC:" in content:
                thc_text = content.replace("THC:", "").strip()
    except Exception as e:
        print("Failed to get THC value:", e)

    # Terpenes
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

    # Price
    price = None
    try:
        price_button = page.locator("div[data-testid='options-list'] button[data-testid='option-tile']").first
        price_text = price_button.text_content().strip()
        if "$" in price_text:
            price = f"${price_text.split('$')[1].strip()}"
    except:
        pass

    # Image URL (get from inside the picture/img tag)
    image_url = None
    try:
        img_locator = page.locator("div[data-testid='main-product-image-scroll-container'] img").first
        if img_locator:
            image_url = img_locator.get_attribute("src")
    except Exception as e:
        print("Failed to get image URL:", e)

    return {
        "url": url,
        "name": name,
        "strain_type": strain_type,
        "thc": thc_text,
        "terpenes": terpenes,
        "weight": weight,
        "price": price,
        "brand": brand_name,
        "offer": offer,
        "image_url": image_url,
    }
