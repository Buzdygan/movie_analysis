import requests as rq 
import traceback

from storage import session_scope, Movie, MovieAward
from constants import OMDB_API_KEY


def get_omdb_info(imdb_id):
    return rq.get(f'http://www.omdbapi.com/?i={imdb_id}&apikey={OMDB_API_KEY}&tomatoes=true').json()

def get_clean_list(items):
    return [x.strip() for x in items.split(',')]

def fetch_movie_info(chunk_size=10):
    with session_scope() as session:
        awarded_movie_ids = set([x[0] for x in session.query(MovieAward.movie_imdb_id).distinct().all()])
        fetched_movie_ids = set([x[0] for x in session.query(Movie.imdb_id).distinct().all()])
        ids_to_fetch = list(awarded_movie_ids - fetched_movie_ids)
        for i in range(0, len(ids_to_fetch), chunk_size):
            print(f"Fetched {i} / {len(ids_to_fetch)} movies")
            fetched_movies = []
            for imdb_id in ids_to_fetch[i:i+chunk_size]:
                try:
                    info = get_omdb_info(imdb_id)

                    imdb_rating = next(iter([rat['Value'] for rat in info.get('Ratings', []) if rat['Source'] == 'Internet Movie Database']))
                    if imdb_rating:
                        imdb_rating = float(imdb_rating.split('/')[0])
                    else:
                        print(f"\nWARNING: No rating for id={imdb_id}")

                    fetched_movies.append(Movie(
                        imdb_id=imdb_id,
                        title=info.get('Title'),
                        release_year=info.get('Year'),
                        directors=get_clean_list(info.get('Director')),
                        actors=get_clean_list(info.get('Actors')),
                        runtime=info.get('Runtime'),
                        genres=get_clean_list(info.get('Genre')),
                        countries=get_clean_list(info.get('Country')),
                        imdb_rating=imdb_rating,
                        imdb_votes=int(info.get('imdbVotes').replace(',', '')),
                        box_office=info.get('BoxOffice'),
                        rt_url=info.get('tomatoURL'),
                    ))
                except:
                    print(f"ERROR, problem with id={imdb_id}")
                    traceback.print_exc()

            session.bulk_save_objects(fetched_movies)
            session.commit()

fetch_movie_info()
            
"""
{'Title': 'Guardians of the Galaxy Vol. 2',
 'Year': '2017',
 'Rated': 'PG-13',
 'Released': '05 May 2017',
 'Runtime': '136 min',
 'Genre': 'Action, Adventure, Comedy, Sci-Fi',
 'Director': 'James Gunn',
 'Writer': 'James Gunn, Dan Abnett (based on the Marvel comics by), Andy Lanning (based on the Marvel comics by), Steve Englehart (Star-Lord created by), Steve Gan (Star-Lord created by), Jim Starlin (Gamora and Drax created by), Stan Lee (Groot created by), Larry Lieber (Groot created by), Jack Kirby (Groot created by), Bill Mantlo (Rocket Raccoon created by), Keith Giffen (Rocket Raccoon created by), Steve Gerber (Howard the Duck created by), Val Mayerik (Howard the Duck created by)',
 'Actors': 'Chris Pratt, Zoe Saldana, Dave Bautista, Vin Diesel',
 'Plot': "The Guardians must fight to keep their newfound family together as they unravel the mystery of Peter Quill's true parentage.",
 'Language': 'English',
 'Country': 'USA',
 'Awards': 'Nominated for 1 Oscar. Another 12 wins & 42 nominations.',
 'Poster': 'https://m.media-amazon.com/images/M/MV5BMTg2MzI1MTg3OF5BMl5BanBnXkFtZTgwNTU3NDA2MTI@._V1_SX300.jpg',
 'Ratings': [{'Source': 'Internet Movie Database', 'Value': '7.7/10'},
  {'Source': 'Rotten Tomatoes', 'Value': '83%'},
  {'Source': 'Metacritic', 'Value': '67/100'}],
 'Metascore': '67',
 'imdbRating': '7.7',
 'imdbVotes': '431,166',
 'imdbID': 'tt3896198',
 'Type': 'movie',
 'tomatoMeter': 'N/A',
 'tomatoImage': 'N/A',
 'tomatoRating': 'N/A',
 'tomatoReviews': 'N/A',
 'tomatoFresh': 'N/A',
 'tomatoRotten': 'N/A',
 'tomatoConsensus': 'N/A',
 'tomatoUserMeter': 'N/A',
 'tomatoUserRating': 'N/A',
 'tomatoUserReviews': 'N/A',
 'tomatoURL': 'http://www.rottentomatoes.com/m/guardians_of_the_galaxy_vol_2/',
 'DVD': '22 Aug 2017',
 'BoxOffice': '$389,804,217',
 'Production': 'Walt Disney Pictures',
 'Website': 'https://marvel.com/guardians',
 'Response': 'True'}"""

