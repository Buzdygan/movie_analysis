import warnings
import sys
from itertools import product

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression, LinearRegression, SGDClassifier
from sklearn.svm import SVC

from utils import get_movie_df
from constants import AWARD_COLUMNS

# AWARDS + CRITICS >= 2000 : Avg Nscore: 0.84, Rank Score: 0.91, Accuracy: 0.63

BASE_COLUMNS = ['year', 'title', 'winner']
PRED_SCORE_COL = 'predicted_score'
AWARDS = 'Awards'
CRITICS = 'Critics'
EVALUATION_START_YEAR = 1960

def iterate_cases(full_df, level=None):
    for year in full_df['year'].drop_duplicates().tolist():
        if year >= EVALUATION_START_YEAR:
            if level:
                print(f"{level} Year: {year}", file=sys.stderr)
                print(f"{level} Year: {year}")
            df = full_df.copy()
            year_train_df = df[df.year != year]
            year_test_df = df[df.year == year]
            year_df = year_test_df.copy()[['year', 'title', 'winner']].reset_index()
            yield year_train_df, year_test_df, year_df


def get_avg_norm_score(orig_df, col=PRED_SCORE_COL):
    df = orig_df.copy()
    df['norm_score'] = df.groupby('year')[col].transform(lambda x: (x - x.min()) / (x.max() - x.min()))
    return df[df.winner]['norm_score'].mean()


def get_accuracy(orig_df, col=PRED_SCORE_COL):
    df = orig_df.copy()
    df['pred_winner'] = (df.groupby('year')[col].transform(max) == df[col]).apply(int)
    return df[df.winner]['pred_winner'].mean()


def get_rank_score(orig_df, col=PRED_SCORE_COL):
    df = orig_df.copy()
    df['rank'] = df.groupby('year')[col].rank(ascending=False)
    year_cnt_df = df.groupby('year')[col].count().reset_index().rename(columns={col: 'year_cnt'})
    df = df.merge(year_cnt_df)
    df['rscore'] = df.apply(lambda x: 1.0 - (x['rank'] - 1) / (x['year_cnt'] - 1), axis=1) 
    return df[df.winner]['rscore'].mean()


def choose_hparams(predictor_cls, train_df, evaluation_method=get_rank_score):
    best_score = 0.0
    best_hparams = None
    for hparams in predictor_cls.HPARAM_COMBINATIONS:
        year_dfs = []
        for year_train_df, year_test_df, year_df in iterate_cases(train_df):
            predictor = predictor_cls(year_train_df, year_test_df, hparams)
            year_df[PRED_SCORE_COL] = predictor.predict()
            year_dfs.append(year_df)
        result_df = pd.concat(year_dfs)
        score = evaluation_method(result_df) 
        if score > best_score:
            best_score = score
            best_hparams = hparams
    print(f"Best hparams for {predictor_cls.__name__}: {best_hparams} : {best_score}")
    return best_hparams, best_score


class BasePredictor(object):
    HPARAM_COMBINATIONS = [{}]

    def __init__(self, train_df, test_df, hparams=None):
        self._train_df = self.adjust_data(train_df)
        self._test_df = self.adjust_data(test_df)
        self._hparams = hparams

    @property
    def hparams(self):
        return self._hparams

    @property
    def NAME(self):
        return self.__class__.__name__

    def xy(self, data_df):
        return data_df.drop(BASE_COLUMNS, axis=1), data_df['winner']

    def adjust_data(self, data_df):
        return data_df

    def predict(self):
        """
        Return pandas series with predicted scores corresponding to
        `self._test_df` rows
        """
        raise NotImplementedError


class CriticPredictorMixin(BasePredictor):
    def adjust_data(self, data_df):
        return data_df[data_df.year >= 2000].drop(AWARD_COLUMNS, axis=1)


class AwardPredictorMixin(BasePredictor):
    def adjust_data(self, data_df):
        return data_df[BASE_COLUMNS + AWARD_COLUMNS]


class SklearnPredictor(BasePredictor):
    MODEL_CLASS = None
    def predict(self):
        model = self.MODEL_CLASS(**self.hparams).fit(*self.xy(self._train_df))
        return pd.Series(model.predict_proba(self.xy(self._test_df)[0])[:, 1])

class GradientBoostingPredictor(SklearnPredictor):
    MODEL_CLASS = GradientBoostingClassifier
    HPARAM_COMBINATIONS = [{'loss': loss, 'learning_rate': lrate, 'max_depth': max_depth}
                           for loss in ['deviance', 'exponential']
                           for lrate in [0.01, 0.03, 0.1, 0.3, 1.0]
                           for max_depth in [2, 3, 4, 5]]

class RandomForestPredictor(SklearnPredictor):
    MODEL_CLASS = RandomForestClassifier
    HPARAM_COMBINATIONS = [{'criterion': criterion, 'max_depth': max_depth, 'n_estimators': n_estimators}
                           for criterion in ['gini', 'entropy']
                           for max_depth in [None, 2, 3, 4]
                           for n_estimators in [10, 50, 100]]

