import re
import datetime
import dateparser
import traceback
import IPython
import requests as rq
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from selenium import webdriver

from storage import MovieAward, ScrapingLog, Award, session_scope
from constants import IMDB_BASE_URL, IMDB_TYPE_MOVIE, IMDB_TYPE_PERSON, BLANK_IMDB_ID, BLANK_PERSON_NAME


def fix_oscar_dates():
    soup = BeautifulSoup(rq.get('https://en.wikipedia.org/wiki/List_of_Academy_Awards_ceremonies').text, 'lxml')
    table = soup.find('table', {'class': 'wikitable'}).find('tbody')
    table = table.findNext('table', {'class': 'wikitable'}).find('tbody')
    data = []
    rows = table.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        cols = [ele.text.strip() for ele in cols]
        data.append([ele for ele in cols if ele]) # Get rid of empty values

    dates = [x[1] for x in data[1:] if len(x) >= 2]
    parsed_dates_dict = {d.year: d.date() for d in [dateparser.parse(date) for date in dates]}
    with session_scope() as session:
        for award in session.query(MovieAward).all():
            award.award_date = parsed_dates_dict.get(award.award_date.year, award.award_date)
    with session_scope() as session:
        dates = set([x.award_date for x in session.query(MovieAward).all()])


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
            results = self.scrape_soup(soup)
            if results is not None:
                self.save_results(results)
                ScrapingLog.add_log(self.award_url)
                print(f"Scraping {self.award_url}, successfull")
        else:
            print(f"Skip scraping {self.award_url}: Already scraped")

    def scrape_soup(self, soup):
        scraped = []
        for award in soup.findChildren('div', {'class': 'event-widgets__award'}):
            aname = award.find('div', {'class': 'event-widgets__award-name'})
            if not aname:
                continue
            award_name = aname.text
            for category in award.findChildren('div', {'class': 'event-widgets__award-category'}):
                cname = category.find('div', {'class': 'event-widgets__award-category-name'})
                category_name = award_name
                if cname:
                    category_name = award_name + ' - ' + cname.text
                print(f"Scraping {category_name}")
                for nominee in category.findChildren('div', {'class': 'event-widgets__nomination-details'}):
                    for movie_imdb_id, person_id, person_name, winner in self.extract_nominee_info(nominee):
                        scraped.append((category_name, movie_imdb_id, person_id, person_name, winner))
        return set(scraped)

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

        if not people:
            people.append((BLANK_IMDB_ID, BLANK_PERSON_NAME)) 

        for movie_imdb_id in movies:
            for person_id, person_name in people:
                yield movie_imdb_id, person_id, person_name, winner


class IMDBCannesAwardScraper(IMDBAwardScraper):
    def scrape_soup(self, soup):
        scraped = []
        for category in soup.findChildren('div', {'class': 'event-widgets__award'}):
            cname = category.find('div', {'class': 'event-widgets__award-name'})
            if not cname:
                continue
            category_name = cname.text
            for nominee in category.findChildren('div', {'class': 'event-widgets__nomination-details'}):
                for movie_imdb_id, person_id, person_name, winner in self.extract_nominee_info(nominee):
                    scraped.append((category_name, movie_imdb_id, person_id, person_name, winner))
        return set(scraped)

SCRAPER_CLS_DICT = {
    'ev0000147': IMDBCannesAwardScraper
}

def scrape_imdb_awards():
    with session_scope() as session:
        for award in session.query(Award).all():
            for year in range(award.start_year, award.end_year + 1):
                try:
                    print(f"Scraping {award.award_name} {year}")
                    SCRAPER_CLS = SCRAPER_CLS_DICT.get(award.award_id, IMDBAwardScraper)
                    SCRAPER_CLS(award.award_id, year, award.award_name, award.date_timedelta).scrape()
                except Exception as e:
                    print(f"ERROR, problem with {award.award_name} {year}, Exception: {e}")
                    traceback.print_exc()

scrape_imdb_awards()
