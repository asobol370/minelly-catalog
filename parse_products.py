"""Парсер карточек Minelly: JSON-LD → catalog.json."""
import json
import re
import time
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
BASE = "https://minelly.com.ua"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def parse_page(url):
    html = fetch(url)
    # JSON-LD блок
    block = re.search(
        r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.DOTALL
    )
    if not block:
        return None
    data = json.loads(block.group(1))
    product = next((x for x in data if x.get("@type") == "Product"), None)
    breadcrumbs = next((x for x in data if x.get("@type") == "BreadcrumbList"), None)
    if not product:
        return None

    offers = product.get("offers", {})
    if isinstance(offers, list):
        offers = offers[0] if offers else {}

    # Категория из breadcrumbs (предпоследний элемент, последний — сам товар)
    category = None
    if breadcrumbs:
        items = breadcrumbs.get("itemListElement", [])
        if len(items) >= 2:
            category = items[-2].get("name")

    # Главная картинка из HTML: первый /images/uploads/*-thumb.*
    img_match = re.search(r'src="(/images/uploads/[^"]+-thumb\.[^"]+)"', html)
    if not img_match:
        img_match = re.search(r'src="(/images/uploads/[^"]+)"', html)
    image = BASE + img_match.group(1) if img_match else None

    # Чистим description от HTML-entities
    desc = product.get("description", "")
    desc = desc.replace("&rsquo;", "'").replace("&amp;", "&").replace("&nbsp;", " ")
    desc = re.sub(r"<[^>]+>", "", desc).strip()

    return {
        "name": product.get("name"),
        "description": desc,
        "weight": product.get("weight"),
        "price": float(offers.get("price", 0)),
        "currency": offers.get("priceCurrency", "UAH"),
        "in_stock": "InStock" in offers.get("availability", ""),
        "category": category,
        "image": image,
        "url": url,
    }


def main():
    with open("selected.txt") as f:
        urls = [line.strip().split("\t")[1] for line in f if line.strip()]

    products = []
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}")
        try:
            p = parse_page(url)
            if p:
                products.append(p)
                print(f"     ✓ {p['name']} — {p['price']} {p['currency']}")
            else:
                print("     ✗ No Product schema")
        except Exception as e:
            print(f"     ✗ Error: {e}")
        time.sleep(0.5)  # вежливая задержка

    with open("catalog.json", "w") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print(f"\n💾 catalog.json — {len(products)} products")


if __name__ == "__main__":
    main()
