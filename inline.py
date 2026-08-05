"""Вписывает catalog.json прямо в <script id="catalog-data"> внутри index.html."""
import json
import re

catalog = json.load(open("catalog.json"))
html = open("index.html").read()
catalog_str = json.dumps(catalog, ensure_ascii=False).replace("</", "<\\/")

new_html = re.sub(
    r'(<script type="application/json" id="catalog-data">)[^<]*(</script>)',
    lambda m: m.group(1) + catalog_str + m.group(2),
    html,
    count=1,
)

if new_html == html:
    print(f"WARN: no <script id=\"catalog-data\"> found in index.html")
open("index.html", "w").write(new_html)
print(f"Inlined {len(catalog)} products into index.html")
