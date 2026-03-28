#!/usr/bin/env python3
"""
YouTube Transcript Extractor - Multi-layer fallback chain.
Designed for Claude.ai container environment where cloud IPs are blocked by YouTube.

Fallback chain:
  Layer 1: Node.js youtube-transcript npm + undici proxy (structured, with timestamps)
  Layer 2: curl YouTube watch page -> parse captionTracks -> fetch timedtext XML
  Layer 3: web_search + web_fetch for third-party transcript sites (handled by Claude, not this script)
  Layer 4: User pastes transcript (handled by Claude, not this script)

Usage: python3 yt-transcript-extract.py VIDEO_ID [--json]
"""
import subprocess, re, json, html as htmlmod, sys, os, time

def extract_via_node(video_id):
    """Layer 1: Node.js youtube-transcript + undici ProxyAgent"""
    script = f"""
import {{ ProxyAgent, fetch as undiciFetch }} from 'undici';
import {{ YoutubeTranscript }} from './node_modules/youtube-transcript/dist/youtube-transcript.esm.js';

const proxyUrl = process.env.HTTPS_PROXY;
const dispatcher = new ProxyAgent({{
  uri: proxyUrl,
  requestTls: {{ rejectUnauthorized: false }}
}});
const proxyFetch = (url, opts = {{}}) => undiciFetch(url, {{ ...opts, dispatcher }});

try {{
  const t = await YoutubeTranscript.fetchTranscript('{video_id}', {{ fetch: proxyFetch }});
  console.log(JSON.stringify({{
    success: true,
    method: 'node-youtube-transcript',
    segments: t.map(s => ({{ offset: s.offset, duration: s.duration, text: s.text }})),
    totalWords: t.map(s => s.text).join(' ').split(' ').length
  }}));
}} catch(e) {{
  console.log(JSON.stringify({{ success: false, error: e.constructor.name, message: e.message }}));
}}
"""
    script_path = '/home/claude/yt-extract-layer1.mjs'
    with open(script_path, 'w') as f:
        f.write(script)
    
    try:
        result = subprocess.run(
            ['node', script_path],
            capture_output=True, text=True, timeout=30,
            cwd='/home/claude'
        )
        if result.stdout.strip():
            data = json.loads(result.stdout.strip())
            if data.get('success'):
                return data
            else:
                print(f"  Layer 1 failed: {data.get('error')}: {data.get('message', '')[:100]}", file=sys.stderr)
        else:
            print(f"  Layer 1: no output. stderr: {result.stderr[:200]}", file=sys.stderr)
    except subprocess.TimeoutExpired:
        print("  Layer 1: timeout", file=sys.stderr)
    except Exception as e:
        print(f"  Layer 1: {e}", file=sys.stderr)
    return None


