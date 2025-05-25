import sqlite3

conn = sqlite3.connect('transcripts.db')
c = conn.cursor()
c.execute('SELECT video_id, channel_id, title, date, length(transcript) FROM transcripts')
rows = c.fetchall()
print(f"Found {len(rows)} transcripts:")
for row in rows:
    print(f"Video ID: {row[0]}, Channel ID: {row[1]}, Title: {row[2]}, Date: {row[3]}, Transcript Length: {row[4]}")
conn.close()