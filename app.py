from flask import Flask, request, jsonify, render_template
import requests
import random
import os
from dotenv import load_dotenv
project_folder = os.path.expanduser('~/')
load_dotenv(os.path.join(project_folder, '.env'))

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

# Replace with your TMDb API key
TMDB_API_KEY = os.getenv('TMDB_API_KEY')

# Base URL for TMDb API
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_API_URL = 'https://api.themoviedb.org/3/search/tv'
TMDB_TV_DETAILS_URL = 'https://api.themoviedb.org/3/tv'


@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    query = request.args.get('query')
    if not query:
        return jsonify([])  # Return an empty list if no query is provided

    # Construct the URL for the TMDb API with the query and your API key
    url = f"{TMDB_API_URL}?api_key={TMDB_API_KEY}&query={query}"

    # Make the GET request to TMDb
    response = requests.get(url)
    data = response.json()

    # Check if the response contains results
    if 'results' in data:
        tv_shows = [{'name': show['name']} for show in data['results']]
        return jsonify(tv_shows)
    else:
        return jsonify([])  # Return empty list if no results found

@app.route('/filter', methods=['GET'])
def filter_shows():
    show_name = request.args.get('showName')
    keywords = request.args.get('keywords', '')

    if not show_name:
        return jsonify({'error': 'Please provide a show name.'}), 400

    # Search for the show using TMDb API
    search_response = requests.get(
        TMDB_API_URL,
        params={
            'api_key': TMDB_API_KEY,
            'query': show_name,
            'include_adult': 'false'
        }
    )

    search_data = search_response.json()
    if 'results' not in search_data or len(search_data['results']) == 0:
        return jsonify({'error': 'No shows found for the given name.'}), 404

    # Extract the most relevant show ID
    show_id = search_data['results'][0]['id']

    # Fetch details of the selected show
    details_response = requests.get(
        f"{TMDB_TV_DETAILS_URL}/{show_id}",
        params={'api_key': TMDB_API_KEY}
    )
    details_data = details_response.json()

    if 'episodes' not in details_data and 'seasons' not in details_data:
        return jsonify({'error': 'No episodes found for the selected show.'}), 404

    # Extract episodes
    all_episodes = []
    for season in details_data.get('seasons', []):
        season_number = season['season_number']
        season_details_response = requests.get(
            f"{TMDB_TV_DETAILS_URL}/{show_id}/season/{season_number}",
            params={'api_key': TMDB_API_KEY}
        )
        season_details = season_details_response.json()
        all_episodes.extend(season_details.get('episodes', []))

    # Filter episodes by keywords
    keyword_list = [k.strip().lower() for k in keywords.split(',') if k.strip()]
    filtered_episodes = [
        episode for episode in all_episodes
        if any(keyword in (episode['name'] + ' ' + episode.get('overview', '')).lower() for keyword in keyword_list)
    ] if keyword_list else all_episodes

    if not filtered_episodes:
        return jsonify({'error': 'No episodes matched the given keywords.'}), 404

    # Select a random episode
    random_episode = random.choice(filtered_episodes)

    # Get the poster image for the episode, if available
    poster_image_url = None
    if 'still_path' in random_episode:
        poster_image_url = f"https://image.tmdb.org/t/p/w500{random_episode['still_path']}"

    return jsonify({
        'show': details_data['name'],
        'season': random_episode['season_number'],
        'episode': random_episode['episode_number'],
        'title': random_episode['name'],
        'synopsis': random_episode.get('overview', 'No synopsis available.'),
        'poster': poster_image_url  # Include the poster URL if available
    })

if __name__ == '__main__':
    app.run(debug=True)