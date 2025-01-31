from flask import Flask, render_template_string, request, jsonify, render_template
import requests
import random
import os
import csv
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv

app = Flask(__name__)

# directories
project_folder = os.path.expanduser('~/')
load_dotenv(os.path.join(project_folder, '.env'))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
BLOG_DIR = os.path.join(BASE_DIR, "templates", "blog")
TRACK_FILE = os.path.join(DATA_DIR, "blog_posts.csv")

# api keys
api_key_tmdb = os.getenv('TMDB_API_KEY')
api_key_openai = os.getenv('OPENAI_API_KEY')



@app.route('/')
def index():
    csv_file = os.path.join(app.root_path, 'data', 'blog_posts.csv')
    recent_posts = []

    # Read the CSV to get titles and file names
    if os.path.exists(csv_file):
        with open(csv_file, mode='r') as file:
            reader = csv.DictReader(file)
            all_posts = list(reader)
            # Sort by file modification time (assuming files are named consistently)
            blog_folder = os.path.join(app.root_path, 'templates', 'blog')
            for post in all_posts:
                file_path = os.path.join(blog_folder, post['file_name'])
                if os.path.exists(file_path):
                    post['mod_time'] = os.path.getmtime(file_path)
                else:
                    post['mod_time'] = 0  # Default for missing files
            sorted_posts = sorted(all_posts, key=lambda x: x['mod_time'], reverse=True)
            recent_posts = sorted_posts[:5]

    return render_template('index.html', recent_posts=recent_posts)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


# Base URL for TMDb API
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_API_URL = 'https://api.themoviedb.org/3/search/tv'
TMDB_TV_DETAILS_URL = 'https://api.themoviedb.org/3/tv'

@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    query = request.args.get('query')
    if not query:
        return jsonify([])  # Return an empty list if no query is provided

    url = f"{TMDB_API_URL}?api_key={api_key_tmdb}&query={query}"
    response = requests.get(url)
    data = response.json()

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

    search_response = requests.get(
        TMDB_API_URL,
        params={
            'api_key': api_key_tmdb,
            'query': show_name,
            'include_adult': 'false'
        }
    )

    search_data = search_response.json()
    if 'results' not in search_data or len(search_data['results']) == 0:
        return jsonify({'error': 'No shows found for the given name.'}), 404

    show_id = search_data['results'][0]['id']

    details_response = requests.get(
        f"{TMDB_TV_DETAILS_URL}/{show_id}",
        params={'api_key': api_key_tmdb}
    )
    details_data = details_response.json()

    if 'episodes' not in details_data and 'seasons' not in details_data:
        return jsonify({'error': 'No episodes found for the selected show.'}), 404

    all_episodes = []
    for season in details_data.get('seasons', []):
        season_number = season['season_number']

        # Skip invalid seasons (NULL, N/A, or None)
        if not isinstance(season_number, int) or season_number <= 0:
            continue

        season_details_response = requests.get(
            f"{TMDB_TV_DETAILS_URL}/{show_id}/season/{season_number}",
            params={'api_key': api_key_tmdb}
        )
        season_details = season_details_response.json()
        all_episodes.extend(season_details.get('episodes', []))

    keyword_list = [k.strip().lower() for k in keywords.split(',') if k.strip()]
    filtered_episodes = [
        episode for episode in all_episodes
        if any(keyword in (episode['name'] + ' ' + episode.get('overview', '')).lower() for keyword in keyword_list)
    ] if keyword_list else all_episodes

    if not filtered_episodes:
        return jsonify({'error': 'No episodes matched the given keywords.'}), 404

    random_episode = random.choice(filtered_episodes)
    
    poster_image_url = None
    if 'still_path' in random_episode and random_episode['still_path']:
        poster_image_url = f"https://image.tmdb.org/t/p/w500{random_episode['still_path']}"

    return jsonify({
        'show': details_data['name'],
        'season': random_episode['season_number'],
        'episode': random_episode['episode_number'],
        'title': random_episode['name'],
        'synopsis': random_episode.get('overview', 'No synopsis available.'),
        'poster': poster_image_url,
        'episode_link': f"https://www.themoviedb.org/tv/{show_id}/season/{random_episode['season_number']}/episode/{random_episode['episode_number']}",
        'series_link': f"https://www.themoviedb.org/tv/{show_id}"
    })


# Ensure the CSV file exists
def ensure_csv_exists():
    if not os.path.exists(TRACK_FILE):
        with open(TRACK_FILE, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["series_title", "prompt_type", "date_generated"])

