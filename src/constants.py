#!/usr/local/bin/python3

from collections import namedtuple

from constants_local import OMDB_API_KEY

DB_PATH = 'sqlite:////Users/jakubtlalka/it/ds/projects/movies/movies.sqlite'

IMDB_BASE_URL = 'https://www.imdb.com'

BLANK_IMDB_ID = 'blank_imdb_id'
BLANK_PERSON_NAME = 'blank_person_name'

BEST_FILM_CATEGORY = 'Best Motion Picture of the Year'
BEST_FOREIGN_FILM_CATEGORY = 'Best Foreign Language Film of the Year'

Review = namedtuple('Review', ['movie_url', 'reviewer_type', 'reviewer_name', 'reviewer_url', 'fresh', 'original_score', 'text', 'date'])

TYPE_CRITIC = 'critic'
TYPE_USER = 'user'
RT_BASE_URL = "https://www.rottentomatoes.com"

AWARD_WINNER = 'winner'
AWARD_NOMINEE = 'nominee'

IMDB_TYPE_MOVIE = 'title'
IMDB_TYPE_PERSON = 'name'
