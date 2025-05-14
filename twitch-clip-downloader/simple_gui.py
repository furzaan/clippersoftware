"""
Twitch Clip Downloader GUI
A standalone version with full clip downloading functionality
"""

import os
import sys
import threading
import datetime
import subprocess
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import re
import random
import time
from pathlib import Path

class RedirectText:
    """Class for redirecting stdout to a tkinter Text widget."""
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = ""

    def write(self, string):
        self.buffer += string
        self.text_widget.configure(state="normal")
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)
        self.text_widget.configure(state="disabled")
    
    def flush(self):
        pass

class TwitchClipDownloaderGUI:
    """GUI for the Twitch Clip Downloader."""
    
    def __init__(self, root):
        """Initialize the GUI."""
        self.root = root
        self.root.title("Twitch Clip Downloader")
        self.root.geometry("700x600")
        self.root.minsize(600, 500)
        
        # Set up main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create input frame
        input_frame = ttk.LabelFrame(main_frame, text="Download Settings", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        
        # Create form elements
        ttk.Label(input_frame, text="Streamer Username:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.streamer_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.streamer_var, width=30).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(input_frame, text="Time Period:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.period_var = tk.StringVar(value="24h")
        period_combo = ttk.Combobox(input_frame, textvariable=self.period_var, width=10)
        period_combo['values'] = ('24h', '7d', '30d', 'all')
        period_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(input_frame, text="Maximum Clips:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.limit_var = tk.IntVar(value=5)
        ttk.Spinbox(input_frame, from_=1, to=50, textvariable=self.limit_var, width=5).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(input_frame, text="Minimum Views:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.min_views_var = tk.IntVar(value=0)
        ttk.Spinbox(input_frame, from_=0, to=100000, textvariable=self.min_views_var, width=10).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(input_frame, text="Output Format:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.format_var = tk.StringVar(value="mp4")
        format_combo = ttk.Combobox(input_frame, textvariable=self.format_var, width=5)
        format_combo['values'] = ('mp4', 'mov')
        format_combo.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(input_frame, text="Output Directory:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.output_dir_var = tk.StringVar(value=os.path.join(os.getcwd(), "downloads"))
        output_dir_frame = ttk.Frame(input_frame)
        output_dir_frame.grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(output_dir_frame, textvariable=self.output_dir_var, width=30).pack(side=tk.LEFT)
        ttk.Button(output_dir_frame, text="Browse", command=self.browse_output_dir).pack(side=tk.LEFT, padx=5)
        
        # Create options frame
        options_frame = ttk.Frame(input_frame)
        options_frame.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        self.create_metadata_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Create Metadata Files", variable=self.create_metadata_var).pack(side=tk.LEFT, padx=5)
        
        self.generate_instructions_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Generate Upload Instructions", variable=self.generate_instructions_var).pack(side=tk.LEFT, padx=5)
        
        # Create action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.check_deps_button = ttk.Button(button_frame, text="Check Dependencies", command=self.check_deps)
        self.check_deps_button.pack(side=tk.LEFT, padx=5)
        
        self.download_button = ttk.Button(button_frame, text="Start Download", command=self.start_download)
        self.download_button.pack(side=tk.LEFT, padx=5)
        
        self.open_folder_button = ttk.Button(button_frame, text="Open Output Folder", command=self.open_output_folder)
        self.open_folder_button.pack(side=tk.LEFT, padx=5)
        
        self.download_ffmpeg_button = ttk.Button(button_frame, text="Download FFmpeg", command=self.download_ffmpeg)
        self.download_ffmpeg_button.pack(side=tk.LEFT, padx=5)
        
        # Create output log
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = ScrolledText(log_frame, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.configure(state="disabled")
        
        # Redirect stdout to the text widget
        self.old_stdout = sys.stdout
        sys.stdout = RedirectText(self.log_text)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Initialize
        self.log("Welcome to Twitch Clip Downloader")
        self.log("Fill out the form and click 'Start Download' to begin")
        
        # Check dependencies on startup
        self.root.after(500, self.check_deps)
    
    def log(self, message):
        """Add a message to the log."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def browse_output_dir(self):
        """Open a directory browser dialog."""
        directory = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if directory:
            self.output_dir_var.set(directory)
    
    def download_ffmpeg(self):
        """Download a portable version of ffmpeg."""
        try:
            self.log("Downloading portable ffmpeg...")
            
            # Create directories
            ffmpeg_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg")
            os.makedirs(ffmpeg_dir, exist_ok=True)
            
            # URLs for Windows, adjust for other platforms if needed
            ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
            
            # Download zip file
            import urllib.request
            zip_path = os.path.join(ffmpeg_dir, "ffmpeg.zip")
            self.log(f"Downloading from {ffmpeg_url}...")
            urllib.request.urlretrieve(ffmpeg_url, zip_path)
            
            # Extract zip file
            import zipfile
            self.log("Extracting files...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(ffmpeg_dir)
            
            # Find ffmpeg.exe
            for root, dirs, files in os.walk(ffmpeg_dir):
                if "ffmpeg.exe" in files:
                    self.ffmpeg_path = os.path.join(root, "ffmpeg.exe")
                    self.log(f"✓ ffmpeg installed at: {self.ffmpeg_path}")
                    return True
            
            self.log("Failed to find ffmpeg.exe in extracted files")
            return False
            
        except Exception as e:
            self.log(f"Error downloading ffmpeg: {str(e)}")
            return False
    
    def check_deps(self):
        """Check if required dependencies are installed."""
        self.log("Checking dependencies...")
        
        dependencies_ok = True
        
        try:
            # Check for yt-dlp
            try:
                result = subprocess.run(['yt-dlp', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                version = result.stdout.decode('utf-8').strip()
                self.log(f"✓ yt-dlp is installed (version {version})")
            except (subprocess.SubprocessError, FileNotFoundError):
                self.log("✗ yt-dlp is not installed. Please install it with 'pip install yt-dlp'")
                dependencies_ok = False
            
            # Define possible ffmpeg locations
            ffmpeg_paths = [
                'ffmpeg',                                # Check in PATH
                r'C:\ffmpeg\bin\ffmpeg.exe',             # Common install location
                r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
                r'C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe',
                os.path.join(os.path.expanduser('~'), 'ffmpeg', 'bin', 'ffmpeg.exe')
            ]
            
            # Try each path
            ffmpeg_found = False
            self.ffmpeg_path = None
            
            for path in ffmpeg_paths:
                try:
                    result = subprocess.run([path, '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                    version_output = result.stdout.decode('utf-8').split('\n')[0]
                    self.log(f"✓ ffmpeg is installed at {path} ({version_output})")
                    ffmpeg_found = True
                    self.ffmpeg_path = path
                    break
                except (subprocess.SubprocessError, FileNotFoundError):
                    continue
            
            if not ffmpeg_found:
                self.log("✗ ffmpeg is not installed or not found in PATH")
                self.log("Please install ffmpeg from https://ffmpeg.org/download.html")
                self.log("You can use the 'Download FFmpeg' button to get a portable version")
                dependencies_ok = False
            
            if dependencies_ok:
                self.status_var.set("Dependencies OK")
            else:
                self.status_var.set("Missing dependencies")
                messagebox.showwarning(
                    "Missing Dependencies",
                    "Some required dependencies are missing. Please install them before downloading clips."
                )
                
        except Exception as e:
            self.log(f"Error checking dependencies: {str(e)}")
            self.status_var.set("Error checking dependencies")
    
    def ask_ffmpeg_path(self):
        """Ask the user to locate the ffmpeg executable."""
        result = messagebox.askyesno(
            "FFmpeg Not Found",
            "FFmpeg was not found in your PATH or common install locations.\n\n"
            "Would you like to manually locate the ffmpeg.exe file?"
        )
        
        if result:
            ffmpeg_file = filedialog.askopenfilename(
                title="Select ffmpeg.exe",
                filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
            )
            
            if ffmpeg_file and os.path.exists(ffmpeg_file):
                try:
                    result = subprocess.run([ffmpeg_file, '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                    version_output = result.stdout.decode('utf-8').split('\n')[0]
                    self.log(f"✓ ffmpeg is installed at {ffmpeg_file} ({version_output})")
                    self.ffmpeg_path = ffmpeg_file
                    self.status_var.set("FFmpeg manually set")
                except:
                    self.log("✗ The selected file is not a valid ffmpeg executable")
                    messagebox.showerror("Error", "The selected file is not a valid ffmpeg executable")
    
    def open_output_folder(self):
        """Open the output folder in the file explorer."""
        output_dir = self.output_dir_var.get()
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Open folder based on OS
        if sys.platform == 'win32':
            os.startfile(output_dir)
        elif sys.platform == 'darwin':  # macOS
            subprocess.run(['open', output_dir], check=True)
        else:  # Linux
            subprocess.run(['xdg-open', output_dir], check=True)
    
    def get_user_agent(self):
        """Return a random user agent to avoid detection."""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
        ]
        return random.choice(user_agents)
    
    def scrape_clips(self, username, period="24h", limit=5, min_views=0):
        """Scrape clips information from a streamer's Twitch page."""
        self.log(f"Searching for clips from {username} ({period})...")
        
        # Map period to hours for display
        hours_map = {
            "24h": 24,
            "7d": 7 * 24,
            "30d": 30 * 24,
            "all": "all time"
        }
        
        hours_display = hours_map.get(period, period)
        self.log(f"Looking back {hours_display} hours/period")
        
        try:
            # Use yt-dlp to list available clips
            command = [
                'yt-dlp', 
                '--flat-playlist',
                '--dump-json',
                f'https://www.twitch.tv/{username}/clips',
                '--match-filter', f'view_count >= {min_views}',
                '--playlist-end', str(limit)
            ]
            
            if period != "all":
                # Add time filter if not "all time"
                command.extend(['--dateafter', self.get_date_filter(period)])
            
            self.log(f"Running clip search...")
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.log(f"Error running yt-dlp: {result.stderr}")
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
                    
            self.log(f"Found {len(clips)} clips")
            
            # Sort by view count
            clips.sort(key=lambda x: x.get('view_count', 0), reverse=True)
            
            return clips
            
        except Exception as e:
            self.log(f"Error scraping clips: {str(e)}")
            return []
    
    def get_date_filter(self, period):
        """Convert period to a date filter string for yt-dlp."""
        now = datetime.datetime.now()
        
        if period == "24h":
            # 24 hours ago
            date = now - datetime.timedelta(hours=24)
        elif period == "7d":
            # 7 days ago
            date = now - datetime.timedelta(days=7)
        elif period == "30d":
            # 30 days ago
            date = now - datetime.timedelta(days=30)
        else:
            # Default to 24 hours
            date = now - datetime.timedelta(hours=24)
        
        # Format date as YYYYMMDD
        return date.strftime("%Y%m%d")
    
    def download_clip(self, clip, output_dir, output_format='mp4'):
        """Download a single clip using yt-dlp."""
        try:
            clip_url = clip.get('url')
            if not clip_url:
                self.log(f"Error: No URL for clip {clip.get('title')}")
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
                self.log(f"Clip already exists: {output_path}")
                return output_path
                
            self.log(f"Downloading: {title}")
            
            # Download with yt-dlp
            command = [
                'yt-dlp',
                '-o', output_path,
                '-f', 'best',  # Get the best quality
                clip_url
            ]
            
            # Add ffmpeg location if we found it
            if hasattr(self, 'ffmpeg_path') and self.ffmpeg_path:
                command.extend(['--ffmpeg-location', self.ffmpeg_path])
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.log(f"Error downloading clip: {result.stderr}")
                return None
                
            if not os.path.exists(output_path):
                self.log(f"Download finished but file not found: {output_path}")
                return None
                
            self.log(f"Successfully downloaded: {output_path}")
            return output_path
            
        except Exception as e:
            self.log(f"Error downloading clip: {str(e)}")
            return None
    
    def create_metadata_file(self, clip, video_path):
        """Create a metadata file for easier uploading to platforms."""
        try:
            output_path = video_path.rsplit('.', 1)[0] + '.json'
            
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
                
            self.log(f"Created metadata file: {output_path}")
            return output_path
            
        except Exception as e:
            self.log(f"Error creating metadata file: {str(e)}")
            return None
    
    def generate_platform_instructions(self, downloaded_clips, output_dir):
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
        
        self.log(f"Created upload instructions: {instructions_path}")
    
    def start_download(self):
        """Start the download process in a separate thread."""
        # Validate inputs
        streamer = self.streamer_var.get().strip()
        if not streamer:
            messagebox.showerror("Error", "Please enter a streamer username")
            return
        
        # Create output directory if it doesn't exist
        output_dir = self.output_dir_var.get()
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Disable buttons during download
        self.disable_buttons()
        
        # Start download in a separate thread
        self.status_var.set("Downloading clips...")
        threading.Thread(target=self.download_clips_thread, daemon=True).start()
    
    def disable_buttons(self):
        """Disable buttons during processing."""
        self.download_button.configure(state="disabled")
        self.check_deps_button.configure(state="disabled")
    
    def enable_buttons(self):
        """Re-enable buttons after processing."""
        self.root.after(0, lambda: self.download_button.configure(state="normal"))
        self.root.after(0, lambda: self.check_deps_button.configure(state="normal"))
    
    def download_clips_thread(self):
        """Download clips based on user input in a separate thread."""
        try:
            # Get parameters from form
            streamer = self.streamer_var.get().strip()
            period = self.period_var.get()
            limit = self.limit_var.get()
            min_views = self.min_views_var.get()
            output_format = self.format_var.get()
            output_dir = self.output_dir_var.get()
            create_metadata = self.create_metadata_var.get()
            generate_instructions = self.generate_instructions_var.get()
            
            # Get clips
            self.log(f"Searching for clips from {streamer} ({period})...")
            clips = self.scrape_clips(
                username=streamer,
                period=period,
                limit=limit,
                min_views=min_views
            )
            
            if not clips:
                self.log(f"No clips found for {streamer} in the selected time period.")
                self.root.after(0, lambda: self.status_var.set("No clips found"))
                self.root.after(0, self.enable_buttons)
                return
            
            # Download each clip
            downloaded_clips = []
            
            for i, clip in enumerate(clips, 1):
                self.log(f"\nProcessing clip {i}/{len(clips)}")
                self.log(f"Title: {clip.get('title')}")
                self.log(f"Views: {clip.get('view_count', 0)}")
                
                # Update status
                self.root.after(0, lambda i=i, total=len(clips): 
                    self.status_var.set(f"Downloading {i}/{total} clips"))
                
                output_path = self.download_clip(clip, output_dir, output_format)
                
                if output_path and create_metadata:
                    metadata_path = self.create_metadata_file(clip, output_path)
                    
                if output_path:
                    downloaded_clips.append((clip, output_path))
            
            self.log(f"\nDownloaded {len(downloaded_clips)}/{len(clips)} clips to {os.path.abspath(output_dir)}")
            
            # Generate instruction file
            if generate_instructions:
                self.generate_platform_instructions(downloaded_clips, output_dir)
            
            # Update status
            self.root.after(0, lambda: self.status_var.set(f"Completed: {len(downloaded_clips)} clips downloaded"))
            
            # Show completion message
            self.root.after(0, lambda: messagebox.showinfo(
                "Download Complete", 
                f"Successfully downloaded {len(downloaded_clips)} clips."
            ))
            
        except Exception as e:
            self.log(f"Error during download: {str(e)}")
            import traceback
            traceback.print_exc()
            self.root.after(0, lambda: self.status_var.set("Error during download"))
            self.root.after(0, lambda e=str(e): messagebox.showerror("Error", f"An error occurred: {e}"))
        
        finally:
            # Re-enable buttons
            self.root.after(0, self.enable_buttons)
    
    def on_closing(self):
        """Clean up before closing."""
        # Restore stdout
        sys.stdout = self.old_stdout
        self.root.destroy()

def main():
    """Start the GUI application."""
    root = tk.Tk()
    
    # Set theme (use a built-in theme)
    style = ttk.Style()
    if 'clam' in style.theme_names():
        style.theme_use('clam')
    
    app = TwitchClipDownloaderGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")