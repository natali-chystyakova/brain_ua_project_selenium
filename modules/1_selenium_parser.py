import os  # noqa: F401
import sys  # noqa: F401
import django  # noqa: F401

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from selenium.webdriver.common.by import By

# from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

# from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains

from selenium.common.exceptions import NoSuchElementException
from load_django import *  # noqa: F403,F401


from parser_app.models import Product


def parse():
    options = webdriver.ChromeOptions()

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # options.add_argument("--headless=new")   # браузер в фоне (безгловый ржим)

    # создаем обьект - установка драйвера, открытиеи закрытие драйвера
    service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=options)  # обьект драйвера и чем будет управляться

    try:
        # Открваем страницу по url
        driver.get("https://brain.com.ua/ ")

        # получение title (тег в header)
        current_title = driver.title
        print("Текущий заголовок:", current_title)
        # валидация. проверка данных
        assert (
            current_title == "Brain - роздрібний інтернет-магазин комп'ютерної техніки та електроніки в Україні"
        ), "Некоректний заголовок"

        # search_input = driver.find_element(By.CSS_SELECTOR, "input.quick-search-input")

        search_input = driver.find_element(By.XPATH, "//input[contains(@class, 'quick-search-input')]")
        print(search_input)

        # Вводим текст по буквам
        actions = ActionChains(driver)
        actions.move_to_element(search_input).click()
        for c in "Apple iPhone 15 128GB Black":
            actions.send_keys(c)
            actions.pause(0.05)  # для иммитации ввода
        actions.perform()

        print(search_input.get_attribute("value"))  # проверка записи поля

        # #введем текст в строку поиска все вместе
        # search_input.send_keys("Apple iPhone 15 128GB Black")

        # без нажатия кнопки срабатывает
        # search_input.send_keys("Apple iPhone 15 128GB Black", Keys.ENTER)

        # если нужно именно нажать кнопку
        def wait_for_block(driver):
            # Найти в HTML элемент <div class="qsr-block">, зять его CSS-свойство display
            js = "return document.querySelector('div.qsr-block').style.display"
            value = driver.execute_script(js)
            return value == "block"

        wait = WebDriverWait(driver, 10)
        wait.until(wait_for_block)

        # найдём кнопку <input class="qsr-submit"> и нажимаем
        driver.execute_script("document.querySelector('input.qsr-submit').click()")
        # search_submit = driver.find_element(By.XPATH, "//input[contains(@class, 'qsr-submit')]")
        # #search_submit.click()
        # print(search_submit)

        # #заходим на первый елемент массива(карточек)
        # items = driver.find_elements(By.CSS_SELECTOR, "div.br-pcg-product-wrapper a")
        # print(len(items))
        # items[0].click()

        # #заходим на первый елемент массива(карточек) XPATH
        first_block = driver.find_element(By.XPATH, "(//div[contains(@class, 'br-pcg-product-wrapper')])[1]")

        # Находим любую ссылку внутри этого блока (берём первую попавшуюся)
        link = first_block.find_element(By.TAG_NAME, "a")

        # Кликаем по ссылке
        link.click()

        # получение текущей страницы
        URL = driver.current_url
        print("URL:", URL)

        # Берем данные с карточки для записи в базу данных

        product = {}

        # название товара
        try:
            title_el = driver.find_element(By.XPATH, "//h1[contains(@class, 'desktop-only-title')]")
            product["title"] = title_el.get_attribute("innerText").strip()
        except NoSuchElementException:
            product["title"] = None

        print("title", product["title"])

        # старая цена, если есть скидки
        try:
            o_price = driver.find_element(By.XPATH, "//div[contains(@class, 'br-pr-op')]//span")
            product["old_price"] = o_price.get_attribute("innerText").strip()
        except NoSuchElementException:
            product["old_price"] = None

        # новая цена - всегда есть
        try:
            price_block = driver.find_element(By.XPATH, "//div[contains(@class,'br-pr-np')]")

            red_prices = price_block.find_elements(By.XPATH, ".//span[contains(@class,'red-price')]")
            # (выдаст пустой список есл елемента нет, а не исключение. тут проверяем - elements)
            if red_prices:
                product["new_price"] = red_prices[0].text.strip()
                product["is_discount"] = True
            else:
                product["new_price"] = price_block.find_element(
                    By.XPATH, ".//div[contains(@class,'price-wrapper')]/span"
                ).text.strip()
                # тут утверджаем - element
                product["is_discount"] = False
        except NoSuchElementException:
            product["new_price"] = None
            product["is_discount"] = False

        print("old_price", product["old_price"])
        print("new_price", product["new_price"])
        print("is_discount", product["is_discount"])

        try:
            product_code = driver.find_element(By.XPATH, "//span[contains(@class, 'br-pr-code-val')]")
            product["product_code"] = product_code.get_attribute("innerText").strip()
        except NoSuchElementException:
            product["product_code"] = None  # код товара

        try:
            reviews_count = driver.find_element(By.XPATH, "//a[contains(@class, 'forbid-click')]//span")
            product["reviews_count"] = reviews_count.get_attribute("innerText").strip()
        except NoSuchElementException:
            product["reviews_count"] = None  # количество отзывов

        print("product_code", product["product_code"])
        print("reviews_count", product["reviews_count"])

        # ищем все картинки с классом br-main-img
        try:
            images = driver.find_elements(By.XPATH, "//img[contains(@class, 'br-main-img')]")
            base_url = "https://brain.com.ua"

            photo_urls = []
            for img in images:
                src = img.get_attribute("src")  # значение атрибута src (строка)
                if not src:
                    continue

                if src.startswith("http"):
                    photo_urls.append(src)
                else:
                    photo_urls.append(base_url + src)

        except NoSuchElementException:
            photo_urls = None

        product["images"] = photo_urls
        print("images:", product["images"])

        # найдем все характеристики и соберем их как слварь
        try:
            specifications_dict = {}

            sections = driver.find_elements(By.XPATH, "//div[contains(@class, 'br-pr-chr-item')]")

            for section in sections:
                # название секции (Основні характеристики, Дисплей, и т.д.)
                section_name = section.find_element(By.XPATH, ".//h3").get_attribute("innerText").strip()

                specifications_dict[section_name] = {}

                # строки характеристик — div, внутри которых есть ДВА span
                rows = section.find_elements(By.XPATH, ".//div[span and count(span)=2]")

                for row in rows:
                    spans = row.find_elements(By.XPATH, ".//span")

                    name = spans[0].get_attribute("innerText").strip()
                    value = spans[1].get_attribute("innerText").strip().replace("\xa0", "")

                    specifications_dict[section_name][name] = value

        except NoSuchElementException:
            specifications_dict = None

        product["specifications"] = specifications_dict
        print("specifications:", product["specifications"])

        try:
            product["color"] = specifications_dict.get("Фізичні характеристики", {}).get("Колір")
        except AttributeError:
            product["color"] = None

        try:
            product["memory"] = specifications_dict.get("Функції пам'яті", {}).get("Вбудована пам'ять")
        except AttributeError:
            product["memory"] = None

        try:
            product["manufacturer"] = specifications_dict.get("Інші", {}).get("Виробник")  # Производитель
        except AttributeError:
            product["manufacturer"] = None

        try:
            product["screen_size"] = specifications_dict.get("Дисплей", {}).get("Діагональ екрану")  # Диагональ экрана
        except AttributeError:
            product["screen_size"] = None

        try:
            product["resolution"] = specifications_dict.get("Дисплей", {}).get(
                "Роздільна здатність екрану"
            )  # роздiльна здатнiсть дiсплея
        except AttributeError:
            product["resolution"] = None

        for key, value in product.items():
            print("=" * 50)
            print(f"{key}: {value}")

        return URL, product

    finally:
        driver.quit()


URL, product = parse()


def save_product(url: str, data: dict):
    """Сохраняет продукт в базу данных (update or create)."""

    product, created = Product.objects.get_or_create(url=url)

    product.title = data.get("title")
    product.color = data.get("color")
    product.memory = data.get("memory")
    product.manufacturer = data.get("manufacturer")

    product.old_price = data.get("old_price")
    product.new_price = data.get("new_price")
    product.is_discount = data.get("is_discount")

    product.images = data.get("images")
    product.code = data.get("product_code")
    product.reviews_count = data.get("reviews_count")
    product.screen_size = data.get("screen_size")
    product.resolution = data.get("resolution")
    product.specifications = data.get("specifications")

    product.save()


save_product(url=URL, data=product)
