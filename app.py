import requests
import logging
import random
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from ytmusicapi import YTMusic

app = FastAPI()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# 1. The Search Brain (YouTube Music)
yt = YTMusic()

# 2. The Streaming Swarm (Piped Instances)
# We rotate through these to ensure we never get blocked.
PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://api.piped.video",
    "https://pipedapi.tokhmi.xyz",
    "https://piped-api.garudalinux.org",
    "https://api.piped.projectsegfau.lt",
    "https://pipedapi.wglab.net",
    "https://api.martinfc.eu",
    "https://pipedapi.drgns.space"
]

def search_youtube_music(query):
    """
    Uses YouTube Music's superior algorithm to find the EXACT match.
    """
    try:
        logger.info(f"Searching YTM for: {query}")
        # filter='songs' ensures we don't get fan-made videos or covers
        results = yt.search(query, filter="songs")
        
        if not results:
            # Fallback to general search if 'songs' filter misses (rare)
            results = yt.search(query)
            
        if not results: return None

        # The #1 result on YTM is always the most relevant (The Original)
        top_result = results[0]
        video_id = top_result.get('videoId')
        title = top_result.get('title')
        artists = ", ".join([a['name'] for a in top_result.get('artists', [])])
        
        logger.info(f"🏆 YTM Match: {title} by {artists} (ID: {video_id})")
        return video_id

    except Exception as e:
        logger.error(f"YTM Search Error: {e}")
        return None

def get_stream_from_piped(video_id):
    """
    Asks the Piped Swarm for a direct audio link for this ID.
    """
    # Randomize the list so we don't hammer one server
    instances = PIPED_INSTANCES.copy()
    random.shuffle(instances)

    for base_url in instances:
        try:
            # Piped Endpoint: /streams/{video_id}
            resp = requests.get(f"{base_url}/streams/{video_id}", timeout=3)
            
            if resp.status_code != 200: continue
            
            data = resp.json()
            audio_streams = data.get('audioStreams', [])
            
            if not audio_streams: continue
            
            # Look for m4a (best for Discord/FFmpeg)
            for stream in audio_streams:
                if stream.get('format') == 'm4a':
                    return stream['url']
            
            # Fallback to any audio
            return audio_streams[0]['url']

        except Exception:
            # Silently fail and try the next instance
            continue
    
    return None

@app.get("/")
def home():
    return {"status": "alive", "engine": "Hybrid (YTM + Piped)", "platform": "Koyeb"}

@app.get("/health")
def health_check():
    """Koyeb uses this to check if the app is running"""
    return {"status": "ok"}

@app.get("/stream")
def get_stream(q: str):
    if not q: raise HTTPException(status_code=400, detail="Query empty")
    
    # Clean query
    q = q.replace('"', '').strip()
    
    # 1. SEARCH (Accuracy Phase)
    video_id = search_youtube_music(q)
    
    if not video_id:
        raise HTTPException(status_code=404, detail="Song not found on YouTube Music")
        
    # 2. STREAM (Delivery Phase)
    stream_url = get_stream_from_piped(video_id)
    
    if stream_url:
        return RedirectResponse(url=stream_url, status_code=307)
    
    logger.error("All Piped instances failed to stream.")
    raise HTTPException(status_code=500, detail="Stream unavailable")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
