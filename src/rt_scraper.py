import re
import datetime
import requests as rq 
import dateparser
import traceback
from itertools import groupby
from collections import namedtuple
from bs4 import BeautifulSoup

from constants import Review, TYPE_CRITIC, TYPE_USER, RT_BASE_URL
from storage import session_scope, Movie, MovieAward, ScrapingLog, RTReview


class BaseReviews(object):
    def __init__(self, movie_url):
        self.movie_url = movie_url

    def getReviews(self):
        # return [Review('movie_url', TYPE_CRITIC, 'cname', 'curl', True, 0.23, 'text', datetime.date(2013,2,3))]
        reviews = []
        for page_num in range(1, 1000):
            page_url = self.getReviewUrl(page_num) 
            print(f"Getting url {page_url}")
            resp = rq.get(page_url)
            if not resp.ok:
                print(f"Finish scraping, page {page_num} does not exist")
                break
            soup = BeautifulSoup(resp.text, 'lxml')
            reviews += self.getReviewsFromPage(soup)
            print(f"Scraped {page_url}")
            if page_num > 50:
                raise Exception(f"Something's wrong, page already on {page_num}")
        return reviews

    def getReviewUrl(self, page_num=1):
        return self.movie_url.rstrip('/') + f'/reviews/?page={page_num}'

    def getReviewsFromPage(self, page_soup):
        raise NotImplementedError

# Audience Reviews inherits from RTScore
class AudienceReviews(BaseReviews):
    def getReviewUrl(self, page_num=1):
        return self.movie_url.rstrip('/') + '/reviews/?type=user&page={page_num}'

    def getReviewsFromPage(self, page_soup):
        raise NotImplementedError

# Audience Reviews inherits from RTScore
class CriticReviews(BaseReviews):
    def getReviewsFromPage(self, page_soup):
        review_list = []
        reviews = page_soup.find('div', {'id': 'reviews'})
        for review in reviews.findChildren('div', {'class': 'row review_table_row'}):
            try:
                critic = review.find('div', {'class': 'critic_name'})
                critic_name = critic.text.strip()
                critic_url = critic.find('a').get('href')
                date = dateparser.parse(review.find('div', {'class': 'review_date'}).text.strip()).date()
                text = review.find('div', {'class': 'the_review'}).text.strip()
                fresh = bool(review.find('div', {'class': 'fresh'}))
                small_subtle = review.find('div', {'class': 'small subtle'})
                if small_subtle:
                    score = re.search("Original Score: (.+)$", small_subtle.text)
                    if score:
                        score = self.parse_score(score.group(1))
                    else:
                        score = None
                review_list.append(Review(self.movie_url, TYPE_CRITIC, critic_name, critic_url, fresh, score, text, date))
            except:
                print(f"ERROR parsing {review.__str__()}")
                traceback.print_exc()
                raise

        return review_list

    def parse_score(self, score_text):
        score_text = score_text.strip().replace("'", "")
        try:
            if '/' in score_text:
                n, d = score_text.split('/')
                return float(n) / float(d)
            match = re.match(r"([A-F])([+-]*)", score_text)
            if match:
                letter = match.group(1)
                score = 6 + ord('A') - ord(letter) 
                if match.group(2) == '+':
                    score += 0.5
                elif match.group(2) == '-':
                    score -= 0.5
                return score / 7
        except:
            print(f"PROBLEM parsing score: {score_text}")
            return None


# class that grabs Rotten Tomatoes scores and link to reviews page
class RTMovie:
    # initialized to website of movie on Rotten Tomatoes
    def __init__(self, imdb_id, rt_url):
        self.imdb_id = imdb_id
        self.url = rt_url

    # Tomatometer score
    def criticScore(self, soup):
        score = soup.find('span', {'class': "meter-value superPageFontColor"})
        return int(score.text.replace('%', ''))

    def audienceScore(self, soup):
        meter = soup.find('div', {'class': "audience-score meter"})
        score = meter.find('span', {'class': "superPageFontColor"})
        return int(score.text.replace('%', ''))

    def audienceReviews(self):
        return AudienceReviews(self.url).getReviews()

    def criticReviews(self):
        return CriticReviews(self.url).getReviews()

    def removeDuplicatedReviews(self, reviews):
        deduplicated = []
        key = lambda x: (x.reviewer_type, x.reviewer_url, x.reviewer_name, x.date)
        reviews.sort(key=key)
        for _, group in groupby(reviews, key=key):
            items = list(group)
            if len(items) == 1:
                deduplicated += items 
        return deduplicated

    def save_reviews(self, reviews):
        reviews = self.removeDuplicatedReviews(reviews)
        try:
            with session_scope() as session:
                session.bulk_save_objects([RTReview(
                    type=r.reviewer_type,
                    movie_imdb_id=self.imdb_id,
                    reviewer_url=r.reviewer_url,
                    reviewer_name=r.reviewer_name,
                    fresh=r.fresh,
                    original_score=r.original_score,
                    review_text=r.text,
                    review_date=r.date
                ) for r in reviews])
        except:
            print(f"Problem saving")
            for r in sorted(reviews, key=lambda x: (x.reviewer_type, x.reviewer_url, x.date)):
                print(f"{r.reviewer_url}, {r.date}, {r.reviewer_name}, {r.fresh}, {r.original_score} {r.text}")
            raise

    def scrape(self, update_after=None):
        scrape_id = f"rt_{self.imdb_id}_critic_reviews"
        scrape_date = ScrapingLog.get_date(scrape_id)
        if not scrape_date or (update_after and scrape_date < update_after):
            soup = BeautifulSoup(rq.get(self.url).text, 'lxml')
            with session_scope() as session:
                movie = session.query(Movie).get(self.imdb_id)
                movie.rt_tomato_score = self.criticScore(soup)
                movie.rt_audience_score = self.audienceScore(soup)
                session.bulk_save_objects([movie])

            critic_reviews = self.criticReviews()
            self.save_reviews(critic_reviews)
            ScrapingLog.add_log(scrape_id)
        else:
            print(f"Skip scraping {scrape_id}: Already scraped")
            

def scrape_oscar_movies():
    with session_scope() as session:
        movies_to_scrape = list(session.query(Movie) \
                                       .join(MovieAward, Movie.imdb_id==MovieAward.movie_imdb_id) \
                                       .filter(MovieAward.award_category.in_(['Best Motion Picture of the Year', 'Best Picture'])) \
                                       .distinct() \
                                       .values(Movie.imdb_id, Movie.rt_url))

    for imdb_id, rt_url in movies_to_scrape:
        print(f"Start scraping {rt_url}, id: {imdb_id}")
        RTMovie(imdb_id, rt_url).scrape()
        print(f"Scraped {rt_url}")

scrape_oscar_movies()
# RTMovie('tt5580390', 'https://www.rottentomatoes.com/m/the_shape_of_water_2017').scrape()

