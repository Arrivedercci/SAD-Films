from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import csv
import re

# Configuração do Selenium (headless)
options = Options()
options.add_argument("--headless")
driver = webdriver.Chrome(options=options)

start_url = "https://letterboxd.com/members/popular/this/week/"
max_users = 500
user_count = 0
results = []

try:
    driver.get(start_url)

    while user_count < max_users:
        user_links = driver.find_elements(By.CSS_SELECTOR, 'div.person-summary a.name')
        for link in user_links:
            if user_count >= max_users:
                break
            user_count += 1
            user_id = f"user_{user_count:03d}"
            films_link = link.get_attribute('href') + 'films/'
            driver2 = webdriver.Chrome(options=options)
            driver2.get(films_link)
            time.sleep(2)  # Aguarda o carregamento da página

            while True:
                film_elements = driver2.find_elements(By.CSS_SELECTOR, 'li.poster-container')
                for film in film_elements:
                    # Título do filme
                    film_title = film.find_element(By.CSS_SELECTOR, 'img').get_attribute('alt')
                    # Link do filme
                    try:
                        film_url = film.find_element(By.CSS_SELECTOR, 'a.frame').get_attribute('href')
                    except:
                        film_url = ''
                    # Nota
                    try:
                        rating_class = film.find_element(By.CSS_SELECTOR, 'span.rating').get_attribute('class')
                        match = re.search(r"rated-(\d+)", rating_class)
                        rating = float(match.group(1)) if match else None
                    except:
                        rating = None

                    film_year = None
                    # Tenta pegar do frame-title
                    try:
                        frame_title = film.find_element(By.CSS_SELECTOR, 'span.frame-title').text
                        match = re.search(r'\((\d{4})\)', frame_title)
                        if match:
                            film_year = match.group(1)
                    except:
                        pass
                    # Se não achar, tenta pegar do atributo data-original-title do <a>
                    if not film_year:
                        try:
                            data_original_title = film.find_element(By.CSS_SELECTOR, 'a.frame').get_attribute('data-original-title')
                            match = re.search(r'\((\d{4})\)', data_original_title)
                            if match:
                                film_year = match.group(1)
                        except:
                            pass

                    results.append({
                        'user_id': user_id,
                        'film_title': film_title,
                        'film_url': film_url,
                        'rating': rating,
                        'film_year': film_year
                    })

                # Paginação dos filmes do usuário
                try:
                    next_page = driver2.find_element(By.CSS_SELECTOR, 'a.next')
                    next_page_url = next_page.get_attribute('href')
                    if next_page_url:
                        driver2.get(next_page_url)
                        time.sleep(1)
                    else:
                        break
                except:
                    break
            driver2.quit()

        # Paginação dos membros
        try:
            next_page = driver.find_element(By.CSS_SELECTOR, 'a.next')
            next_page_url = next_page.get_attribute('href')
            if next_page_url:
                driver.get(next_page_url)
                time.sleep(1)
            else:
                break
        except:
            break

except KeyboardInterrupt:
    print("\nInterrompido pelo usuário. Salvando dados...")

finally:
    driver.quit()
    # Salva em CSV
    with open('films.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['user_id', 'film_title', 'film_url', 'rating', 'film_year']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    print("Dados salvos em films.csv")