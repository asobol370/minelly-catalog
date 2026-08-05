# Minelly · Швидкий каталог

Публичный каталог кофе Minelly для быстрого просмотра из Telegram-чата с менеджером.
Одностраничник + автопарсинг данных с [minelly.com.ua](https://minelly.com.ua) раз в сутки.

## Как это работает

- **`build_catalog.py`** — обходит 10 верхнеуровневых категорий Minelly со всеми страницами pagination, парсит JSON-LD со страниц товаров, скачивает картинки (оригинальный размер) в `images/`, сохраняет всё в `catalog.json`.
- **`inline.py`** — вписывает содержимое `catalog.json` прямо в `index.html` (в тег `<script id="catalog-data">`) чтобы сайт был автономный и работал даже через `file://`.
- **`.github/workflows/update-catalog.yml`** — GitHub Action, каждый день в 06:00 UTC запускает оба скрипта и коммитит изменения. При коммите GitHub Pages автоматически публикует новую версию.
- **`index.html`** — сам каталог: dark-тема в стиле Minelly, 10 категорий-чипов, сетка карточек, TG-кнопка «Написати менеджеру».

## Локальная пересборка вручную

```bash
python3 build_catalog.py
python3 inline.py
```

## Ручной запуск GitHub Action

Actions → Update Minelly catalog → Run workflow

## Обновить TG-ссылку менеджера

В `index.html`, поиск по `TG_LINK` — заменить `https://t.me/minelly_coffee` на реальный username.
