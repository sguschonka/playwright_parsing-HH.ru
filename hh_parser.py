from playwright.async_api import async_playwright
import asyncio
from datetime import datetime
import re
import pandas

filename = f"результаты_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.xlsx"


async def parse(page, data):
    await page.wait_for_selector('[data-qa="vacancy-serp__vacancy"]')
    vacancy_info = page.locator('[data-qa="vacancy-serp__vacancy"]')
    count = await vacancy_info.count()

    for i in range(count):
        try:
            container = vacancy_info.nth(i)
            vacancy_locator = container.locator(
                '[data-qa="serp-item__title-text"]')
            company_locator = container.locator(
                '[data-qa="vacancy-serp__vacancy-employer-text"]').nth(0)
            salary_locator = container.locator(
                'div.narrow-container--HaV4hduxPuElpx0V > span.magritte-text___pbpft_3-0-41').nth(0)
            link_locator = container.locator(
                '[data-qa="serp-item__title"]')
            address_locator = container.locator(
                '[data-qa="vacancy-serp__vacancy-address"]').nth(0)

            address = await address_locator.text_content()
            vacancy = await vacancy_locator.text_content()
            link = await link_locator.get_attribute('href')
            company_row = await company_locator.inner_text()
            company = re.sub(r'[\u202f\xa0]', '', company_row).strip()

            if await salary_locator.count() > 0:
                salary_raw = await salary_locator.text_content()
                salary = re.sub(r'[\u202f\xa0]', '', salary_raw).strip()
            if '₽' not in salary:
                salary = 'Не указана'

            data.append({
                'Вакансия': vacancy,
                'Работодатель': company,
                'Заработная плата': salary,
                'Ссылка': link,
                'Местоположение': address,
            })

        except Exception as e:
            print(f" Ошибка при обработке {i}-й вакансии: {e}")
            continue  # Не останавливаем цикл


async def goto_next(browser_page):
    buttons = browser_page.locator('[data-qa="pager-page"]')

    if await buttons.count() > 0:
        active = browser_page.locator(
            '[data-qa="pager-page"][aria-current="true"]')
        active_text = await active.text_content()

        index = -1
        for b in range(await buttons.count()):
            btn = buttons.nth(b)
            text = await btn.text_content()
            if text == active_text:
                index = b
                break

        if index + 1 < await buttons.count():
            await buttons.nth(index + 1).click()
            await browser_page.wait_for_selector('[data-qa="vacancy-serp__vacancy"]')
            await asyncio.sleep(1)
            return True  # ✅ успешно перешли
        else:
            return False  # ❌ больше нет страниц
    else:
        return False


async def file_update(data):
    vacancies_without_salary = sum(
        1 for value in data if value['Заработная плата'] == 'Не указана')
    datafile = pandas.DataFrame(data)
    with pandas.ExcelWriter(filename, engine='openpyxl') as writer:
        datafile.to_excel(
            writer, sheet_name='Сбор данных о вакансиях python-backend разработчика в Москве', index=False)
    with open('log.txt', 'a', encoding="utf-8") as f:
        f.write(
            f'[{datetime.now()}] Собрано: {len(data)}, из них без зарплаты: {vacancies_without_salary}')


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

if __name__ == '__main__':
    asyncio.run(main())
