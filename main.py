from gui.main_gui import ScraperApp
import tkinter as tk

# Main entry point of the application
if __name__ == "__main__":
    root = tk.Tk()  # Initialize the main Tkinter window
    app = ScraperApp(root)  # Create an instance of the ScraperApp (from gui.py)
    root.mainloop()  # Start the Tkinter main loop
    