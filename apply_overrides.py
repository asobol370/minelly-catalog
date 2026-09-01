"""
Применяет price_overrides.json к catalog.json.
Правило: цена меняется только если текущая == old (пока сайт отдаёт старую цену).
Когда сайт обновится и парсер принесёт новые цены — оверрайд перестаёт срабатывать сам.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def apply(items):
    try:
        with open(os.path.join(HERE, 'price_overrides.json')) as f:
            ov = json.load(f)
    except FileNotFoundError:
        return 0
    changed = 0
    for item in items:
        rules = ov.get(item.get('name'))
        if not rules:
            continue
        base = rules.get('base')
        if base and item.get('price') == base['old']:
            item['price'] = base['new']
            changed += 1
        for v in item.get('variants') or []:
            r = (rules.get('variants') or {}).get(v.get('label'))
            if r and v.get('price') == r['old']:
                v['price'] = r['new']
                changed += 1
    return changed


if __name__ == '__main__':
    path = os.path.join(HERE, 'catalog.json')
    with open(path) as f:
        items = json.load(f)
    n = apply(items)
    with open(path, 'w') as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    print(f'applied {n} price changes')
