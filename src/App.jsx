import React, { useState } from 'react';
import axios from 'axios';
import YouTube from 'react-youtube';

function App() {
  const [channelId, setChannelId] = useState('');
  const [searchPhrase, setSearchPhrase] = useState('');
  const [handle, setHandle] = useState('');
  const [foundChannelId, setFoundChannelId] = useState('');
  const [results, setResults] = useState([]);
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isFindingChannel, setIsFindingChannel] = useState(false);
  const [sortBy, setSortBy] = useState('date-desc');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [clickedResultIndex, setClickedResultIndex] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  const handleFindChannelId = async () => {
    if (!handle) {
      setErrorMessage('Please enter a YouTube handle');
      return;
    }
    setIsFindingChannel(true);
    setErrorMessage('');
    setChannelId(''); // Clear channel ID input when searching new handle
    try {
      const response = await axios.post('http://localhost:5001/find-channel-id', { handle });
      setFoundChannelId(response.data.channelId);
      setChannelId(response.data.channelId);
      console.log('Found channel ID:', response.data.channelId);
    } catch (error) {
      console.error('Find channel ID error:', error);
      setErrorMessage(`Error finding channel ID: ${error.response?.data?.error || error.message}. Please try again.`);
    }
    setIsFindingChannel(false);
  };

  const handleSearch = async () => {
    if (!channelId || !searchPhrase) {
      setErrorMessage('Please enter a YouTube Channel ID and Search Phrase');
      return;
    }
    setIsLoading(true);
    setErrorMessage('');
    try {
      const response = await axios.post('http://localhost:5001/search', {
        channelId,
        searchPhrase,
        startDate: startDate || undefined,
        endDate: endDate || undefined,
      });
      let sortedResults = response.data.results || [];
      if (sortBy === 'date-desc') {
        sortedResults.sort((a, b) => new Date(b.date) - new Date(a.date));
      } else if (sortBy === 'date-asc') {
        sortedResults.sort((a, b) => new Date(a.date) - new Date(b.date));
      } else if (sortBy === 'relevance') {
        sortedResults.sort((a, b) => b.matchCount - a.matchCount);
      }
      setResults(sortedResults);
      setClickedResultIndex(null);
      if (sortedResults.length === 0) {
        setErrorMessage('No results found. Try a different search phrase or filters.');
      }
    } catch (error) {
      console.error('Search error:', error);
      setErrorMessage(`Error fetching results: ${error.response?.data?.error || error.message}. Please try again.`);
      setResults([]);
    }
    setIsLoading(false);
  };

  const handleResultClick = (result, index) => {
    setSelectedVideo({ videoId: result.videoId, timestamp: result.timestamp });
    setClickedResultIndex(index);
  };

  const scrollToTop = () => {
    document.getElementById('search-results').scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-navy-blue text-navy-blue flex flex-col items-center p-6">
      <h1 className="text-4xl font-bold mb-4 text-youtube-red border-2 border-youtube-red px-4 py-2 rounded-lg">
        YouTube Transcript Search
      </h1>
      <div className="w-full max-w-6xl mb-8 bg-white rounded-lg shadow-lg p-4 sticky top-0 z-20 flex flex-wrap gap-4 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-navy-blue font-semibold">YouTube Handle</label>
          <input
            type="text"
            value={handle}
            onChange={(e) => setHandle(e.target.value)}
            className="w-full p-2 border rounded-lg text-black focus:outline-none focus:ring-2 focus:ring-gold"
            placeholder="e.g., @MrBeast"
          />
        </div>
        <div className="flex-1 min-w-[200px]">
          <label className="block text-navy-blue font-semibold">YouTube Channel ID</label>
          <input
            type="text"
            value={channelId}
            onChange={(e) => setChannelId(e.target.value)}
            className="w-full p-2 border rounded-lg text-black focus:outline-none focus:ring-2 focus:ring-gold"
            placeholder="e.g., UCX6OQ3DkcsbYNE6H8uQQuVA"
            required
          />
        </div>
        <div className="flex-1 min-w-[200px]">
          <label className="block text-navy-blue font-semibold">Search Phrase</label>
          <input
            type="text"
            value={searchPhrase}
            onChange={(e) => setSearchPhrase(e.target.value)}
            className="w-full p-2 border rounded-lg text-black focus:outline-none focus:ring-2 focus:ring-gold"
            placeholder="e.g., hello world"
            required
          />
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleFindChannelId}
            className="bg-gold text-navy-blue px-4 py-2 rounded-lg hover:bg-yellow-500 transition disabled:opacity-50"
            disabled={isFindingChannel}
          >
            {isFindingChannel ? 'Finding...' : 'Find Channel ID'}
          </button>
          <button
            onClick={handleSearch}
            className="bg-gold text-navy-blue px-4 py-2 rounded-lg hover:bg-yellow-500 transition disabled:opacity-50"
            disabled={isLoading}
          >
            {isLoading ? 'Searching...' : 'Search'}
          </button>
        </div>
        {foundChannelId && (
          <p className="w-full text-navy-blue text-sm">Channel ID: {foundChannelId}</p>
        )}
      </div>
      {(isFindingChannel || isLoading) && (
        <div className="w-full max-w-6xl mb-4 bg-navy-blue p-4 rounded-lg shadow-lg">
          <p className="text-white text-center mb-2">Searching...</p>
          <div className="w-full bg-gray-300 rounded-full h-2.5">
            <div className="bg-gold h-2.5 rounded-full animate-pulse" style={{ width: '100%' }}></div>
          </div>
        </div>
      )}
      {errorMessage && (
        <p className="w-full max-w-6xl text-red-500 mb-4">{errorMessage}</p>
      )}
      <div className="w-full max-w-6xl flex flex-col md:flex-row gap-6">
        <div className="md:w-1/2" id="search-results">
          <h2 className="text-2xl font-semibold mb-4 text-white">Search Results</h2>
          <div className="mb-4 bg-white rounded-lg shadow-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-semibold text-navy-blue">Filter Results</h3>
              <button
                onClick={handleSearch}
                className="bg-gold text-navy-blue px-3 py-1 rounded-lg hover:bg-yellow-500 transition disabled:opacity-50 text-xs w-32"
                disabled={isLoading}
              >
                {isLoading ? 'Applying...' : 'Apply Filters'}
              </button>
            </div>
            <div className="flex flex-wrap gap-2 items-start">
              <div className="flex-1 min-w-[100px]">
                <label className="block text-navy-blue text-xs font-semibold">Sort By</label>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="w-full p-1 border rounded-lg text-black focus:outline-none focus:ring-2 focus:ring-gold text-xs"
                >
                  <option value="date-desc">Date (Newest)</option>
                  <option value="date-asc">Date (Oldest)</option>
                  <option value="relevance">Relevance</option>
                </select>
              </div>
              <div className="flex flex-1 min-w-[140px] gap-1">
                <div className="flex-1">
                  <label className="block text-navy-blue text-xs font-semibold">From</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full p-1 border rounded-lg text-black focus:outline-none focus:ring-2 focus:ring-gold text-xs"
                  />
                </div>
                <div className="flex-1">
                  <label className="block text-navy-blue text-xs font-semibold">To</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full p-1 border rounded-lg text-black focus:outline-none focus:ring-2 focus:ring-gold text-xs"
                  />
                </div>
              </div>
            </div>
          </div>
          {results.length === 0 && !isLoading && !errorMessage && (
            <p className="text-white">No results found. Try a different search.</p>
          )}
          <ul className="space-y-4">
            {results.map((result, index) => (
              <li
                key={index}
                className={`p-4 bg-white rounded-lg shadow-lg cursor-pointer hover:bg-gray-50 transition ${
                  clickedResultIndex === index ? 'border-2 border-gold' : ''
                }`}
                onClick={() => handleResultClick(result, index)}
              >
                <div className="flex items-center justify-between">
                  <p className="font-semibold text-navy-blue text-lg">#{index + 1} {result.title}</p>
                  <a
                    href={`https://www.youtube.com/watch?v=${result.videoId}&t=${result.timestamp}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="bg-gold text-navy-blue px-3 py-1 rounded-lg hover:bg-yellow-500 transition text-sm w-32 text-center"
                  >
                    Watch on YouTube
                  </a>
                </div>
                <p className="text-navy-blue">Timestamp: {result.timestamp}s</p>
                <p className="text-navy-blue">Published: {new Date(result.date).toLocaleDateString()}</p>
                <p className="text-navy-blue">Matches: {result.matchCount}</p>
                <p className="text-navy-blue">Snippet: {result.snippet}</p>
              </li>
            ))}
          </ul>
        </div>
        <div className="md:w-1/2 sticky top-24 self-start">
          <h2 className="text-2xl font-semibold mb-4 text-white">Video Player</h2>
          {selectedVideo ? (
            <YouTube
              videoId={selectedVideo.videoId}
              opts={{
                width: '100%',
                height: '315',
                playerVars: { start: selectedVideo.timestamp },
              }}
              className="rounded-lg shadow-lg"
            />
          ) : (
            <p className="text-white">Select a result to play the video.</p>
          )}
        </div>
      </div>
      <button
        onClick={scrollToTop}
        className="fixed bottom-4 left-4 bg-gold text-navy-blue px-4 py-2 rounded-full hover:bg-yellow-500 transition z-30"
      >
        Back to Top
      </button>
    </div>
  );
}

export default App;