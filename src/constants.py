#!/usr/local/bin/python3

from collections import namedtuple

from constants_local import OMDB_API_KEY

DB_PATH = 'sqlite:////Users/jakubtlalka/it/ds/projects/movies/movies.sqlite'

IMDB_BASE_URL = 'https://www.imdb.com'

Review = namedtuple('Review', ['movie_url', 'reviewer_type', 'reviewer_name', 'reviewer_url', 'fresh', 'original_score', 'text', 'date'])

TYPE_CRITIC = 'critic'
TYPE_USER = 'user'
RT_BASE_URL = "https://www.rottentomatoes.com"

AWARD_WINNER = 'winner'
AWARD_NOMINEE = 'nominee'

IMDB_TYPE_MOVIE = 'title'
IMDB_TYPE_PERSON = 'name'
