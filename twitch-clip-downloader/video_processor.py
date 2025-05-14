"""
A utility script for processing and preparing downloaded Twitch clips for various platforms.
Provides functions to trim clips, add watermarks, convert formats, and more.
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path

def check_ffmpeg():
    """Check if ffmpeg is installed and available."""
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        print("ffmpeg is not installed or not found in PATH. Please install it from https://ffmpeg.org/download.html")
        return False

def list_video_files(directory, extensions=None):
    """List all video files in a directory with specific extensions."""
    if extensions is None:
        extensions = ['.mp4', '.mov', '.avi', '.mkv']
    
    video_files = []
    for ext in extensions:
        video_files.extend(list(Path(directory).glob(f'*{ext}')))
    
    return [str(f) for f in video_files]

def trim_video(input_path, output_path=None, start_time=0, duration=None):
    """
    Trim a video file using ffmpeg.
    
    Args:
        input_path: Path to input video file
        output_path: Path to output file (default: adds "_trimmed" to input)
        start_time: Start time in seconds
        duration: Duration in seconds (if None, trim to the end)
    
    Returns:
        Path to the trimmed video file
    """
    if not check_ffmpeg():
        return None
    
    if output_path is None:
        filename, ext = os.path.splitext(input_path)
        output_path = f"{filename}_trimmed{ext}"
    
    command = ['ffmpeg', '-i', input_path, '-ss', str(start_time)]
    
    if duration is not None:
        command.extend(['-t', str(duration)])
    
    command.extend(['-c', 'copy', output_path, '-y'])
    
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Trimmed video saved to: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Error trimming video: {e}")
        return None

def add_watermark(input_path, watermark_text, output_path=None, position="bottomright", fontsize=24):
    """
    Add a text watermark to a video using ffmpeg.
    
    Args:
        input_path: Path to input video file
        watermark_text: Text to use as watermark
        output_path: Path to output file (default: adds "_watermarked" to input)
        position: Position of watermark (topleft, topright, bottomleft, bottomright, center)
        fontsize: Font size for the watermark text
    
    Returns:
        Path to the watermarked video file
    """
    if not check_ffmpeg():
        return None
    
    if output_path is None:
        filename, ext = os.path.splitext(input_path)
        output_path = f"{filename}_watermarked{ext}"
    
    # Define position coordinates
    positions = {
        "topleft": "10:10",
        "topright": "w-tw-10:10",
        "bottomleft": "10:h-th-10",
        "bottomright": "w-tw-10:h-th-10",
        "center": "(w-tw)/2:(h-th)/2"
    }
    
    position_value = positions.get(position.lower(), positions["bottomright"])
    
    # Build ffmpeg command
    command = [
        'ffmpeg', '-i', input_path,
        '-vf', f"drawtext=text='{watermark_text}':fontcolor=white:fontsize={fontsize}:box=1:boxcolor=black@0.5:boxborderw=5:x={position_value}",
        '-codec:a', 'copy', output_path, '-y'
    ]
    
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Watermarked video saved to: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Error adding watermark: {e}")
        return None

def add_intro(input_path, intro_path, output_path=None):
    """
    Add an intro video to the beginning of a clip.
    
    Args:
        input_path: Path to input video file
        intro_path: Path to intro video file
        output_path: Path to output file (default: adds "_with_intro" to input)
    
    Returns:
        Path to the combined video file
    """
    if not check_ffmpeg():
        return None
    
    if not os.path.exists(intro_path):
        print(f"Intro file not found: {intro_path}")
        return None
    
    if output_path is None:
        filename, ext = os.path.splitext(input_path)
        output_path = f"{filename}_with_intro{ext}"
    
    # Create a temporary file for the concat list
    temp_list = "concat_list.txt"
    with open(temp_list, "w") as f:
        f.write(f"file '{os.path.abspath(intro_path)}'\n")
        f.write(f"file '{os.path.abspath(input_path)}'\n")
    
    # Build ffmpeg command
    command = [
        'ffmpeg', '-f', 'concat', '-safe', '0',
        '-i', temp_list, '-c', 'copy', output_path, '-y'
    ]
    
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Video with intro saved to: {output_path}")
        # Remove temp file
        os.remove(temp_list)
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Error adding intro: {e}")
        if os.path.exists(temp_list):
            os.remove(temp_list)
        return None

def convert_format(input_path, output_format, output_path=None):
    """
    Convert a video to a different format.
    
    Args:
        input_path: Path to input video file
        output_format: Output format (mp4, mov, etc.)
        output_path: Path to output file (default: changes extension of input)
    
    Returns:
        Path to the converted video file
    """
    if not check_ffmpeg():
        return None
    
    if output_path is None:
        filename, _ = os.path.splitext(input_path)
        output_path = f"{filename}.{output_format}"
    
    # Build ffmpeg command
    command = [
        'ffmpeg', '-i', input_path,
        '-c:v', 'libx264', '-c:a', 'aac',
        output_path, '-y'
    ]
    
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Converted video saved to: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Error converting video: {e}")
        return None

def resize_for_platform(input_path, platform, output_path=None):
    """
    Resize a video for a specific platform.
    
    Args:
        input_path: Path to input video file
        platform: Target platform (tiktok, instagram, youtube)
        output_path: Path to output file
    
    Returns:
        Path to the resized video file
    """
    if not check_ffmpeg():
        return None
    
    # Platform-specific dimensions and settings
    platform_settings = {
        "tiktok": {
            "resolution": "1080:1920",  # 9:16 vertical
            "description": "TikTok (vertical 9:16)"
        },
        "instagram": {
            "resolution": "1080:1080",  # 1:1 square
            "description": "Instagram (square 1:1)"
        },
        "instagram_story": {
            "resolution": "1080:1920",  # 9:16 vertical
            "description": "Instagram Story (vertical 9:16)"
        },
        "youtube": {
            "resolution": "1920:1080",  # 16:9 horizontal
            "description": "YouTube (horizontal 16:9)"
        }
    }
    
    if platform.lower() not in platform_settings:
        print(f"Unknown platform: {platform}")
        print(f"Supported platforms: {', '.join(platform_settings.keys())}")
        return None
    
    settings = platform_settings[platform.lower()]
    
    if output_path is None:
        filename, ext = os.path.splitext(input_path)
        output_path = f"{filename}_for_{platform}{ext}"
    
    # Build ffmpeg command with padding to maintain aspect ratio
    command = [
        'ffmpeg', '-i', input_path,
        '-vf', f"scale={settings['resolution']}:force_original_aspect_ratio=decrease,pad={settings['resolution']}:(ow-iw)/2:(oh-ih)/2",
        '-c:a', 'copy', output_path, '-y'
    ]
    
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Resized video for {settings['description']} saved to: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Error resizing video: {e}")
        return None

def batch_process(input_dir, operations, output_dir=None):
    """
    Batch process multiple videos.
    
    Args:
        input_dir: Directory containing videos to process
        operations: List of operations to perform
        output_dir: Directory to save processed videos
    
    Returns:
        List of paths to processed videos
    """
    if output_dir is None:
        output_dir = os.path.join(input_dir, "processed")
    
    os.makedirs(output_dir, exist_ok=True)
    
    video_files = list_video_files(input_dir)
    processed_files = []
    
    for video_file in video_files:
        filename = os.path.basename(video_file)
        output_path = os.path.join(output_dir, filename)
        current_input = video_file
        
        for operation in operations:
            op_type = operation.get("type")
            if op_type == "trim":
                current_input = trim_video(
                    current_input,
                    output_path=os.path.join(output_dir, f"{os.path.splitext(filename)[0]}_trimmed{os.path.splitext(filename)[1]}"),
                    start_time=operation.get("start_time", 0),
                    duration=operation.get("duration")
                )
            elif op_type == "watermark":
                current_input = add_watermark(
                    current_input,
                    watermark_text=operation.get("text", ""),
                    output_path=os.path.join(output_dir, f"{os.path.splitext(filename)[0]}_watermarked{os.path.splitext(filename)[1]}"),
                    position=operation.get("position", "bottomright"),
                    fontsize=operation.get("fontsize", 24)
                )
            elif op_type == "intro":
                current_input = add_intro(
                    current_input,
                    intro_path=operation.get("intro_path", ""),
                    output_path=os.path.join(output_dir, f"{os.path.splitext(filename)[0]}_with_intro{os.path.splitext(filename)[1]}")
                )
            elif op_type == "convert":
                current_input = convert_format(
                    current_input,
                    output_format=operation.get("format", "mp4"),
                    output_path=os.path.join(output_dir, f"{os.path.splitext(filename)[0]}.{operation.get('format', 'mp4')}")
                )
            elif op_type == "resize":
                current_input = resize_for_platform(
                    current_input,
                    platform=operation.get("platform", "youtube"),
                    output_path=os.path.join(output_dir, f"{os.path.splitext(filename)[0]}_for_{operation.get('platform', 'youtube')}{os.path.splitext(filename)[1]}")
                )
        
        if current_input and current_input != video_file:
            processed_files.append(current_input)
    
    return processed_files

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Process Twitch clips for uploading to social platforms")
    
    parser.add_argument("--input", "-i", type=str, required=True, help="Input video file or directory")
    parser.add_argument("--output", "-o", type=str, help="Output file or directory")
    parser.add_argument("--batch", "-b", action="store_true", help="Process all videos in input directory")
    
    subparsers = parser.add_subparsers(dest="operation", help="Operation to perform")
    
    # Trim operation
    trim_parser = subparsers.add_parser("trim", help="Trim video")
    trim_parser.add_argument("--start", type=float, default=0, help="Start time in seconds")
    trim_parser.add_argument("--duration", type=float, help="Duration in seconds")
    
    # Watermark operation
    watermark_parser = subparsers.add_parser("watermark", help="Add watermark")
    watermark_parser.add_argument("--text", type=str, required=True, help="Watermark text")
    watermark_parser.add_argument("--position", type=str, default="bottomright", 
                                 choices=["topleft", "topright", "bottomleft", "bottomright", "center"],
                                 help="Watermark position")
    watermark_parser.add_argument("--fontsize", type=int, default=24, help="Font size")
    
    # Intro operation
    intro_parser = subparsers.add_parser("intro", help="Add intro")
    intro_parser.add_argument("--intro-file", type=str, required=True, help="Path to intro video")
    
    # Convert operation
    convert_parser = subparsers.add_parser("convert", help="Convert format")
    convert_parser.add_argument("--format", type=str, required=True, help="Output format (mp4, mov, etc.)")
    
    # Resize operation
    resize_parser = subparsers.add_parser("resize", help="Resize for platform")
    resize_parser.add_argument("--platform", type=str, required=True, 
                              choices=["tiktok", "instagram", "instagram_story", "youtube"],
                              help="Target platform")
    
    # Batch processing from config
    batch_parser = subparsers.add_parser("batch-config", help="Batch process using config file")
    batch_parser.add_argument("--config", type=str, required=True, help="Path to JSON config file")
    
    return parser.parse_args()

def main():
    """Main entry point."""
    args = parse_args()
    
    # Check if ffmpeg is installed
    if not check_ffmpeg():
        sys.exit(1)
    
    # Handle batch-config operation
    if args.operation == "batch-config":
        if not os.path.exists(args.config):
            print(f"Config file not found: {args.config}")
            sys.exit(1)
        
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
            
            input_dir = config.get("input_dir", args.input)
            output_dir = config.get("output_dir", args.output)
            operations = config.get("operations", [])
            
            processed_files = batch_process(input_dir, operations, output_dir)
            print(f"Processed {len(processed_files)} files")
            
        except json.JSONDecodeError:
            print(f"Invalid JSON in config file: {args.config}")
            sys.exit(1)
        except Exception as e:
            print(f"Error processing batch: {e}")
            sys.exit(1)
        
        sys.exit(0)
    
    # Handle batch processing
    if args.batch:
        if not os.path.isdir(args.input):
            print(f"Input must be a directory for batch processing: {args.input}")
            sys.exit(1)
        
        output_dir = args.output or os.path.join(args.input, "processed")
        os.makedirs(output_dir, exist_ok=True)
        
        video_files = list_video_files(args.input)
        print(f"Found {len(video_files)} video files")
        
        for video_file in video_files:
            filename = os.path.basename(video_file)
            output_path = os.path.join(output_dir, filename)
            
            # Process based on operation
            process_single_file(args, video_file, output_path)
        
        print(f"Batch processing complete. Processed files saved to: {output_dir}")
        sys.exit(0)
    
    # Handle single file processing
    if not os.path.exists(args.input):
        print(f"Input file not found: {args.input}")
        sys.exit(1)
    
    process_single_file(args, args.input, args.output)

def process_single_file(args, input_path, output_path):
    """Process a single video file."""
    if args.operation == "trim":
        trim_video(input_path, output_path, args.start, args.duration)
    elif args.operation == "watermark":
        add_watermark(input_path, args.text, output_path, args.position, args.fontsize)
    elif args.operation == "intro":
        add_intro(input_path, args.intro_file, output_path)
    elif args.operation == "convert":
        convert_format(input_path, args.format, output_path)
    elif args.operation == "resize":
        resize_for_platform(input_path, args.platform, output_path)
    else:
        print("No operation specified. Use --help for usage information.")

if __name__ == "__main__":
    main()
