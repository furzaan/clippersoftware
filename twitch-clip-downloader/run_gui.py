"""
Simplified runner for the Twitch Clip Downloader GUI
This script ensures the GUI stays open and displays any errors
"""

import tkinter as tk
from tkinter import ttk
import sys
import traceback
import os

# Try to import the GUI class
try:
    # Updated import path to use the correct directory
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from twitch_clip_downloader_gui import TwitchClipDownloaderGUI
except ImportError:
    print("Error: Could not import TwitchClipDownloaderGUI.")
    print("Make sure twitch_clip_downloader_gui.py is in the correct location.")
    print(f"Current directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    input("Press Enter to exit...")
    sys.exit(1)

def main():
    try:
        # Create the main window
        root = tk.Tk()
        root.title("Twitch Clip Downloader")
        
        # Add error handling message
        error_frame = ttk.Frame(root, padding=10)
        error_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create the application
        app = TwitchClipDownloaderGUI(root)
        
        # Start the main loop
        print("Starting Twitch Clip Downloader GUI...")
        root.mainloop()
        
    except Exception as e:
        print(f"Error starting application: {e}")
        traceback.print_exc()
        
        # Create error window if main window fails
        error_root = tk.Tk()
        error_root.title("Error")
        error_root.geometry("500x300")
        
        error_label = ttk.Label(
            error_root, 
            text=f"An error occurred:\n\n{str(e)}\n\nCheck the console for details.",
            wraplength=450
        )
        error_label.pack(padx=20, pady=20)
        
        ttk.Button(error_root, text="Close", command=error_root.destroy).pack(pady=10)
        
        error_root.mainloop()

if __name__ == "__main__":
    main()
    # Keep console open to see any errors
    input("\nPress Enter to exit...")