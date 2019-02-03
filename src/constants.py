#!/usr/local/bin/python3

from collections import namedtuple

from constants_local import OMDB_API_KEY

DB_PATH = 'sqlite:////Users/jakubtlalka/it/ds/projects/movies/movies.sqlite'

IMDB_BASE_URL = 'https://www.imdb.com'

BLANK_IMDB_ID = 'blank_imdb_id'
BLANK_PERSON_NAME = 'blank_person_name'

BEST_FILM_CATEGORY = 'Best Motion Picture of the Year'
BEST_FOREIGN_FILM_CATEGORY = 'Best Foreign Language Film of the Year'


VENICE_BEST_FILM_CATEGORY = 'Golden Lion - Best Film'
CANNES_BEST_FILM_CATEGORY = "Palme d'Or"
PGA_BEST_FILM_CATEGORY = 'PGA Award - Outstanding Producer of Theatrical Motion Pictures'
SAG_BEST_FILM_CATEGORY = 'Actor - Outstanding Performance by a Cast in a Motion Picture'
DGA_BEST_FILM_CATEGORY = 'DGA Award - Outstanding Directorial Achievement in Feature Film'
GLOBES_BEST_DRAMA_CATEGORY = 'Golden Globe - Best Motion Picture - Drama'
GLOBES_BEST_COMEDY_CATEGORY = 'Golden Globe - Best Motion Picture - Comedy or Musical'
GLOBES_BEST_FOREIGN_FILM_CATEGORY = 'Golden Globe - Best Foreign Language Film'
BAFTA_BEST_FILM_CATEGORY = 'BAFTA Film Award - Best Film'
BAFTA_BEST_NON_ENGLISH_FILM_CATEGORY = 'BAFTA Film Award - Best Film not in the English Language'
CRITICS_BEST_FILM_CATEGORY = 'Critics Choice Award - Best Picture'
CRITICS_BEST_FOREIGN_FILM_CATEGORY = 'Critics Choice Award - Best Foreign Language Film'

AWARD_DICT = {
    'venice': VENICE_BEST_FILM_CATEGORY,
    'cannes': CANNES_BEST_FILM_CATEGORY,
    'pga': PGA_BEST_FILM_CATEGORY,
    'sag': SAG_BEST_FILM_CATEGORY,
    'dga': DGA_BEST_FILM_CATEGORY,
    'globes_drama': GLOBES_BEST_DRAMA_CATEGORY,
    'globes_comedy': GLOBES_BEST_COMEDY_CATEGORY,
    'globes_foreign': GLOBES_BEST_FOREIGN_FILM_CATEGORY,
    'bafta': BAFTA_BEST_FILM_CATEGORY,
    'bafta_nonenglish': BAFTA_BEST_NON_ENGLISH_FILM_CATEGORY,
    'critics': CRITICS_BEST_FILM_CATEGORY,
    'critics_foreign': CRITICS_BEST_FOREIGN_FILM_CATEGORY,
}

Review = namedtuple('Review', ['movie_url', 'reviewer_type', 'reviewer_name', 'reviewer_url', 'fresh', 'original_score', 'text', 'date'])

TYPE_CRITIC = 'critic'
TYPE_USER = 'user'
RT_BASE_URL = "https://www.rottentomatoes.com"

AWARD_WINNER = 'winner'
AWARD_NOMINEE = 'nominee'

IMDB_TYPE_MOVIE = 'title'
IMDB_TYPE_PERSON = 'name'
