# playwright_parsing-HH.ru
---

# 📘 Полный разбор `hh_parser.py`

---

## 🧩 Импорты и инициализация

```python
from playwright.async_api import async_playwright
import asyncio
from datetime import datetime
import re
import pandas
```

### Что это:

* `playwright.async_api` — асинхронный интерфейс к браузеру (используется для управления страницей).
* `asyncio` — встроенный модуль Python для асинхронного программирования.
* `datetime` — нужен для генерации имени файла с датой.
* `re` — модуль регулярных выражений для очистки строк (например, зарплаты).
* `pandas` — для записи данных в Excel.

---

## 🧾 Создание имени файла

```python
filename = f"результаты_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"
```

📌 Формирует имя для Excel-файла, чтобы оно включало дату и время, когда был создан парсинг.

---

## 🔄 Функция `parse(page, data)`

Это основная функция для сбора вакансий с одной страницы.

### 1. Ждём появления блока вакансий

```python
await page.wait_for_selector('[data-qa="vacancy-serp__vacancy"]')
```

📌 Ожидаем, пока загрузятся карточки вакансий.

---

### 2. Получаем все блоки вакансий

```python
vacancy_info = page.locator('[data-qa="vacancy-serp__vacancy"]')
count = await vacancy_info.count()
```

📌 Определяем, сколько карточек на странице.

---

### 3. Проходимся по каждой вакансии

```python
for i in range(count):
    try:
        container = vacancy_info.nth(i)
```

📌 Для каждой карточки — создаём её локатор `container`.

---

### 4. Извлекаем информацию

```python
vacancy_locator = container.locator('[data-qa="serp-item__title-text"]')
company_locator = container.locator('[data-qa="vacancy-serp__vacancy-employer-text"]').nth(0)
salary_locator = container.locator('div.narrow-container--HaV4hduxPuElpx0V > span.magritte-text___pbpft_3-0-41').nth(0)
link_locator = container.locator('[data-qa="serp-item__title"]')
address_locator = container.locator('[data-qa="vacancy-serp__vacancy-address"]').nth(0)
```

📌 Эти локаторы находят нужные части внутри карточки: название, компания, зарплата, адрес, ссылка.

---

### 5. Считываем текстовые данные

```python
address = await address_locator.text_content()
vacancy = await vacancy_locator.text_content()
link = await link_locator.get_attribute('href')
company_row = await company_locator.inner_text()
company = re.sub(r'[\u202f\xa0]', '', company_row).strip()
```

📌 Используется `re.sub()` для очистки пробелов из Unicode (`\u202f`, `\xa0`).

---

### 6. Обрабатываем зарплату

```python
if await salary_locator.count() > 0:
    salary_raw = await salary_locator.text_content()
    salary = re.sub(r'[\u202f\xa0]', '', salary_raw).strip()
if '₽' not in salary:
    salary = 'Не указана'
```

📌 Если зарплата найдена — чистим её, иначе пишем `"Не указана"`.

---

### 7. Сохраняем данные в список

```python
data.append({
    'Вакансия': vacancy,
    'Работодатель': company,
    'Заработная плата': salary,
    'Ссылка': link,
    'Местоположение': address,
})
```

📌 Добавляем собранную информацию в список `data`.

---

### 8. Обработка исключений

```python
except Exception as e:
    print(f" Ошибка при обработке {i}-й вакансии: {e}")
    continue
```

📌 Если произошла ошибка в одной карточке — она пропускается, цикл продолжается.

---

## 🔁 Функция `goto_next(browser_page)`

Переход на следующую страницу.

### Пошаговая логика:

1. Находим все кнопки пагинации.
2. Определяем текущую активную.
3. Находим её индекс.
4. Кликаем по следующей, если есть.

```python
buttons = browser_page.locator('[data-qa="pager-page"]')
active = browser_page.locator('[data-qa="pager-page"][aria-current="true"]')
active_text = await active.text_content()
```

📌 Ищем, какая кнопка сейчас активна.

---

### Цикл по кнопкам:

```python
for b in range(await buttons.count()):
    btn = buttons.nth(b)
    text = await btn.text_content()
    if text == active_text:
        index = b
        break
```

📌 Сравниваем текст на кнопке с текущей активной — находим её индекс.

---

### Переход:

```python
if index + 1 < await buttons.count():
    await buttons.nth(index + 1).click()
    await browser_page.wait_for_selector('[data-qa="vacancy-serp__vacancy"]')
    await asyncio.sleep(1)
    return True
else:
    return False
```

📌 Если следующая кнопка есть — переходим. Если нет — завершаем цикл.

---

## 📁 Функция `file_update(data)`

Записывает данные в Excel и лог-файл.

```python
vacancies_without_salary = sum(
    1 for value in data if value['Заработная плата'] == 'Не указана')
```

📌 Считаем, сколько вакансий без зарплаты.

---

```python
datafile = pandas.DataFrame(data)
with pandas.ExcelWriter(filename, engine='openpyxl') as writer:
    datafile.to_excel(writer, ...)
```

📌 Запись в файл Excel через `pandas`.

---

```python
with open('log.txt', 'a', encoding="utf-8") as f:
    f.write(f'[{datetime.now()}] Собрано: {len(data)}, из них без зарплаты: {vacancies_without_salary}')
```

📌 Записываем лог: общее количество и сколько без зарплаты.

---

## 🧠 Главная функция `main()`

```python
async def main():
    data = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://omsk.hh.ru/search/vacancy?text=python+backend&area=1')

        while True:
            await parse(page, data)
            if not await goto_next(page):
                break

    await browser.close()
    await file_update(data)
```

📌 Основной цикл:

* открывает страницу
* парсит все вакансии со всех страниц
* закрывает браузер
* сохраняет в файл и лог

---

## 🟩 Запуск скрипта:

```python
if __name__ == '__main__':
    asyncio.run(main())
```

📌 Запускает `main()` при старте скрипта.

---

## ✅ Вывод: Что ты получаешь

* Полный цикл: от открытия сайта до Excel и логов
* Парсинг всех страниц (с пагинацией)
* Асинхронность и стабильность
* Защита от сбоев
* Данные пригодны для SQL и визуализации

---
