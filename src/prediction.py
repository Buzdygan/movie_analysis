from itertools import product

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression, LinearRegression, SGDClassifier
from sklearn.svm import SVC


from constants import AWARD_COLUMNS


BASE_COLUMNS = ['year', 'title', 'winner']
PRED_SCORE_COL = 'predicted_score'
AWARDS = 'Awards'
CRITICS = 'Critics'
EVALUATION_START_YEAR = 2000

def iterate_cases(full_df, level=None):
    for year in full_df['year'].drop_duplicates().tolist():
        if year >= EVALUATION_START_YEAR:
            if level:
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


class BasePredictor(object):
    @classmethod
    def hparam_combinations(cls):
        return [{}]

    def __init__(self, train_df, test_df, hparam_dict):
        self._train_df = self.adjust_data(train_df)
        self._test_df = self.adjust_data(test_df)
        self._hparam_dict = hparam_dict

    @property
    def hparams(self):
        return self._hparam_dict.get(self.NAME, {})

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

class RandomForestPredictor(SklearnPredictor):
    MODEL_CLASS = RandomForestClassifier

class LogisticPredictor(SklearnPredictor):
    MODEL_CLASS = LogisticRegression

class SVCPredictor(SklearnPredictor):
    MODEL_CLASS = SVC

    @classmethod
    def hparam_combinations(cls):
        return [{'probability': True}]

class SGDPredictor(SklearnPredictor):
    MODEL_CLASS = SGDClassifier

    @classmethod
    def hparam_combinations(cls):
        return [{'loss': 'log', 'alpha': alpha}
                for alpha in [0.1, 0.01, 0.001]]


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
                                   SGDPredictor
                                  ]
                 ]

    def predict(self):
        results = [predictor_cls(self._train_df, self._test_df, self._hparam_dict).predict()
                   for predictor_cls in self.PREDICTORS]
        return sum(results) / len(self.PREDICTORS)


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
                predictor = predictor_cls(year_train_df, year_test_df, self._hparam_dict)
                year_df[predictor.NAME] = predictor.predict()
            year_dfs.append(year_df)
        train_df = pd.concat(year_dfs)

        test_df = self._test_df.copy()[['year', 'title', 'winner']].reset_index()
        for predictor_cls in self.PREDICTORS:
            predictor = predictor_cls(self._train_df, self._test_df, self._hparam_dict)
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


class WeightAdjustingPredictor(BasePredictor):
    ENSEMBLE_CLASS = SimpleEnsemblePredictor
    def _possible_hparams(self):
        predictors = self.ENSEMBLE_CLASS.PREDICTORS + [self.ENSEMBLE_CLASS]
        for choice in product(*[pred.hparam_combinations() for pred in predictors]):
            yield {predictor.__name__: hdict for predictor, hdict in zip(predictors, choice)}

    def predict(self):
        best_score, best_hparams = 0, None
        for hparams_dict in self._possible_hparams():
            print("Try hparams")
            print(hparams_dict)
            year_dfs = []
            for year_train_df, year_test_df, year_df in iterate_cases(self._train_df):
                ens_predictor = self.ENSEMBLE_CLASS(year_train_df, year_test_df, hparams_dict)
                year_df[PRED_SCORE_COL] = ens_predictor.predict()
                year_dfs.append(year_df)
            predicted_df = pd.concat(year_dfs)
            score = get_avg_norm_score(predicted_df)
            if score > best_score:
                best_score = score
                best_hparams = hparams_dict
            print(f"Score: {score}, best: {best_score}")
        
        ens_predictor = self.ENSEMBLE_CLASS(self._train_df, self._test_df, best_hparams)
        return ens_predictor.predict()


def evaluate(data_df):
    year_dfs = []
    for ytrain_df, ytest_df, ydf in iterate_cases(data_df, "Outer Evaluation"):
        wa_predictor = WeightAdjustingPredictor(ytrain_df, ytest_df, {})
        ydf[PRED_SCORE_COL] = wa_predictor.predict()
        year_dfs.append(ydf)
    result_df = pd.concat(year_dfs)
    avg_nscore = get_avg_norm_score(result_df)
    accuracy = get_accuracy(result_df)
    print(f"Avg Nscore: {avg_nscore:.2}, Accuracy: {accuracy:.2}")



