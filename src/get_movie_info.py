import requests as rq 
import traceback

from storage import session_scope, Movie, MovieAward
from constants import OMDB_API_KEY


def get_omdb_info(imdb_id):
    return rq.get(f'http://www.omdbapi.com/?i={imdb_id}&apikey={OMDB_API_KEY}&tomatoes=true').json()

def get_clean_list(items):
    if items == 'N/A':
        return None
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
                    ratings = info.get('Ratings')
                    imdb_rating = None
                    if ratings:
                        imdb_rating = next(iter([rat['Value'] for rat in ratings if rat['Source'] == 'Internet Movie Database']))
                        if imdb_rating:
                            imdb_rating = float(imdb_rating.split('/')[0])
                    if not imdb_rating:
                        print(f"\nWARNING: No rating for id={imdb_id}")

                    if info.get('imdbVotes') == 'N/A':
                        imdb_votes = None
                    else:
                        imdb_votes = int(info.get('imdbVotes').replace(',', ''))

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
                        imdb_votes=imdb_votes,
                        box_office=info.get('BoxOffice'),
                        rt_url=info.get('tomatoURL'),
                    ))
                except:
                    print(f"\n\n\nERROR, problem with id={imdb_id}")
                    print(info)
                    traceback.print_exc()
                    print("\n\n\n")

            session.bulk_save_objects(fetched_movies)
            session.commit()

fetch_movie_info()
