"""Читает sitemap, группирует товарные URL по категориям, выбирает 2 из каждой."""
import re
import xml.etree.ElementTree as ET
from collections import defaultdict

NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}

# Не-товарные страницы, которые пропускаем
EXCLUDE = {
    "", "catalog", "pro-nas", "blog", "virobnictvo", "contacts", "faq",
    "yak-obrati-kavu", "akciyi", "dostavka-i-oplata", "kava-v-zernax",
    "melena-kava", "melena-kava-smakova", "kava-spesialty", "drip-kava",
    "drip-kava-smakova", "kava-bez-kofeyinu", "nabori", "melena-aromatizovana",
    "podarunkovi-sertifikati", "moloti-monosorti", "monosorti-arabiki-v-zernah",
    "kupazhi", "return", "privacy", "terms",
}

# Правила категоризации по префиксу slug
CATEGORY_RULES = [
    (r"^zernova-kava-", "Зернова кава"),
    (r"^kava-v-zernax-", "Зернова кава"),
    (r"^melena-kava-.*smakova", "Мелена смакова"),
    (r"^melena-kava-", "Мелена кава"),
    (r"^melena-smakova-", "Мелена смакова"),
    (r"^melena-aromatizovana-", "Мелена ароматизована"),
    (r"^kava-melena-", "Мелена кава"),
    (r"^drip-kava-.*smakova", "Дрип смакова"),
    (r"^drip-kava-", "Дрип-кава"),
    (r"^kava-spesialty-", "Specialty"),
    (r"^kava-bez-kofeyinu-", "Без кофеїну"),
    (r"^piramidki-", "Пірамідки"),
    (r"^nabir-", "Набори"),
    (r"^dehustac", "Дегустаційні"),
    (r"^podarunkovi-sertifikat", "Сертифікати"),
    (r"^moloti-monosort", "Моносорти мелені"),
    (r"^monosort", "Моносорти зернові"),
    # Моносорти по стране (без префикса, просто slug страны)
    (r"^(braziliya|gvatemala|gonduras|el-salvador|efiopiya|indiya|indoneziya|keniya|kitai|kolumbiya|kosta-rika|meksika|nikaragua|panama|peru|ruanda|tanzaniya|uganda|jemen)", "Моносорти"),
]


def categorize(slug):
    for pattern, cat in CATEGORY_RULES:
        if re.match(pattern, slug):
            return cat
    return None


def main():
    tree = ET.parse("sitemap.xml")
    root = tree.getroot()

    by_category = defaultdict(list)
    uncategorized = []

    for url_elem in root.findall("s:url/s:loc", NS):
        url = url_elem.text.strip()
        slug = url.replace("https://minelly.com.ua/", "").strip("/")
        if slug in EXCLUDE or "/" in slug:
            continue
        cat = categorize(slug)
        if cat:
            by_category[cat].append(url)
        else:
            uncategorized.append(slug)

    print(f"=== Категорії ({len(by_category)}) ===")
    for cat, urls in sorted(by_category.items()):
        print(f"\n{cat}: {len(urls)} товарів")
        for u in urls[:3]:
            print(f"   {u}")

    print(f"\n=== Неопізнані ({len(uncategorized)}) ===")
    for slug in uncategorized[:30]:
        print(f"   {slug}")

    # Берём ВСЕ товары
    selected = []
    for cat, urls in sorted(by_category.items()):
        for url in urls:
            selected.append((cat, url))

    print(f"\n=== Обрано для парсингу: {len(selected)} ===")
    with open("selected.txt", "w") as f:
        for cat, url in selected:
            f.write(f"{cat}\t{url}\n")
            print(f"   {cat}: {url}")


if __name__ == "__main__":
    main()
