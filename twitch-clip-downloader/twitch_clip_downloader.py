"""
Twitch Clip Downloader - A tool to download clips from Twitch streamers without using the official API.

This script uses publicly available information and yt-dlp to download clips from Twitch streamers,
organize them locally, and prepare them for manual upload to various platforms.
"""

import argparse
import os
import sys
import json
import re
import subprocess
import datetime
import requests
from bs4 import BeautifulSoup
import time
import random
from pathlib import Path

def setup_argparse():
    """Set up command line argument parsing."""
    parser = argparse.ArgumentParser(description='Download Twitch clips without using official APIs.')
    
    parser.add_argument('streamer', type=str, help='Twitch streamer username')
    parser.add_argument('--hours', type=int, default=24, help='Hours to look back for clips (default: 24)')
    parser.add_argument('--limit', type=int, default=5, help='Maximum number of clips to process (default: 5)')
    parser.add_argument('--output-dir', type=str, default='downloads', help='Directory to save clips (default: downloads)')
    parser.add_argument('--min-views', type=int, default=0, help='Minimum views for clips (default: 0)')
    parser.add_argument('--metadata', action='store_true', help='Generate metadata files for uploads')
    parser.add_argument('--format', type=str, choices=['mp4', 'mov'], default='mp4', help='Output format (default: mp4)')
    
    return parser.parse_args()

