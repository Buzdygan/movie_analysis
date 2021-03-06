#!/usr/local/bin/python3

from collections import namedtuple

from constants_local import OMDB_API_KEY

DB_PATH = 'sqlite:////Users/jakubtlalka/it/ds/projects/movies/movies.sqlite'

WIKI_BASE = 'https://en.wikipedia.org'

BEST_FILM_CATEGORY = 'Best Motion Picture of the Year'
BEST_FOREIGN_FILM_CATEGORY = 'Best Foreign Language Film of the Year'


OSCARS_BEST_FILM = 'oscars'
OSCARS_BEST_FOREIGN_FILM = 'oscars_foreign'
VENICE_BEST_FILM = 'venice'
CANNES_BEST_FILM = 'cannes'
PGA_BEST_FILM = 'pga'
SAG_BEST_FILM = 'sag'
DGA_BEST_FILM = 'dga'
GLOBES_BEST_DRAMA = 'globes_drama'
GLOBES_BEST_COMEDY = 'globes_comedy'
GLOBES_BEST_FOREIGN_FILM = 'globes_foreign'
BAFTA_BEST_FILM = 'bafta'
BAFTA_BEST_NON_ENGLISH_FILM = 'bafta_nonenglish'
CRITICS_BEST_FILM = 'critics'
CRITICS_BEST_FOREIGN_FILM = 'critics_foreign'


AWARD_COLUMNS = [CANNES_BEST_FILM, PGA_BEST_FILM, SAG_BEST_FILM, DGA_BEST_FILM, GLOBES_BEST_DRAMA, GLOBES_BEST_COMEDY, BAFTA_BEST_FILM, CRITICS_BEST_FILM]


Review = namedtuple('Review', ['movie_url', 'reviewer_type', 'reviewer_name', 'reviewer_url', 'fresh', 'original_score', 'text', 'date'])

TYPE_CRITIC = 'critic'
TYPE_USER = 'user'
RT_BASE_URL = "https://www.rottentomatoes.com"

AWARD_WINNER = 'winner'
AWARD_NOMINEE = 'nominee'

IMDB_TYPE_MOVIE = 'title'
IMDB_TYPE_PERSON = 'name'
