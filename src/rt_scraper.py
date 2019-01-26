from bs4 import BeautifulSoup
import requests as rq 

from collections import namedtuple

Review = namedtuple('Review', ['movie_url', 'reviewer_type', 'reviewer_name', 'reviewer_url', 'rating', 'text', 'date'])

TYPE_CRITIC = 'critic'
TYPE_USER = 'user'
RT_BASE_URL = "https://www.rottentomatoes.com"


class BaseReviews(object):
    def __init__(self, movie_url):
        self.movie_url = movie_url

    # to get the url of the next page
    def nextPageUrl(self, soup):
        page_section = soup.find('span', {'class': 'pageInfo'})
        try:
            next_page = page_section.findNext('a', {'class': 'btn btn-xs btn-primary-rt'})['href']
            return RT_BASE_URL + next_page
        except:
            return None

    def getReviews(self):
        reviews = []
        page_url = self.getReviewUrl() 
        while page_url:
            soup = BeautifulSoup(rq.get(page_url).text, 'lxml')
            reviews += self.getReviewsFromPage(soup)
            page_url = self.nextPageUrl(soup)
        return reviews

    def getReviewUrl(self):
        return self.movie_url.rstrip('/') + '/reviews/'

    def getReviewsFromPage(self, page_soup):
        raise NotImplementedError

# Audience Reviews inherits from RTScore
class AudienceReviews(BaseReviews):
    def getReviewUrl(self):
        return self.movie_url.rstrip('/') + '/reviews/?type=user'

    def getReviewsFromPage(self, page_soup):
        raise NotImplementedError

# Audience Reviews inherits from RTScore
class CriticReviews(BaseReviews):
    def getReviewsFromPage(self, page_soup):
        review_list = []
        reviews = page_soup.find('div', {'id': 'reviews'})
        review = reviews.findNext('div', {'class': 'row review_table_row'})
        while review:
            critic = review.find('div', {'class': 'critic_name'}).find('a', {'class': 'articleLink'})
            critic_name = critic.text.strip()
            critic_url = critic.get('href')
            date = review.find('div', {'class': 'review_date'}).text.strip()
            text = review.find('div', {'class': 'the_review'}).text.strip()
            rating = int(bool(review.find('div', {'class': 'fresh'})))
            review_list.append(Review(self.movie_url, TYPE_CRITIC, critic_name, critic_url, rating, text, date))
            review = review.findNext('div', {'class': 'row review_table_row'})
        return review_list

# class that grabs Rotten Tomatoes scores and link to reviews page
class RTMovie:
    # initialized to website of movie on Rotten Tomatoes
    def __init__(self, url):
        self.url = url
        self.soup = BeautifulSoup(rq.get(url).text, 'lxml')

    # Tomatometer score
    def criticScore(self):
        meter = "meter-value superPageFontColor"
        score = self.soup.find('span', {'class': meter})
        return score.text

    def audienceScore(self):
        audience_meter = "audience-score meter"
        audience_score = "superPageFontColor"
        meter = self.soup.find('div', {'class': audience_meter})
        score = meter.find('span', {'class': audience_score})
        return score.text

    def audienceReviews(self):
        return AudienceReviews(self.url)

    def criticReviews(self):
        return CriticReviews(self.url)