class LogisticPredictor(SklearnPredictor):
    MODEL_CLASS = LogisticRegression
    HPARAM_COMBINATIONS = [{'C': c} for c in [0.1, 0.3, 1.0, 3.0]]

class SVCPredictor(SklearnPredictor):
    MODEL_CLASS = SVC
    HPARAM_COMBINATIONS = [{'probability': True, 'C': c}
                           for c in [0.1, 0.3, 1.0, 3.0, 10.0]]

class SGDPredictor(SklearnPredictor):
    MODEL_CLASS = SGDClassifier
    HPARAM_COMBINATIONS = [{'loss': 'log', 'alpha': alpha}
                           for alpha in [0.01, 0.03, 0.1, 0.3]]


def P(predictor_cls, tp='Awards'):
    return type(f"{tp}{predictor_cls.__name__}",
                (AwardPredictorMixin if tp == AWARDS else CriticPredictorMixin, predictor_cls),
                {})


class SimpleEnsemblePredictor(BasePredictor):
    PREDICTORS = [P(pred_cls, tp)
                  for tp in [AWARDS]
                  for pred_cls in [RandomForestPredictor,
                                   LogisticPredictor,
                                   SVCPredictor,
                                   SGDPredictor,
                                   GradientBoostingPredictor
                                  ]
                 ]

    def predict(self):
        results = []
        weight_sum = 0.0
        for predictor_cls in self.PREDICTORS:
            hparams, weight = choose_hparams(predictor_cls, self._train_df)
            predictor = predictor_cls(self._train_df,
                                      self._test_df,
                                      hparams)
            results.append(predictor.predict() * weight)
            weight_sum += weight
        return sum(results) / weight_sum


class EnsemblePredictor(BasePredictor):
    PREDICTORS = [P(pred_cls, tp)
                  for tp in [AWARDS]
                  for pred_cls in [RandomForestPredictor,
                                   LogisticPredictor,
                                   SVCPredictor,
                                   SGDPredictor
                                  ]
                 ]

    def predict(self):
        train_df, test_df = self.get_children_data()
        """
        LINEAR COMBINATION
        model = LinearRegression().fit(*self.xy(train_df))
        columns = self.xy(train_df)[0].columns
        for pname, coeff in zip(list(columns), list(model.coef_)):
            print(f"        {pname}: {coeff:.2}")
        return pd.Series(model.predict(self.xy(test_df)[0]))
        """

        model = LogisticRegression().fit(*self.xy(train_df))
        columns = self.xy(train_df)[0].columns
        for pname, coeff in zip(list(columns), list(model.coef_[0])):
            print(f"        {pname}: {coeff:.2}")
        return pd.Series(model.predict_proba(self.xy(test_df)[0])[:, 1])

    def get_children_data(self):
        year_dfs = []
        for year_train_df, year_test_df, year_df in iterate_cases(self._train_df):
            for predictor_cls in self.PREDICTORS:
                predictor = predictor_cls(year_train_df,
                                          year_test_df,
                                          choose_hparams(predictor_cls, year_train_df))
                year_df[predictor.NAME] = predictor.predict()
            year_dfs.append(year_df)
        train_df = pd.concat(year_dfs)

        test_df = self._test_df.copy()[['year', 'title', 'winner']].reset_index()
        for predictor_cls in self.PREDICTORS:
            predictor = predictor_cls(self._train_df,
                                      self._test_df,
                                      choose_hparams(predictor_cls, self._train_df))
            test_df[predictor.NAME] = predictor.predict()

        # Normalize
        for predictor_cls in self.PREDICTORS:
            col = predictor_cls.__name__
            """
            nscore = get_avg_norm_score(train_df, col)
            accuracy = get_accuracy(train_df, col)
            print(f"    {col}: nscore: {nscore:.2}, accuracy: {accuracy:.2}")
            """
            joined_df = pd.concat([train_df, test_df])
            mean = joined_df[col].mean()
            std = joined_df[col].std()
            train_df[col] = train_df[col].transform(lambda x: (x - mean) / std)
            test_df[col] = test_df[col].transform(lambda x: (x - mean) / std)
        return train_df, test_df


def evaluate(data_df):
    year_dfs = []
    for ytrain_df, ytest_df, ydf in iterate_cases(data_df, "Outer Evaluation"):
        wa_predictor = SimpleEnsemblePredictor(ytrain_df, ytest_df)
        ydf[PRED_SCORE_COL] = wa_predictor.predict()
        year_dfs.append(ydf)
        print(f"Year rscore: {get_rank_score(ydf):.2}")
    result_df = pd.concat(year_dfs)
    avg_rscore = get_rank_score(result_df)
    avg_nscore = get_avg_norm_score(result_df)
    accuracy = get_accuracy(result_df)
    print(f"Avg Nscore: {avg_nscore:.2}, Rank Score: {avg_rscore:.2}, Accuracy: {accuracy:.2}")
    return result_df



if __name__ == "__main__":
    warnings.filterwarnings('ignore')
    movie_df = get_movie_df()
    result_df = evaluate(movie_df)
    result_df.to_csv('results_awards_1960.csv')
