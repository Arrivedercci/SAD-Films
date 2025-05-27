import scrapy


class LetterboxdFilmsSpider(scrapy.Spider):
    name = "letterboxd_films"
    allowed_domains = ["letterboxd.com"]
    start_urls = ["https://letterboxd.com/members/"]

    user_count = 0
    max_users = 50000  

    def parse(self, response):
        # Extrair links dos perfis de usuários na página de membros
        user_links = response.css('div.person-summary a.name::attr(href)').getall()
        for link in user_links:
            if self.user_count >= self.max_users:
                return  # Encerra o parse se atingir o limite

            self.user_count += 1
            user_id = f"user_{self.user_count:03d}"
            films_link = response.urljoin(link + 'films/')
            yield scrapy.Request(
                films_link,
                callback=self.parse_films,
                cb_kwargs={'user_id': user_id}
            )

        # Se ainda não atingiu o limite, segue para a próxima página de membros
        next_page = response.css('a.next::attr(href)').get()
        if next_page and self.user_count < self.max_users:
            yield response.follow(next_page, callback=self.parse)

    def parse_films(self, response, user_id):
        for film in response.css('li.poster-container'):
            # Busca o span com classe que contém 'rated-'
            rating_class = film.css('span.rating::attr(class)').get()
            rating = None
            if rating_class:
                import re
                match = re.search(r"rated-(\d+)", rating_class)
                if match:
                    rating = float(match.group(1)) 

            yield {
                'user_id': user_id,
                'film_title': film.css('img::attr(alt)').get(),
                'film_url': response.urljoin(film.css('div.poster a::attr(href)').get()),
                'rating': rating
            }

        # Paginação na página de filmes do usuário
        next_page = response.css('a.next::attr(href)').get()
        if next_page:
            yield response.follow(
                next_page,
                callback=self.parse_films,
                cb_kwargs={'user_id': user_id}
            )