# Check if the series is already in the CSV
def is_series_in_csv(series_title, prompt_type):
    with open(TRACK_FILE, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["series_title"] == series_title and row["prompt_type"] == prompt_type:
                return True
    return False

# Add a new entry to the CSV
def add_to_csv(series_title, blog_title, prompt_type, image_url):
    with open(TRACK_FILE, "a", newline="", encoding="utf-8") as file:
    
        date_today = datetime.now().strftime("%Y-%m-%d")
        file_name = f"{series_title.replace(' ', '_')}_{date_today}.html"
        writer = csv.writer(file)
        writer.writerow([series_title, blog_title, prompt_type, image_url, file_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])


# Function 1: Fetch trending TV series and generate a blog post
def generate_blog_post(api_key_tmdb, api_key_openai, prompt_type="general"):
    ensure_csv_exists()

    # Fetch popular TV series from TMDb API
    tmdb_url = f"https://api.themoviedb.org/3/trending/tv/week?language=en-US&api_key={api_key_tmdb}"
    response = requests.get(tmdb_url)
    response.raise_for_status()
    trending_series = response.json()["results"]

    # Find a series not already in the CSV
    for series in trending_series:
        series_title = series["name"]

        if not is_series_in_csv(series_title, prompt_type):
            series_overview = series["overview"]
            image_path = series.get("poster_path", "")
            image_url = f"https://image.tmdb.org/t/p/w500{image_path}" if image_path else None


            # Ask ChatGPT to generate blog post content and title
            client = OpenAI(
                api_key=os.environ.get("OPENAI_API_KEY")
            )

            prompt = (
                f"Write a short blog post about the TV series '{series_title}'. "
                f"The post should be engaging and provide a brief overview of the show: {series_overview}. "
                f"Also, suggest a suitable blog post title for this series. Format the response in this way:\n\n"
                f"Title: [Insert blog title here]\n\n"
                f"Content:\n<h2>[Insert subtitle here]</h2><p>[Insert paragraphs here]</p>"
            )
            response =  client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
            )
            completion = response.choices[0].message.content.strip()

            # Extract title and content from the response
            title_line, content = completion.split("\n\n", 1)
            blog_title = title_line.replace("Title: ", "").strip()
            content = content.replace("Content:", "")

            # Add series to CSV
            add_to_csv(series_title, blog_title, prompt_type, image_url)

            return series_title, blog_title, content, image_url

    raise ValueError("No new trending series found for the given prompt type.")

def generate_blog_post_list(api_key_tmdb, api_key_openai, prompt_type="list"):
    ensure_csv_exists()

    # Fetch popular TV series from TMDb API
    tmdb_url = f"https://api.themoviedb.org/3/discover/tv?include_adult=false&language=en-US&page=1&sort_by=vote_average.desc&vote_count.gte=200&with_original_language=en&api_key={api_key_tmdb}"
    response = requests.get(tmdb_url)
    response.raise_for_status()
    trending_series = response.json()["results"]

    # Find a series not already in the CSV
    for series in trending_series:
        series_title = series["name"]

        if not is_series_in_csv(series_title, prompt_type):
            series_overview = series["overview"]
            image_path = series.get("poster_path", "")
            image_url = f"https://image.tmdb.org/t/p/w500{image_path}" if image_path else None


            # Ask ChatGPT to generate blog post content and title
            client = OpenAI(
                api_key=os.environ.get("OPENAI_API_KEY")
            )

            prompt = (
                f"Write a blog post about the top 10 episodes of the TV series '{series_title}'. If the series has less than 10 episodes, write about the two or three best episodes."
                f"Each episode should be described in around 200 words."
                f"Also, suggest a suitable blog post title. Format the response in this way:\n\n"
                f"Title: [Insert blog title here]\n\n"
                f"Content:\n<h2>[Episode title] (Season Number, Episode Number)</h2><p>[Insert paragraphs here]</p>"
            )
        
            response =  client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
            )
            completion = response.choices[0].message.content.strip()

            # Extract title and content from the response
            title_line, content = completion.split("\n\n", 1)
            blog_title = title_line.replace("Title: ", "").strip()
            content = content.replace("Content:", "")

            # Add series to CSV
            add_to_csv(series_title, blog_title, prompt_type, image_url)

            return series_title, blog_title, content, image_url

    raise ValueError("No new trending series found for the given prompt type.")

def save_blog_post(series_title, blog_title, blog_content, image_url):
    # Define the HTML structure
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>{blog_title}</title>
        {{% include 'head.html' %}}
    </head>
    <body>
        <main>
            <div id="content-wrapper">
                {{% include 'logo.html' %}}
                <div id="blog-body">
    <div id="back"><a href="/">< Back</a></div>      
    <h1>{blog_title}</h1>
    {'<img src="' + image_url + '" alt="' + series_title + ' poster" />' if image_url else ''}

                    {blog_content}
                </div>
            </div>
        {{% include 'footer.html' %}}
    </body>
    </html>
    """
    
    # Create the blog folder if it doesn't exist
    os.makedirs("blog", exist_ok=True)

    # Save the file with the current date
    date_today = datetime.now().strftime("%Y-%m-%d")

    filename = os.path.join(BLOG_DIR, f"{series_title.replace(' ', '_')}_{date_today}.html")

    with open(filename, "w", encoding="utf-8") as file:
        file.write(html_template)
    
    print(f"Blog post saved as {filename}")

    return jsonify({
        'status': 200
    })

@app.route('/create_blogpost', methods=['GET'])
def create_blogpost():
    prompt_type = request.args.get('prompt')

    if prompt_type == 'list':
        series_title, blog_title, blog_content, image_url = generate_blog_post_list(api_key_tmdb, api_key_openai)
    else:
        series_title, blog_title, blog_content, image_url = generate_blog_post(api_key_tmdb, api_key_openai)

    # Save blog post
    save_blog_post(series_title, blog_title, blog_content, image_url)

    # Redirect to the blog list page
    return redirect(url_for('list_blogs'))

@app.route('/blog')
def list_blogs():
    import os
    blog_dir = os.path.join(BASE_DIR, "templates", "blog")

    # Get all blog filenames
    blogs = []
    if os.path.exists(blog_dir):
        blogs = [f for f in os.listdir(blog_dir) if f.endswith('.html')]

    return render_template('blogs.html', blogs=blogs)

@app.route('/blog/<blog_name>')
def view_blog(blog_name):
    import os
    blog_path = os.path.join(BASE_DIR, "templates", 'blog', blog_name)

    # Read the content of the blog post
    if os.path.exists(blog_path):
        with open(blog_path, 'r') as file:
            content = file.read()
        return render_template_string(content)

    # If the file doesn't exist, show a 404 page
    return "Blog not found", 404

if __name__ == '__main__':
    app.run(debug=True)
