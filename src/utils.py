import pandas as pd
import numpy as np
from sklearn import preprocessing
from storage import session_scope, Movie, MovieAward, RTReview
from constants import OSCARS_BEST_FILM


def get_top_critics_df(df, review_prc=0.75):
    num_movies = df['title'].nunique()
    return df.groupby('reviewer_url').filter(lambda x: len(x) >= num_movies * review_prc)

def add_score(relevant_df):
    def compute_add_score(rows):
        fresh_score, rotten_score = 1, 0
        scored = rows[rows.original_score.notnull()]
        if len(scored) > 0:
            fresh = scored[scored.fresh == True]
            if len(fresh) > 0:
                fresh_score = fresh['original_score'].mean()
            rotten = scored[scored.fresh == False]
            if len(rotten) > 0:
                rotten_score = rotten['original_score'].mean()
        return pd.Series([fresh_score, rotten_score])

    def choose_score(x):
        if np.isnan(x['original_score']):
            if x['fresh']:
                return x['fresh_score']
            else:
                return x['rotten_score']
        return x['original_score']

    critic_score_df = relevant_df.groupby('reviewer_url', as_index=True).apply(compute_add_score).reset_index()
    critic_score_df.columns = ['reviewer_url', 'fresh_score', 'rotten_score']
    joined_df = pd.merge(relevant_df, critic_score_df, on='reviewer_url')
    joined_df['score'] = joined_df.apply(choose_score, axis=1)

    # Normalize score
    joined_df['score'] = joined_df.groupby('reviewer_url')['score'].transform(preprocessing.scale)
    return joined_df.drop(['fresh_score', 'rotten_score'], axis=1)


def get_award_winners_df(remove_oscars=True):
    with session_scope() as session:
        movie_awards_df = pd.read_sql(session.query(MovieAward).statement, session.bind)

    df = movie_awards_df.drop(['award_date'], axis=1).drop_duplicates()
    df = df[df.award_category != OSCARS_BEST_FILM]
    df = df.pivot(index='movie_wiki_url', columns='award_category', values='winner') \
           .fillna(-1).applymap(int).reset_index()

    return df


def get_awards_df(category=OSCARS_BEST_FILM):
    with session_scope() as session:
        movies_df = pd.read_sql(session.query(Movie).statement, session.bind)
        movie_awards_df = pd.read_sql(session.query(MovieAward).statement, session.bind)

    madf = movie_awards_df[movie_awards_df.award_category == category].drop(['award_category'],
                                                                            axis=1).drop_duplicates()
    df = pd.merge(madf, 
                  movies_df.drop(['release_year', 'countries', 'box_office', 'rt_url'], axis=1),
                  on='movie_wiki_url').rename(columns={'imdb_id': 'movie_imdb_id'})
    return df


def get_relevant_df(category=OSCARS_BEST_FILM, min_year=2000):
    with session_scope() as session:
        reviews_df = pd.read_sql(session.query(RTReview).statement, session.bind)

    full_df = pd.merge(get_awards_df(category=category),
                       reviews_df,
                       on='movie_imdb_id').drop(['type', 'reviewer_name'], axis=1)

    # We only consider reviews that were written BEFORE the Oscars.
    df = full_df[full_df.award_date > full_df.review_date][[
        'movie_wiki_url', 'award_date', 'winner', 'title', 'reviewer_url', 'fresh', 'original_score', 'rt_tomato_score', 'rt_audience_score'
    ]]
    df['year'] = df.apply(lambda x: x.award_date.year, axis=1)
    df = df.drop('award_date', axis=1)
    df = df[df.year >= min_year]
    df = df.drop_duplicates(subset=['reviewer_url', 'movie_wiki_url'])
    return add_score(df)


def get_title_map():
    with session_scope() as session:
        movies_df = pd.read_sql(session.query(Movie).statement, session.bind)
    return movies_df[['title', 'movie_wiki_url']]


def get_movie_df(category=OSCARS_BEST_FILM, review_prc=0.75):
    awinners_df = get_award_winners_df()
    oscars_df = get_awards_df(category=category)
    awards_df = oscars_df.merge(awinners_df, on='movie_wiki_url')
    awards_df['year'] = awards_df.apply(lambda x: x.award_date.year, axis=1)
    awards_df = awards_df.drop(['award_date', 'movie_title', 'movie_imdb_id', 'directors',
                                'imdb_votes', 'imdb_rating', 'movie_wiki_url',
                                'actors', 'runtime', 'genres', 'rt_tomato_score', 'rt_audience_score'], axis=1)

    rel_df = get_relevant_df()
    top_df = get_top_critics_df(rel_df, review_prc=review_prc)
    info_df = top_df[['movie_wiki_url', 'winner', 'year', 'title']].drop_duplicates()
    critic_df = top_df.pivot(index='movie_wiki_url', columns='reviewer_url', values='score').fillna(0).reset_index()
    critic_df = info_df.merge(critic_df, on='movie_wiki_url').drop('movie_wiki_url', axis=1)

    df = awards_df.merge(critic_df.drop('winner', axis=1), on=['year', 'title'], how='left')
    return df[df.year >= 1960][df.year <= 2018]