def extract_via_curl(video_id):
    """Layer 2: curl watch page -> parse captionTracks -> fetch timedtext XML"""
    # Step 1: Fetch watch page
    try:
        result = subprocess.run(
            ["curl", "-sL", "--insecure", "--max-time", "15",
             f"https://www.youtube.com/watch?v={video_id}",
             "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
             "-H", "Accept-Language: en-US,en;q=0.9",
             "-b", "CONSENT=YES+1"],
            capture_output=True, text=True, timeout=20
        )
        page = result.stdout
    except Exception as e:
        print(f"  Layer 2: curl watch page failed: {e}", file=sys.stderr)
        return None
    
    if len(page) < 10000:
        print(f"  Layer 2: page too small ({len(page)} bytes), likely blocked", file=sys.stderr)
        return None
    
    if 'g-recaptcha' in page or 'captcha' in page.lower()[:5000]:
        print("  Layer 2: CAPTCHA detected", file=sys.stderr)
        return None
    
    # Step 2: Extract captionTracks
    match = re.search(r'"captionTracks":(\[.*?\])', page)
    if not match:
        if '"playabilityStatus"' not in page:
            print("  Layer 2: no playability status (video unavailable?)", file=sys.stderr)
        else:
            print("  Layer 2: no captionTracks (captions disabled or unavailable)", file=sys.stderr)
        return None
    
    try:
        tracks_json = match.group(1).replace('\\u0026', '&')
        tracks = json.loads(tracks_json)
    except json.JSONDecodeError as e:
        print(f"  Layer 2: JSON parse error: {e}", file=sys.stderr)
        return None
    
    if not tracks:
        print("  Layer 2: empty captionTracks", file=sys.stderr)
        return None
    
    # Prefer English, then first available
    en_track = next((t for t in tracks if t.get('languageCode', '').startswith('en')), None)
    track = en_track or tracks[0]
    base_url = track['baseUrl'].replace('\\u0026', '&')
    lang = track.get('languageCode', 'unknown')
    
    # Step 3: Fetch timedtext XML
    try:
        result2 = subprocess.run(
            ["curl", "-sL", "--insecure", "--max-time", "10",
             base_url,
             "-H", "User-Agent: Mozilla/5.0"],
            capture_output=True, text=True, timeout=15
        )
        xml_data = result2.stdout
    except Exception as e:
        print(f"  Layer 2: curl timedtext failed: {e}", file=sys.stderr)
        return None
    
    if '<html' in xml_data[:100].lower() or 'sorry' in xml_data[:500].lower():
        print("  Layer 2: timedtext blocked (got HTML error page)", file=sys.stderr)
        return None
    
    # Step 4: Parse XML - try both formats
    segments = []
    
    # Format A: <text start="0.24" dur="4.08">text</text>
    for m in re.finditer(r'<text start="([^"]*)" dur="([^"]*)">([^<]*)</text>', xml_data):
        text = htmlmod.unescape(m.group(3)).strip()
        if text:
            segments.append({
                'offset': float(m.group(1)) * 1000,
                'duration': float(m.group(2)) * 1000,
                'text': text
            })
    
    # Format B: <p t="1234" d="5678"><s>word1</s><s>word2</s></p>
    if not segments:
        for m in re.finditer(r'<p\s+t="(\d+)"\s+d="(\d+)"[^>]*>(.*?)</p>', xml_data, re.DOTALL):
            inner = m.group(3)
            words = re.findall(r'<s[^>]*>([^<]*)</s>', inner)
            text = ''.join(words) if words else re.sub(r'<[^>]+>', '', inner)
            text = htmlmod.unescape(text).strip()
            if text:
                segments.append({
                    'offset': int(m.group(1)),
                    'duration': int(m.group(2)),
                    'text': text
                })
    
    if not segments:
        print(f"  Layer 2: no segments parsed from XML ({len(xml_data)} bytes)", file=sys.stderr)
        return None
    
    all_text = ' '.join(s['text'] for s in segments)
    return {
        'success': True,
        'method': 'curl-captionTracks',
        'language': lang,
        'segments': segments,
        'totalWords': len(all_text.split())
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 yt-transcript-extract.py VIDEO_ID [--json]", file=sys.stderr)
        sys.exit(1)
    
    video_id = sys.argv[1]
    output_json = '--json' in sys.argv
    
    print(f"Extracting transcript for: {video_id}", file=sys.stderr)
    
    # Layer 1: Node.js
    print("Trying Layer 1 (Node.js youtube-transcript + undici proxy)...", file=sys.stderr)
    result = extract_via_node(video_id)
    
    if not result:
        # Layer 2: curl-based
        print("Trying Layer 2 (curl watch page + captionTracks)...", file=sys.stderr)
        result = extract_via_curl(video_id)
    
    if not result:
        print("All automated layers failed. Fallback to web_search or user paste.", file=sys.stderr)
        if output_json:
            print(json.dumps({'success': False, 'error': 'all_layers_failed'}))
        sys.exit(1)
    
    if output_json:
        print(json.dumps(result))
    else:
        # Output as clean text
        for s in result['segments']:
            print(s['text'])
    
    print(f"\nExtraction method: {result['method']}", file=sys.stderr)
    print(f"Segments: {len(result['segments'])}", file=sys.stderr)
    print(f"Total words: {result['totalWords']}", file=sys.stderr)


if __name__ == '__main__':
    main()