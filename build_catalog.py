"""
Полная пересборка каталога Minelly — 10 верхнеуровневых категорий.
Обходит pagination (?page=1..N). Товар может быть в нескольких категориях.
"""
import json
import os
import re
import time
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"
BASE = "https://minelly.com.ua"

# 10 верхнеуровневых категорий, как на сайте
CATEGORIES = [
    ("kava-v-zernax", "Кава в зернах"),
    ("melena-kava", "Мелена кава"),
    ("melena-kava-smakova", "Мелена кава смакова"),
    ("kava-spesialty", "Кава SPECIALTY"),
    # "Без доданків" = купажі + моносорти + без-кофеїнові моно (все без ароматизаторів)
    (["drip-kava-kupazovana", "drip-kava-monosortova",
      "drip-kava-bez-kofeyinu-monosortova", "drip-kava-bez-kofeyinu-kolumbiya"],
        "DRIP - кава без доданків"),
    # "Смакова" = ароматизовані з кофеїном + без кофеїну
    (["drip-kava-smakova", "drip-kava-bez-kofeyinu-smakova"], "DRIP - кава смакова"),
    ("kava-bez-kofeyinu", "Кава без кофеїну"),
    (None, "Пірамідки кави"),  # спецкейс — фиксированный список товаров
    ("melena-aromatizovana", "Дегустаційні набори"),  # именно этот URL на сайте
    ("podarunkovi-sertifikati", "Подарункові сертифікати"),
]

# Пірамідки — нет страницы категории, товары зафиксированы (на сайте показывается 3)
PIRAMIDKI_SLUGS = ["piramidka-amo", "piramidka-senso", "piramidka-vero"]

# Слаги, которые НЕ являются товарами (собираются с страниц категорий)
NON_PRODUCT = set()
for slug, _ in CATEGORIES:
    if slug is None:
        continue
    if isinstance(slug, list):
        NON_PRODUCT.update(slug)
    else:
        NON_PRODUCT.add(slug)
# Родительские / вспомогательные / подкатегории (тоже не товары)
NON_PRODUCT.update({
    "", "catalog", "pro-nas", "blog", "virobnictvo", "contacts", "faq",
    "yak-obrati-kavu", "akciyi", "dostavka-i-oplata", "return", "privacy",
    "terms", "favorite", "cart", "login", "register", "shop",
    "rozrobka-privatnoyi-marki-kavi", "drip-stakan", "nabori",
    "monosorti-arabiki-v-zernah", "kupazi-kavi", "meleni-kupazi",
    "monosorti", "monosorti-arabiki",
    "drip-kava-kupazovana", "drip-kava-monosortova",
    "drip-kava-bez-kofeyinu-smakova", "drip-kava-bez-kofeyinu-monosortova",
    "drip-kava-bez-kofeyinu-kolumbiya", "dostavka-do-krayin-eu",
    "melena-zernova-bez-kofeyinu-kolumbiya",
})


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8")


def collect_products_from_category(cat_slug):
    """Обходит все страницы категории (с pagination) и возвращает уникальные product slugs.
    cat_slug может быть строкой, списком строк (объединение) или None (спецкейс пірамідок).
    """
    if cat_slug is None:
        return list(PIRAMIDKI_SLUGS)
    if isinstance(cat_slug, list):
        result = set()
        for sub in cat_slug:
            result.update(collect_products_from_category(sub))
        return sorted(result)
    all_slugs = set()
    page = 1
    while True:
        url = f"{BASE}/{cat_slug}" + (f"?page={page}" if page > 1 else "")
        try:
            html = fetch(url)
        except Exception as e:
            print(f"    ✗ page {page}: {e}")
            break

        hrefs = re.findall(r'href="/([a-z0-9][a-z0-9-]{4,120})(?:\?[^"]*)?"', html)
        page_products = set()
        for h in hrefs:
            if h in NON_PRODUCT or "/" in h:
                continue
            page_products.add(h)

        new_products = page_products - all_slugs
        if not new_products:
            break  # ничего нового = дошли до конца
        all_slugs.update(page_products)
        time.sleep(0.2)
        # проверка: есть ли ссылка на следующую страницу?
        if f"page={page + 1}" not in html:
            break
        page += 1
        if page > 20:  # safety
            break
    return sorted(all_slugs)


def parse_variants(html):
    """Извлекает multi-variants из HTML (по первому SKU prefix)."""
    first_sku = re.search(r'"sku":"([^"]+)"', html)
    if not first_sku:
        return []
    prefix = re.sub(r'-[A-Z]?\d+$', '', first_sku.group(1))
    if not prefix or len(prefix) < 3:
        return []
    pattern = r'"short_title":"([^"]+)"[^}]*?"price":(\d+)[^}]*?"sku":"(' + re.escape(prefix) + r'-[^"]*)"'
    seen = set()
    variants = []
    for m in re.finditer(pattern, html):
        t = m.group(1).encode().decode('unicode_escape').strip().rstrip('.')
        t = re.sub(r'^1000\s*г$', '1 кг', t)
        if not re.search(r'(г|кг|шт|мл|л)', t):
            continue
        p = int(m.group(2))
        if (t, p) in seen:
            continue
        seen.add((t, p))
        variants.append({'label': t, 'price': p})
    variants.sort(key=lambda x: x['price'])
    return variants


