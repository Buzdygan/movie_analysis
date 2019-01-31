import pandas as pd
import numpy as np
from sklearn import preprocessing


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