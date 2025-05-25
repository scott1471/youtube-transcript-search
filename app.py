import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import psycopg2
import re
from urllib.parse import urlparse

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:5173", "https://your-frontend.onrender.com"]}})  # Update with frontend URL

# YouTube API setup
youtube_api_key = os.getenv('YOUTUBE_API_KEY')
if not youtube_api_key:
    raise ValueError("YOUTUBE_API_KEY environment variable not set")
youtube = build('youtube', 'v3', developerKey=youtube_api_key)

# Database setup
def get_db_connection():
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        parsed_url = urlparse(database_url)
        conn = psycopg2.connect(
            database=parsed_url.path[1:],
            user=parsed_url.username,
            password=parsed_url.password,
            host=parsed_url.hostname,
            port=parsed_url.port
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

def init_db():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS channels
                     (channel_id TEXT PRIMARY KEY, handle TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS transcripts
                     (id SERIAL PRIMARY KEY,
                      video_id TEXT NOT NULL UNIQUE,
                      channel_id TEXT,
                      title TEXT,
                      date TEXT NOT NULL,
                      transcript TEXT)''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database initialization failed: {e}")
        raise

try:
    init_db()
except Exception as e:
    print(f"Failed to initialize database: {e}")
    raise

@app.route('/find-channel-id', methods=['POST'])
def find_channel_id():
    data = request.get_json()
    handle = data.get('handle')
    if not handle:
        return jsonify({'error': 'Handle is required'}), 400

    try:
        response = youtube.channels().list(
            part='id',
            forHandle=handle
        ).execute()

        if 'items' in response and len(response['items']) > 0:
            channel_id = response['items'][0]['id']
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('INSERT INTO channels (channel_id, handle) VALUES (%s, %s) ON CONFLICT (channel_id) UPDATE SET handle = EXCLUDED.handle',
                      (channel_id, handle))
            conn.commit()
            conn.close()
            return jsonify({'channelId': channel_id})
        else:
            return jsonify({'error': 'Channel not found'}), 404
    except HttpError as e:
        return jsonify({'error': f'YouTube API error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    channel_id = data.get('channelId')
    search_phrase = data.get('searchPhrase')
    start_date = data.get('startDate')
    end_date = data.get('endDate')

    if not channel_id or not search_phrase:
        return jsonify({'error': 'Channel ID and search phrase are required'}), 400

    try:
        # Fetch videos for the channel
        videos = []
        next_page_token = None
        while True:
            response = youtube.search().list(
                part='id,snippet',
                channelId=channel_id,
                maxResults=50,
                pageToken=next_page_token,
                type='video',
                publishedAfter=start_date + 'T00:00:00Z' if start_date else None,
                publishedBefore=end_date + 'T23:59:59Z' if end_date else None
            ).execute()

            for item in response.get('items', []):
                videos.append({
                    'videoId': item['id']['videoId'],
                    'title': item['snippet']['title'],
                    'date': item['snippet']['publishedAt']
                })
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break

        # Search transcripts
        results = []
        conn = get_db_connection()
        c = conn.cursor()
        for video in videos:
            video_id = video['videoId']
            c.execute('SELECT transcript FROM transcripts WHERE video_id = %s', (video_id,))
            row = c.fetchone()
            if row:
                transcript = row[0]
                matches = list(re.finditer(search_phrase, transcript, re.IGNORECASE))
                if matches:
                    for match in matches:
                        start = max(0, match.start() - 50)
                        snippet = transcript[start:start + 100]
                        results.append({
                            'videoId': video_id,
                            'title': video['title'],
                            'date': video['date'],
                            'timestamp': 0,  # Simplified; real app would parse transcript timestamps
                            'snippet': snippet,
                            'matchCount': len(matches)
                        })
        conn.close()
        return jsonify({'results': results})
    except HttpError as e:
        return jsonify({'error': f'YouTube API error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    print("Starting Flask app...")
    print("Initializing YouTube API client...")
    print("Initializing database...")
    app.run(host='0.0.0.0', port=5001, debug=False)
#API_KEY = "AIzaSyCLcWj0LcrYPDvDyK05Pk1D67eqU2nivy8"