def parse_product(url):
    html = fetch(url)
    block = re.search(
        r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.DOTALL
    )
    if not block:
        return None
    data = json.loads(block.group(1))
    product = next((x for x in data if x.get("@type") == "Product"), None)
    if not product:
        return None

    offers = product.get("offers", {})
    if isinstance(offers, list):
        offers = offers[0] if offers else {}

    # Оригинал картинки: берём -thumb → убираем суффикс
    img_match = re.search(r'src="(/images/uploads/[^"]+?)-thumb\.([a-z]+)"', html)
    image_url = None
    if img_match:
        image_url = f"{BASE}{img_match.group(1)}.{img_match.group(2)}"
    else:
        m2 = re.search(r'src="(/images/uploads/[^"]+)"', html)
        if m2:
            image_url = f"{BASE}{m2.group(1)}"

    import html as _html
    desc = product.get("description", "")
    desc = _html.unescape(desc)  # &mdash; &rsquo; &amp; &nbsp; etc.
    desc = re.sub(r"<[^>]+>", "", desc).strip()

    variants = parse_variants(html)
    result = {
        "name": product.get("name"),
        "description": desc,
        "weight": product.get("weight"),
        "price": float(offers.get("price", 0)),
        "currency": offers.get("priceCurrency", "UAH"),
        "in_stock": "InStock" in offers.get("availability", ""),
        "image_url": image_url,
        "url": url,
    }
    if len(variants) > 1:
        result["variants"] = variants
    return result


def download_image(image_url):
    """Скачивает картинку, конвертирует в WebP 500px max side, сохраняет только .webp."""
    if not image_url:
        return None
    from PIL import Image
    import io

    fname = image_url.rsplit("/", 1)[-1]
    stem = fname.rsplit(".", 1)[0]
    webp_path = f"images/{stem}.webp"
    if os.path.exists(webp_path):
        return webp_path

    req = urllib.request.Request(image_url, headers={
        "User-Agent": UA,
        "Referer": "https://minelly.com.ua/",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
        img = Image.open(io.BytesIO(raw))
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA")
        # Downscale to max 500px on the longer side
        img.thumbnail((500, 500), Image.LANCZOS)
        img.save(webp_path, "WEBP", quality=80, method=6)
    except Exception as e:
        print(f"    ✗ img {fname}: {e}")
        return None
    return webp_path


def main():
    os.makedirs("images", exist_ok=True)

    # Шаг 1: обход категорий
    cat_to_slugs = {}
    all_slugs = set()
    for slug, title in CATEGORIES:
        print(f"\n[cat] {title}")
        try:
            product_slugs = collect_products_from_category(slug)
        except Exception as e:
            print(f"    ✗ {e}")
            continue
        cat_to_slugs[title] = product_slugs
        all_slugs.update(product_slugs)
        print(f"    → {len(product_slugs)} products")

    # Шаг 2: обратный индекс slug → categories
    slug_to_cats = {}
    for cat, slugs in cat_to_slugs.items():
        for s in slugs:
            slug_to_cats.setdefault(s, []).append(cat)

    print(f"\n=== Total unique products: {len(all_slugs)} ===")

    # Шаг 3: парсинг + скачивание картинок
    products = []
    for i, slug in enumerate(sorted(all_slugs), 1):
        url = f"{BASE}/{slug}"
        try:
            p = parse_product(url)
        except Exception as e:
            print(f"[{i}/{len(all_slugs)}] ✗ {slug}: {e}")
            continue
        if not p:
            print(f"[{i}/{len(all_slugs)}] ✗ {slug}: no product schema")
            continue
        p["categories"] = slug_to_cats.get(slug, [])
        local = download_image(p.pop("image_url", None))
        p["image"] = local
        if not local:
            print(f"[{i}/{len(all_slugs)}] ⚠ {p['name'][:40]}: no image, skipped")
            continue
        products.append(p)
        print(f"[{i}/{len(all_slugs)}] ✓ {p['name'][:45]:45} — {p['price']:>6.0f} грн ({', '.join(p['categories'])[:60]})")
        time.sleep(0.2)

    # Сортируем: сначала товары в наибольшем количестве категорий, затем по цене
    products.sort(key=lambda x: (-len(x["categories"]), -x["price"]))

    # Merge ручных товаров из manual_products.json (не парсяться, живуть окремо)
    if os.path.exists("manual_products.json"):
        try:
            manual = json.load(open("manual_products.json"))
            products.extend(manual)
            print(f"\n➕ merged {len(manual)} manual products from manual_products.json")
        except Exception as e:
            print(f"\n⚠ manual_products.json read failed: {e}")

    with open("catalog.json", "w") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print(f"\n💾 catalog.json — {len(products)} products")

    from collections import Counter
    cnt = Counter()
    for p in products:
        for c in p["categories"]:
            cnt[c] += 1
    print("\n=== Categories ===")
    for cat_title in [t for _, t in CATEGORIES]:
        print(f"  {cnt.get(cat_title, 0):3d}  {cat_title}")


if __name__ == "__main__":
    main()
