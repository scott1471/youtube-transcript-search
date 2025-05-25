import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import psycopg2
import re
from urllib.parse import urlparse
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

app = Flask(__name__)
CORS(app, resources={r"/*": {
    "origins": ["http://localhost:5173", "https://youtube-transcript-search-1.onrender.com"],
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type"],
    "expose_headers": ["Access-Control-Allow-Origin"],
    "support_credentials": False
}}, send_wildcard=False)

# YouTube API setup
youtube_api_key = os.getenv('YOUTUBE_API_KEY')
if not youtube_api_key:
    app.logger.error("YOUTUBE_API_KEY environment variable not set")
    raise ValueError("YOUTUBE_API_KEY not set")
youtube = build('youtube', 'v3', developerKey=youtube_api_key)

# Database setup
def get_db_connection():
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            app.logger.error("DATABASE_URL environment variable not set")
            raise ValueError("DATABASE_URL not set")
        parsed_url = urlparse(database_url)
        conn = psycopg2.connect(
            database=parsed_url.path[1:],
            user=parsed_url.username,
            password=parsed_url.password,
            host=parsed_url.hostname,
            port=parsed_url.port
        )
        conn.set_session(autocommit=False)  # Explicit transaction control
        app.logger.info("Database connection established")
        return conn
    except Exception as e:
        app.logger.error(f"Database connection error: {e}")
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
                      date TEXT,
                      transcript TEXT)''')
        conn.commit()
        conn.close()
        app.logger.info("Database initialized successfully")
    except Exception as e:
        app.logger.error(f"Database initialization failed: {e}")
        raise

try:
    init_db()
except Exception as e:
    app.logger.error(f"Failed to initialize database: {e}")
    raise

def fetch_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = None
        for t in transcript_list:
            if t.language_code in ['en', 'en-US', 'en-GB']:
                transcript = t
                break
        if not transcript:
            transcript = transcript_list.find_generated_transcript(['en', 'en-US', 'en-GB'])
        text = ' '.join([entry['text'] for entry in transcript.fetch()])
        app.logger.info(f"Fetched transcript for video {video_id}, type={'generated' if transcript.is_generated else 'manual'}, length={len(text)}")
        return text
    except (NoTranscriptFound, TranscriptsDisabled) as e:
        app.logger.warning(f"No transcript available for video {video_id}: {e}")
        return None
    except Exception as e:
        app.logger.error(f"Error fetching transcript for {video_id}: {e}")
        return None

@app.route('/find-channel-id', methods=['POST', 'OPTIONS'])
def find_channel_id():
    if request.method == 'OPTIONS':
        app.logger.info("Received OPTIONS request for /find-channel-id")
        return jsonify({}), 200
    try:
        data = request.get_json()
        handle = data.get('handle')
        app.logger.info(f"find-channel-id request: handle={handle}")
        if not handle:
            app.logger.warning("Handle is required")
            return jsonify({'error': 'Handle is required'}), 400

        response = youtube.search().list(
            part='snippet',
            q=handle,
            type='channel',
            maxResults=1
        ).execute()

        if 'items' in response and len(response['items']) > 0:
            channel_id = response['items'][0]['snippet']['channelId']
            try:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute('''INSERT INTO channels (channel_id, handle)
                             VALUES (%s, %s)
                             ON CONFLICT (channel_id)
                             DO UPDATE SET handle = %s''',
                          (channel_id, handle, handle))
                conn.commit()
                app.logger.info(f"Inserted channel: {channel_id}, handle={handle}")
                conn.close()
            except Exception as e:
                app.logger.error(f"Database error inserting channel {channel_id}: {e}")
                conn.rollback()
                conn.close()
                raise
            return jsonify({'channelId': channel_id})
        else:
            app.logger.warning(f"Channel not found for handle={handle}")
            return jsonify({'error': 'Channel not found'}), 404
    except HttpError as e:
        app.logger.error(f"YouTube API error: {e}")
        return jsonify({'error': f'YouTube API error: {str(e)}'}), 500
    except Exception as e:
        app.logger.error(f"Server error in find-channel-id: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/search', methods=['POST', 'OPTIONS'])
def search():
    if request.method == 'OPTIONS':
        app.logger.info("Received OPTIONS request for /search")
        return jsonify({}), 200
    try:
        data = request.get_json()
        channel_id = data.get('channelId')
        search_phrase = data.get('searchPhrase')
        start_date = data.get('startDate')
        end_date = data.get('endDate')

        app.logger.info(f"Search request: channel_id={channel_id}, phrase={search_phrase}, start_date={start_date}, end_date={end_date}")

        if not channel_id or not search_phrase:
            app.logger.warning("Channel ID and search phrase are required")
            return jsonify({'error': 'Channel ID and search phrase are required'}), 400

        # Fetch videos for the channel
        videos = []
        try:
            response = youtube.search().list(
                part='id,snippet',
                channelId=channel_id,
                maxResults=20,
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
            app.logger.info(f"Fetched {len(videos)} videos for channel {channel_id}: {[v['videoId'] for v in videos]}")
        except HttpError as e:
            app.logger.error(f"YouTube API error fetching videos: {e}")
            return jsonify({'error': f'YouTube API error: {str(e)}'}), 500

        # Check and fetch transcripts
        conn = None
        try:
            conn = get_db_connection()
            c = conn.cursor()
            for video in videos:
                video_id = video['videoId']
                c.execute('SELECT transcript FROM transcripts WHERE video_id = %s', (video_id,))
                row = c.fetchone()
                if not row:
                    transcript = fetch_transcript(video_id)
                    if transcript:
                        try:
                            c.execute('''INSERT INTO transcripts (video_id, channel_id, title, date, transcript)
                                         VALUES (%s, %s, %s, %s, %s)
                                         ON CONFLICT (video_id) DO NOTHING''',
                                      (video_id, channel_id, video['title'], video['date'], transcript))
                            conn.commit()
                            app.logger.info(f"Added transcript for video {video_id}: {video['title']}")
                        except Exception as e:
                            app.logger.error(f"Error inserting transcript for video {video_id}: {e}")
                            conn.rollback()

            # Search transcripts
            results = []
            for video in videos:
                video_id = video['videoId']
                c.execute('SELECT transcript FROM transcripts WHERE video_id = %s', (video_id,))
                row = c.fetchone()
                if row and row[0]:
                    transcript = row[0]
                    matches = list(re.finditer(re.escape(search_phrase), transcript, re.IGNORECASE))
                    if matches:
                        for match in matches:
                            start = match.start()
                            snippet = transcript[max(0, start - 50):start + 50 + len(search_phrase)]
                            results.append({
                                'videoId': video_id,
                                'title': video['title'],
                                'date': video['date'],
                                'timestamp': 0,
                                'snippet': snippet,
                                'matchCount': len(matches)
                            })
                    app.logger.info(f"Checked video {video_id}: {len(matches)} matches for phrase '{search_phrase}'")
            app.logger.info(f"Total {len(results)} search results for channel {channel_id}")
            conn.commit()
            return jsonify({'results': results})
        except Exception as e:
            app.logger.error(f"Database or search error: {e}")
            if conn:
                conn.rollback()
            return jsonify({'error': f'Server error: {str(e)}'}), 500
        finally:
            if conn:
                conn.close()
                app.logger.info("Database connection closed")
    except Exception as e:
        app.logger.error(f"Unexpected server error in search: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    app.logger.info("Starting Flask app...")
    app.logger.info("Initializing YouTube API client...")
    app.logger.info("Initializing database...")
    app.run(host='0.0.0.0', port=5001, debug=False)
#API_KEY = "AIzaSyCLcWj0LcrYPDvDyK05Pk1D67eqU2nivy8"

