import requests
import logging
import random
import time
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

# 2. The Mega Swarm (Fresh List - Feb 2026)
# We mix official, community, and Linux distro instances for maximum survival.
PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",          # Official (Global)
    "https://pipedapi.tokhmi.xyz",           # US
    "https://pipedapi.moomoo.me",            # UK
    "https://pipedapi.syncpundit.io",        # India/US/Japan (Fast for Asia)
    "https://api-piped.mha.fi",              # Finland
    "https://piped-api.garudalinux.org",     # Garuda Linux (Reliable)
    "https://pipedapi.rivo.lol",             # Chile
    "https://pipedapi.leptons.xyz",          # Austria
    "https://piped-api.lunar.icu",           # Germany
    "https://ytapi.dc09.ru",                 # Russia
    "https://pipedapi.r4fo.com",             # Germany
    "https://api.piped.privacy.com.de",      # Germany
    "https://pipedapi.smnz.de",              # Germany
    "https://api.piped.projectsegfau.lt",    # Lithuania
    "https://pipedapi.wglab.net",            # Global
    "https://api.martinfc.eu",               # Europe
    "https://pipedapi.drgns.space"           # US
]

def search_youtube_music(query):
    try:
        logger.info(f"Searching YTM for: {query}")
        # Search for songs to ensure we get the original, not a cover video
        results = yt.search(query, filter="songs")
        
        if not results:
            results = yt.search(query)
            
        if not results: return None

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
    Tries to fetch a stream from the Piped Swarm.
    Includes retry logic and timeouts.
    """
    instances = PIPED_INSTANCES.copy()
    random.shuffle(instances) # Randomize to load-balance

    for base_url in instances:
        try:
            # logger.info(f"Trying: {base_url}")
            url = f"{base_url}/streams/{video_id}"
            
            # Short timeout (2s) so we don't hang if a server is slow
            resp = requests.get(url, timeout=2.5)
            
            if resp.status_code != 200: continue
            
            data = resp.json()
            audio_streams = data.get('audioStreams', [])
            
            if not audio_streams: continue
            
            # 1. Prefer m4a (Best for Discord)
            for stream in audio_streams:
                if stream.get('format') == 'm4a':
                    return stream['url']
            
            # 2. Fallback to any audio
            return audio_streams[0]['url']

        except Exception:
            continue
    
    return None

@app.get("/")
def home():
    return {"status": "alive", "engine": "Hybrid Mega-Swarm V2", "platform": "Koyeb"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/stream")
def get_stream(q: str):
    if not q: raise HTTPException(status_code=400, detail="Query empty")
    
    # Clean query (Remove quotes)
    q = q.replace('"', '').strip()
    
    # 1. SEARCH
    video_id = search_youtube_music(q)
    
    if not video_id:
        raise HTTPException(status_code=404, detail="Song not found on YouTube Music")
        
    # 2. STREAM
    stream_url = get_stream_from_piped(video_id)
    
    if stream_url:
        return RedirectResponse(url=stream_url, status_code=307)
    
    logger.error("Mega Swarm exhausted. All 17 instances failed.")
    raise HTTPException(status_code=500, detail="Stream unavailable - Swarm Busy")

if __name__ == "__main__":
    import uvicorn
    # Correct Port for Koyeb
    uvicorn.run(app, host="0.0.0.0", port=8000)
