"""
GUI version of the Twitch Clip Downloader.
A simple interface for downloading Twitch clips without using official APIs.
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

# Import core functionality
try:
    from twitch_clip_downloader import (
        check_dependencies,
        scrape_clips,
        download_clip,
        create_metadata_file,
        generate_platform_instructions
    )
except ImportError:
    # If running as standalone, copy necessary functions
    from twitch_clip_downloader import *

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
        
        ttk.Button(button_frame, text="Check Dependencies", command=self.check_dependencies).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Start Download", command=self.start_download).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Open Output Folder", command=self.open_output_folder).pack(side=tk.LEFT, padx=5)
        
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
        self.root.after(500, self.check_dependencies)
    
    def log(self, message):
        """Add a message to the log."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def browse_output_dir(self):
        """Open a directory browser dialog."""
        directory = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if directory:
            self.output_dir_var.set(directory)
    
    def check_dependencies(self):
        """Check if required dependencies are installed."""
        self.log("Checking dependencies...")
        
        try:
            check_dependencies()
            self.status_var.set("Dependencies OK")
        except Exception as e:
            self.log(f"Error checking dependencies: {str(e)}")
            self.status_var.set("Dependencies missing")
    
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
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Button):
                widget.configure(state="disabled")
        
        # Start download in a separate thread
        self.status_var.set("Downloading clips...")
        threading.Thread(target=self.download_clips, daemon=True).start()
    
    def download_clips(self):
        """Download clips based on user input."""
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
            
            # Map period to hours
            hours_map = {
                "24h": 24,
                "7d": 7 * 24,
                "30d": 30 * 24,
                "all": 365 * 24
            }
            hours = hours_map.get(period, 24)
            
            # Get clips
            self.log(f"Searching for clips from {streamer} ({period})...")
            clips = scrape_clips(
                username=streamer,
                hours=hours,
                limit=limit,
                min_views=min_views
            )
            
            if not clips:
                self.log(f"No clips found for {streamer} in the selected time period.")
                self.root.after(0, self.enable_buttons)
                self.root.after(0, lambda: self.status_var.set("No clips found"))
                return
            
            # Sort by view count
            clips.sort(key=lambda x: x.get('view_count', 0), reverse=True)
            
            # Download each clip
            downloaded_clips = []
            
            for i, clip in enumerate(clips, 1):
                self.log(f"\nProcessing clip {i}/{len(clips)}")
                self.log(f"Title: {clip.get('title')}")
                self.log(f"Views: {clip.get('view_count', 0)}")
                
                output_path = download_clip(clip, output_dir, output_format)
                
                if output_path and create_metadata:
                    metadata_path = create_metadata_file(clip, output_path)
                    
                if output_path:
                    downloaded_clips.append((clip, output_path))
                    
                # Update status
                self.root.after(0, lambda i=i, total=len(clips): 
                    self.status_var.set(f"Downloaded {i}/{total} clips"))
            
            self.log(f"\nDownloaded {len(downloaded_clips)}/{len(clips)} clips to {os.path.abspath(output_dir)}")
            
            # Generate instruction file
            if generate_instructions:
                generate_platform_instructions(downloaded_clips, output_dir)
            
            # Update status
            self.root.after(0, lambda: self.status_var.set(f"Completed: {len(downloaded_clips)} clips downloaded"))
            
            # Show completion message
            self.root.after(0, lambda: messagebox.showinfo(
                "Download Complete", 
                f"Successfully downloaded {len(downloaded_clips)} clips."
            ))
            
        except Exception as e:
            self.log(f"Error during download: {str(e)}")
            self.root.after(0, lambda: self.status_var.set("Error during download"))
            self.root.after(0, lambda e=str(e): messagebox.showerror("Error", f"An error occurred: {e}"))
        
        finally:
            # Re-enable buttons
            self.root.after(0, self.enable_buttons)
    
    def enable_buttons(self):
        """Re-enable all buttons."""
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Button):
                widget.configure(state="normal")
    
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
    main()
