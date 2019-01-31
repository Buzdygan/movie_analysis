#!/usr/local/bin/python3
import datetime
from contextlib import contextmanager

import pandas as pd
import numpy as np
import sqlalchemy as db
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, Column, Integer, Float, Boolean, String, Text, Date, ForeignKey
from sqlalchemy_utils.types import JSONType

from constants import DB_PATH
from utils import add_score


engine = create_engine(DB_PATH)
Base = declarative_base()
Session = sessionmaker(bind=engine)


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


class Movie(Base):
    __tablename__ = 'movies'

    imdb_id = Column(String, primary_key=True)
    title = Column(String)
    release_year = Column(Integer)
    directors = Column(JSONType)
    actors = Column(JSONType)
    runtime = Column(String)
    genres = Column(JSONType)
    countries = Column(JSONType)
    imdb_rating = Column(Float)
    imdb_votes = Column(Integer)
    box_office = Column(String)
    rt_url = Column(Text)
    rt_tomato_score = Column(Integer)
    rt_audience_score = Column(Integer)


class MovieAward(Base):
    __tablename__ = 'movie_awards'
    award_id = Column(String, primary_key=True)
    award_category = Column(String, primary_key=True)
    movie_imdb_id = Column(String, primary_key=True)
    person_imdb_id = Column(String, primary_key=True)
    award_date = Column(Date, primary_key=True)
    winner = Column(Boolean, primary_key=True)
    award_name = Column(String)
    person_name = Column(String)


class Award(Base):
    __tablename__ = 'awards'
    award_id = Column(String, primary_key=True)
    award_name = Column(String)
    start_year = Column(Integer)
    end_year = Column(Integer)
    date_timedelta = Column(Integer)

class RTReview(Base):
    __tablename__ = 'rt_reviews'
    type = Column(String, primary_key=True)
    movie_imdb_id = Column(String, primary_key=True)
    reviewer_url = Column(String, primary_key=True)
    reviewer_name = Column(String, primary_key=True)
    review_date = Column(Date, primary_key=True)
    fresh = Column(Boolean)
    original_score = Column(Float)
    review_text = Column(Text)


class ScrapingLog(Base):
    __tablename__ = 'scraping_log'
    scrape_id = Column(String, primary_key=True)
    scrape_date = Column(Date)

    @classmethod
    def get_date(cls, scrape_id):
        with session_scope() as session:
            obj = session.query(cls).get(scrape_id)
            if obj is not None:
                return obj.scrape_date

    @classmethod
    def add_log(cls, scrape_id):
        date = datetime.datetime.now().date()
        with session_scope() as session:
            obj = session.query(cls).get(scrape_id)
            if obj is None:
                obj = cls(scrape_id=scrape_id)
            obj.scrape_date = date
            session.add(obj)


Base.metadata.create_all(engine)




def get_relevant_df(category='Best Motion Picture of the Year'):
    with session_scope() as session:
        movies_df = pd.read_sql(session.query(Movie).statement, session.bind)
        movie_awards_df = pd.read_sql(session.query(MovieAward).statement, session.bind)
        reviews_df = pd.read_sql(session.query(RTReview).statement, session.bind)

    madf = movie_awards_df[movie_awards_df.award_category == category].drop(['person_imdb_id',
                                                                             'person_name',
                                                                             'award_id',
                                                                             'award_name',
                                                                             'award_category'],
                                                                            axis=1).drop_duplicates()
    df_ = pd.merge(madf, 
               movies_df.drop(['release_year', 'countries', 'box_office', 'rt_url'], axis=1),
               left_on='movie_imdb_id',
               right_on='imdb_id').drop('imdb_id', axis=1)
    
    full_df = pd.merge(df_, reviews_df, on='movie_imdb_id').drop(['movie_imdb_id', 'type', 'reviewer_name'], axis=1)

    # We only consider reviews that were written BEFORE the Oscars.
    df = full_df[full_df.award_date > full_df.review_date][[
        'award_date', 'winner', 'title', 'reviewer_url', 'fresh', 'original_score', 'rt_tomato_score', 'rt_audience_score'
    ]]
    df['year'] = df.apply(lambda x: x.award_date.year, axis=1)
    df = df.drop('award_date', axis=1)

    return add_score(df)
