import re
import datetime
import IPython
import requests as rq
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from selenium import webdriver

from storage import MovieAward, ScrapingLog, Award, session_scope
from constants import IMDB_BASE_URL, IMDB_TYPE_MOVIE, IMDB_TYPE_PERSON

def get_movie(imdb_id):
    pass

class IMDBAwardScraper(object):
    def __init__(self, award_id, year, award_name, award_date_timedelta=0):
        self.award_id = award_id
        self.year = year
        self.award_name = award_name
        self.award_date = datetime.datetime(year, 1, 1) + datetime.timedelta(days=award_date_timedelta)

    @property
    def award_url(self):
        return f'https://www.imdb.com/event/{self.award_id}/{self.year}/'

    def save_results(self, results):
        with session_scope() as session:
            objects = [
                MovieAward(
                    award_id=self.award_id,
                    award_category=award_category,
                    movie_imdb_id=movie_imdb_id,
                    award_name=self.award_name,
                    person_imdb_id=person_imdb_id,
                    person_name=person_name,
                    winner=winner,
                    award_date=self.award_date
                )
                for award_category, movie_imdb_id, person_imdb_id, person_name, winner in results
            ]
            session.bulk_save_objects(objects)

    def scrape(self, update_after=None):
        scrape_date = ScrapingLog.get_date(self.award_url)
        if not scrape_date or (update_after and scrape_date < update_after):
            driver = webdriver.Chrome()
            driver.get(self.award_url)
            soup = BeautifulSoup(driver.page_source, 'lxml')
            results = self.scrape_soup(soup):
            if results is not None:
                print(f"Scraping {self.award_url}, successfull, saving log")
                self.save_results(results)
                ScrapingLog.add_log(self.award_url)
        else:
            print(f"Skip scraping {self.award_url}: Already scraped")

    def scrape_soup(self, soup):
        scraped = []
        for award in soup.findChildren('div', {'class': 'event-widgets__award-category'}):
            category_name = award.find('div', {'class': 'event-widgets__award-category-name'}).text
            for nominee in award.findChildren('div', {'class': 'event-widgets__nomination-details'}):
                for movie_imdb_id, person_id, person_name, winner in self.extract_nominee_info(nominee):
                    scraped.append((category_name, movie_imdb_id, person_id, person_name, winner))
            break
        return scraped 

    def extract_nominee_info(self, base_nominee):
        movies = []
        people = []

        winner = base_nominee.find('div', {'class': 'event-widgets__winner-badge'}) is not None
        def extract(nominee_type):
            typed_nominee = base_nominee.find('div', {'class': f'event-widgets__{nominee_type}-nominees'})
            for nominee in typed_nominee.findChildren('span', {'class': f'event-widgets__nominee-name'}):
                try:
                    name = nominee.text
                    tp, imdb_id = urlparse(nominee.find('a').get('href')).path.strip('/').split('/')
                    if tp == IMDB_TYPE_MOVIE:
                        movies.append(imdb_id)
                    elif tp == IMDB_TYPE_PERSON:
                        people.append((imdb_id, name))
                except:
                    print(f'\n\nWARNING: Problem with {nominee.__str__()}\n\n')

        extract('primary')
        extract('secondary')

        for movie_imdb_id in movies:
            for person_id, person_name in people:
                yield movie_imdb_id, person_id, person_name, winner


with session_scope() as session:
    for award in session.query(Award).all():
        for year in range(award.start_year, award.end_year + 1):
            try:
                print(f"Scraping {award.award_name} {year}")
                IMDBAwardScraper(award.award_id, year, award.award_name, award.date_timedelta)
            except Exception as e:
                print(f"ERROR, problem with {award.award_name} {year}, Exception: {e}")