def check_dependencies():
    """Check if necessary dependencies are installed."""
    try:
        # Check for yt-dlp
        subprocess.run(['yt-dlp', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        print("✓ yt-dlp is installed")
    except (subprocess.SubprocessError, FileNotFoundError):
        print("✗ yt-dlp is not installed. Please install it with 'pip install yt-dlp'")
        sys.exit(1)
    
    try:
        # Check for ffmpeg
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        print("✓ ffmpeg is installed")
    except (subprocess.SubprocessError, FileNotFoundError):
        print("✗ ffmpeg is not installed. Please install it from https://ffmpeg.org/download.html")
        sys.exit(1)

def get_user_agent():
    """Return a random user agent to avoid detection."""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
    ]
    return random.choice(user_agents)

def get_clips_url(username, period="24h"):
    """Generate the URL for a streamer's clips page."""
    # Sanitize username
    username = username.strip().lower()
    return f"https://www.twitch.tv/{username}/clips?filter=clips&range={period}"

def scrape_clips(username, hours=24, limit=5, min_views=0):
    """
    Scrape clips information from a streamer's Twitch page.
    
    This is a fallback approach for when API access is not available.
    """
    period = "24h"
    if hours == 7 * 24:
        period = "7d"
    elif hours == 30 * 24:
        period = "30d"
    elif hours == 90 * 24:
        period = "all"
        
    clips_url = get_clips_url(username, period)
    print(f"Fetching clips from: {clips_url}")
    
    # We'll use yt-dlp to list available clips
    try:
        command = [
            'yt-dlp', 
            '--flat-playlist',
            '--dump-json',
            f'https://www.twitch.tv/{username}/clips',
            '--match-filter', f'view_count >= {min_views}',
            '--playlist-end', str(limit)
        ]
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Error running yt-dlp: {result.stderr}")
            return []
            
        clips = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
                
            try:
                clip_data = json.loads(line)
                # Extract useful info
                clip = {
                    'id': clip_data.get('id', ''),
                    'title': clip_data.get('title', 'Untitled Clip'),
                    'url': clip_data.get('webpage_url', ''),
                    'thumbnail_url': clip_data.get('thumbnail', ''),
                    'view_count': clip_data.get('view_count', 0),
                    'duration': clip_data.get('duration', 0),
                    'created_at': clip_data.get('upload_date', ''),
                    'broadcaster_name': username,
                }
                clips.append(clip)
            except json.JSONDecodeError:
                continue
                
        print(f"Found {len(clips)} clips.")
        return clips
            
    except Exception as e:
        print(f"Error scraping clips: {str(e)}")
        return []

def download_clip(clip, output_dir, output_format='mp4'):
    """Download a single clip using yt-dlp."""
    try:
        clip_url = clip.get('url')
        if not clip_url:
            print(f"Error: No URL for clip {clip.get('title')}")
            return None
            
        # Create sanitized filename
        broadcaster = clip.get('broadcaster_name', 'unknown')
        title = clip.get('title', 'untitled')
        
        # Remove invalid characters
        sanitized_title = re.sub(r'[\\/*?:"<>|]', '_', title)
        filename = f"{broadcaster} - {sanitized_title}.{output_format}"
        
        # Create full output path
        output_path = os.path.join(output_dir, filename)
        
        # Check if file already exists
        if os.path.exists(output_path):
            print(f"Clip already exists: {output_path}")
            return output_path
            
        print(f"Downloading: {title}")
        
        # Download with yt-dlp
        command = [
            'yt-dlp',
            '-o', output_path,
            '-f', 'best',  # Get the best quality
            clip_url
        ]
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Error downloading clip: {result.stderr}")
            return None
            
        if not os.path.exists(output_path):
            print(f"Download finished but file not found: {output_path}")
            return None
            
        print(f"Successfully downloaded: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Error downloading clip: {str(e)}")
        return None

def create_metadata_file(clip, video_path, output_format='json'):
    """Create a metadata file for easier uploading to platforms."""
    try:
        output_path = video_path.rsplit('.', 1)[0] + f'.{output_format}'
        
        metadata = {
            'title': f"{clip.get('broadcaster_name', 'Twitch')} - {clip.get('title', 'Clip')}",
            'description': f"Clip from {clip.get('broadcaster_name', '')} on Twitch\n\nOriginal clip: {clip.get('url', '')}",
            'tags': [
                clip.get('broadcaster_name', '').lower(),
                'twitch',
                'gaming',
                'clip',
                'highlights'
            ],
            'category': 'Gaming',
            'visibility': 'public',
            'original_url': clip.get('url', ''),
            'views': clip.get('view_count', 0),
            'clip_created_at': clip.get('created_at', ''),
            'downloaded_at': datetime.datetime.now().isoformat()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
            
        print(f"Created metadata file: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Error creating metadata file: {str(e)}")
        return None

def generate_platform_instructions(downloaded_clips, output_dir):
    """Generate instructions for manually uploading to various platforms."""
    if not downloaded_clips:
        return
        
    platforms = ['YouTube', 'TikTok', 'Instagram']
    
    instructions = {
        'YouTube': [
            "1. Go to https://studio.youtube.com/",
            "2. Click 'CREATE' > 'Upload video'",
            "3. Select the downloaded clip file",
            "4. Use the metadata file (JSON) to fill in title, description, and tags",
            "5. Set visibility to Public",
            "6. Click 'NEXT' through the screens and then 'PUBLISH'"
        ],
        'TikTok': [
            "1. Open the TikTok app on your device",
            "2. Tap the '+' button to create a new video",
            "3. Tap 'Upload' and select the downloaded clip",
            "4. Ensure the clip is under 60 seconds (TikTok's limit)",
            "5. Add relevant text, effects, and hashtags",
            "6. Tap 'Next' and then 'Post'"
        ],
        'Instagram': [
            "1. Open the Instagram app on your device",
            "2. Tap the '+' button at the bottom and select 'Post'",
            "3. Select the downloaded clip",
            "4. Apply filters if desired",
            "5. Write a caption including attribution to the original creator",
            "6. Add relevant hashtags and location",
            "7. Tap 'Share'"
        ]
    }
    
    instructions_path = os.path.join(output_dir, "upload_instructions.txt")
    
    with open(instructions_path, 'w', encoding='utf-8') as f:
        f.write("==== UPLOAD INSTRUCTIONS ====\n\n")
        f.write(f"Downloaded clips directory: {os.path.abspath(output_dir)}\n")
        f.write(f"Number of clips: {len(downloaded_clips)}\n\n")
        
        for platform in platforms:
            f.write(f"=== {platform} Instructions ===\n")
            for step in instructions[platform]:
                f.write(f"{step}\n")
            f.write("\n")
            
        f.write("==== IMPORTANT NOTES ====\n")
        f.write("1. Always give credit to the original content creator\n")
        f.write("2. Follow each platform's community guidelines\n")
        f.write("3. Consider adding your own branding/intro if reusing content regularly\n")
        f.write("4. Check each platform's specific size/length/format requirements\n")
    
    print(f"Created upload instructions: {instructions_path}")

def main():
    """Main entry point for the application."""
    args = setup_argparse()
    check_dependencies()
    
    print(f"=== Twitch Clip Downloader ===")
    print(f"Target streamer: {args.streamer}")
    print(f"Looking back {args.hours} hours")
    print(f"Clip limit: {args.limit}")
    print(f"Minimum views: {args.min_views}")
    print()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Get list of clips
    clips = scrape_clips(
        username=args.streamer,
        hours=args.hours,
        limit=args.limit,
        min_views=args.min_views
    )
    
    if not clips:
        print(f"No clips found for {args.streamer} in the last {args.hours} hours.")
        return
    
    # Sort by view count
    clips.sort(key=lambda x: x.get('view_count', 0), reverse=True)
    
    # Download each clip
    downloaded_clips = []
    
    for i, clip in enumerate(clips, 1):
        print(f"\nProcessing clip {i}/{len(clips)}")
        print(f"Title: {clip.get('title')}")
        print(f"Views: {clip.get('view_count', 0)}")
        
        output_path = download_clip(clip, args.output_dir, args.format)
        
        if output_path and args.metadata:
            metadata_path = create_metadata_file(clip, output_path)
            
        if output_path:
            downloaded_clips.append((clip, output_path))
    
    print(f"\nDownloaded {len(downloaded_clips)}/{len(clips)} clips to {os.path.abspath(args.output_dir)}")
    
    # Generate instruction file
    generate_platform_instructions(downloaded_clips, args.output_dir)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        sys.exit(1)
