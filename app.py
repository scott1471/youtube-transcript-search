import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import sqlite3
import re
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:5173", "https://your-frontend-domain.onrender.com"]}})  # Update with deployed frontend URL

# YouTube API setup
youtube_api_key = os.getenv('AIzaSyCLcWj0LcrYPDvDyK05Pk1D67eqU2nivy8')
youtube = build('youtube', 'v3', developerKey=youtube_api_key)

# Database setup
db_path = os.getenv('DB_PATH', 'transcripts.db')
def init_db():
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS channels
                     (channel_id TEXT PRIMARY KEY, handle TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS transcripts
                     (video_id TEXT PRIMARY_KEY, channel_id TEXT, title TEXT, date TEXT, transcript TEXT)''')
        conn.commit()

init_db()

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
            with sqlite3.connect(db_path) as conn:
                c = conn.cursor()
                c.execute('INSERT OR REPLACE INTO channels (channel_id, handle) VALUES (?, ?)',
                         (channel_id, handle))
                conn.commit()
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
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            for video in videos:
                video_id = video['videoId']
                c.execute('SELECT transcript FROM transcripts WHERE video_id = ?', (video_id,))
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

        return jsonify({'results': results})
    except HttpError as e:
        return jsonify({'error': f'YouTube API error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    print("Starting Flask app...")
    print("Initializing YouTube API client...")
    print("Initializing database...")
    print("Running Flask server on port 5001...")
    app.run(host='0.0.0.0', port=5001, debug=False)
#API_KEY = "AIzaSyCLcWj0LcrYPDvDyK05Pk1D67eqU2nivy8"

