
from googleapiclient.discovery import build
import traceback

try:
    YOUTUBE_API_KEY = 'AIzaSyCLcWj0LcrYPDvDyK05Pk1D67eqU2nivy8'  # Replace with your API key
    print("Initializing YouTube API client...")
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    print("Sending request to YouTube API...")
    request = youtube.channels().list(part='snippet', id='UCX6OQ3DkcsbYNE6H8uQQuVA')
    response = request.execute()
    print("Response received:")
    print(response)
except Exception as e:
    print("Error occurred:")
    print(str(e))
    print(traceback.format_exc())