import re
import requests as rq 
from bs4 import BeautifulSoup
import traceback

from storage import session_scope, Movie, MovieAward
from constants import OMDB_API_KEY, WIKI_BASE


def get_omdb_info(imdb_id):
    return rq.get(f'http://www.omdbapi.com/?i={imdb_id}&apikey={OMDB_API_KEY}&tomatoes=true').json()

def get_imdb_id_from_wiki(wiki_url):
    soup = BeautifulSoup(rq.get(WIKI_BASE + wiki_url).text, 'lxml')
    ext_links = soup.find('span', {'class': 'mw-headline', 'id': 'External_links'})
    link = ext_links.findNext('a')
    while link:
        match = re.search('imdb.com/title/([\w]+)', link.get('href', ''))
        if match:
            return match.group(1)
        link = link.findNext('a')

    raise Exception(f"No urls found for {wiki_url}")

def get_clean_list(items):
    if items == 'N/A':
        return None
    return [x.strip() for x in items.split(',')]

def fetch_movie_info(chunk_size=10):
    with session_scope() as session:
        current_wiki_urls = set([x.movie_wiki_url for x in session.query(Movie.movie_wiki_url).all()])
        movie_wiki_urls = set([x[0] for x in session.query(MovieAward.movie_wiki_url).distinct().all()])
        urls_to_fetch = list(movie_wiki_urls - current_wiki_urls)
        for i in range(0, len(urls_to_fetch), chunk_size):
            print(f"Fetched {i} / {len(urls_to_fetch)} movies")
            fetched_movies = []
            for wiki_url in urls_to_fetch[i:i+chunk_size]:
                try:
                    imdb_id = get_imdb_id_from_wiki(wiki_url)
                    print(f"{wiki_url}  |  {imdb_id}")
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
                        movie_wiki_url=wiki_url,
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
                    print(f"\n\n\nERROR, problem with url={wiki_url}")
                    print(info)
                    traceback.print_exc()
                    print("\n\n\n")

            session.bulk_save_objects(fetched_movies)
            session.commit()

fetch_movie_info()
