import tkinter as tk
from tkinter import scrolledtext, messagebox
import queue
from scraper import Scraper
from gui.adv_settings import AdvSettingsGUI
import threading
import logging
import os
from logging.handlers import QueueHandler, QueueListener

class ScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Web Scraper")

        # Initialize Scraper object from scraper.py
        self.scraper = Scraper()

        # Store reference to the advanced settings window
        self.adv_window = None
        self.adv_settings = {}

        # Initialize log settings
        self.setup_logger()

        # Bind the window close event to the custom close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # URL input
        self.url_label = tk.Label(root, text="Enter URL:")
        self.url_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.url_entry = tk.Entry(root, width=50)
        self.url_entry.grid(row=0, column=1, columnspan=2, padx=0, pady=0, sticky="w")

        # product_identifier input
        self.product_identifier_label = tk.Label(root, text="Special Product URL Identifier:")
        self.product_identifier_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.product_identifier_entry = tk.Entry(root, width=40)
        self.product_identifier_entry.grid(row=1, column=1, columnspan=2, padx=0, pady=10, sticky="w")

        # Mode selection (HTML or JSON)
        self.mode_html = tk.BooleanVar(value=True)  # Default to HTML mode
        self.mode_json = tk.BooleanVar(value=False)

        self.html_button = tk.Checkbutton(root, text="HTML Mode", variable=self.mode_html, command=self.set_html_mode)
        self.html_button.grid(row=2, column=0, padx=0, pady=10)

        self.json_button = tk.Checkbutton(root, text="JSON-LD Mode", variable=self.mode_json, command=self.set_json_mode)
        self.json_button.grid(row=2, column=1, padx=0, pady=10)

        self.adv_setting_btn = tk.Button(root, text="Advanced Settings", command=self.show_adv_settings)
        self.adv_setting_btn.grid(row=2, column=2, padx=0, pady=10)

        # Product Field Container Frame
        self.product_frame = tk.Frame(root)

        # Optional Product Class Element fields (shown only in HTML mode)
        self.prod_name_label = tk.Label(self.product_frame, text="Product Name Element:")
        self.prod_name_el = tk.Entry(self.product_frame, width=40)
        self.prod_name_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.prod_name_el.grid(row=0, column=1, columnspan=2, padx=20, pady=5, sticky="w")

        self.prod_sku_label = tk.Label(self.product_frame, text="Product SKU Element:")
        self.prod_sku_el = tk.Entry(self.product_frame, width=40)
        self.prod_sku_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.prod_sku_el.grid(row=1, column=1, columnspan=2, padx=20, pady=5, sticky="w")

        self.prod_price_label = tk.Label(self.product_frame, text="Product Price Element:")
        self.prod_price_el = tk.Entry(self.product_frame, width=40)
        self.prod_price_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.prod_price_el.grid(row=2, column=1, columnspan=2, padx=20, pady=5, sticky="w")

        self.prod_desc_label = tk.Label(self.product_frame, text="Product Description Element:")
        self.prod_desc_el = tk.Entry(self.product_frame, width=40)
        self.prod_desc_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.prod_desc_el.grid(row=3, column=1, columnspan=2, padx=20, pady=5, sticky="w")

        self.prod_image_label = tk.Label(self.product_frame, text="Product Image Parent Element:")
        self.prod_image_el = tk.Entry(self.product_frame, width=40)
        self.prod_image_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.prod_image_el.grid(row=4, column=1, columnspan=2, padx=20, pady=5, sticky="w")

        # Pack the product_frame
        self.product_frame.grid(row=4, columnspan=3, padx=10, pady=10, sticky="w")

        # Start and stop buttons
        self.button_frame = tk.Frame(root)
        self.button_frame.grid(row=6, columnspan=3, padx=10, pady=10)
        self.start_button = tk.Button(self.button_frame, text="Start Scraping", command=self.start_scraping)
        self.start_button.grid(row=0, column=0, padx=10)
        self.stop_button = tk.Button(self.button_frame, text="Stop Scraping", command=self.stop_scraping, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=10)

        # Output window (for terminal output redirection)
        self.log_output = scrolledtext.ScrolledText(root, width=70, height=10, state=tk.DISABLED)
        self.log_output.grid(row=7, columnspan=3, padx=10, pady=10)

        self.scraping_thread = None
        self.stop_flag = threading.Event()

        # Initialize a queue for thread-safe logging
        self.log_queue = queue.Queue()
        self.log_buffer = []
        self.process_log_queue()

        # Default: show HTML input fields
        self.show_prod_desc_field()

    def set_html_mode(self):
        self.mode_html.set(True)
        self.mode_json.set(False)
        self.show_prod_desc_field()

    def set_json_mode(self):
        self.mode_html.set(False)
        self.mode_json.set(True)
        self.hide_prod_desc_field()

    def show_prod_desc_field(self):
        self.product_frame.grid(row=4, columnspan=3, padx=10, pady=10, sticky="w")

    def hide_prod_desc_field(self):
        self.product_frame.grid_forget()

    # Start scraping in a separate thread
    def start_scraping(self):
        self.stop_flag.clear()

        url = self.url_entry.get()
        product_identifier = self.product_identifier_entry.get()
        mode = "html" if self.mode_html.get() else "json"
        prod_els = {
            "name": self.prod_name_el.get(),
            "sku": self.prod_sku_el.get(),
            "price": self.prod_price_el.get(),
            "desc": self.prod_desc_el.get(),
            "image": self.prod_image_el.get()
        }

        # Pass the latest settings before starting the scraper
        self.scraper.settings = {
            "url": url, 
            "mode": mode, 
            "product_identifier": product_identifier, 
            "prod_els": prod_els, 
            "log_queue": self.log_queue
        }

        # blacklist is a mandatory input even if empty
        if "blacklist" not in self.adv_settings:
            self.adv_settings["blacklist"] = ""

        # Pass advanced settings as well
        self.scraper.adv_settings = self.adv_settings

        # Hand off and start Scraper class
        self.scraping_thread = threading.Thread(target=self.scraper.start_scraping)
        self.scraping_thread.start()

        # Disable start and enable stop buttons
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

    # Stop scraping by setting a flag
    def stop_scraping(self):
        self.stop_flag.set()
        if self.scraping_thread:
            self.scraping_thread.join()
        self.scraper.stop_scraping()
        self.log_queue.put("Scraping stopped.")
        self.stop_button.config(state=tk.DISABLED)
        self.start_button.config(state=tk.NORMAL)

    # Process log queue
    def process_log_queue(self):
        # Process messages from the queue and add them to the buffer
        while not self.log_queue.empty():
            log_message = self.log_queue.get_nowait()
            self.log_buffer.append(log_message + "\n")

            # If scraping is finished, re-enable buttons
            if "Scraping job finished" in log_message:
                self.start_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)

        # Now display the buffered messages in the output window
        if self.log_buffer:
            self.log_output.config(state=tk.NORMAL)
            self.log_output.insert(tk.END, ''.join(self.log_buffer))
            self.log_output.yview(tk.END)
            self.log_output.config(state=tk.DISABLED)
            self.log_buffer = []

        self.root.after(300, self.process_log_queue)

    def show_adv_settings(self):
        """Show the Advanced Settings window, or focus if already open."""
        if self.adv_window is None or not tk.Toplevel.winfo_exists(self.adv_window): 
            # If there's no window or the previous window was closed, create a new one
            self.adv_window = tk.Toplevel(self.root)
            self.adv_window.protocol("WM_DELETE_WINDOW", self.save_and_close_adv_settings)
            self.adv_settings_gui = AdvSettingsGUI(self.adv_window, self, self.adv_settings)
        else:
            # If the window is already open, bring it to the front
            self.adv_window.focus()

    def save_and_close_adv_settings(self):
        """Save advanced settings and close the advanced settings window."""
        if self.adv_settings_gui:
            self.adv_settings['blacklist'] = self.adv_settings_gui.blacklist_text.get("1.0", tk.END).strip()

        self.adv_window.destroy()
        self.adv_window = None

    def setup_logger(self):
        """Set up thread-safe logging using QueueHandler and QueueListener."""
        self.log_queue = queue.Queue()

        # Set up a QueueHandler to send log messages to the queue
        queue_handler = QueueHandler(self.log_queue)
        logging.basicConfig(level=logging.INFO, handlers=[queue_handler], format="%(asctime)s - %(levelname)s - %(message)s")

        # Start a listener thread that pulls logs from the queue and writes them to the final log handlers
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        log_file_path = os.path.join(desktop_path, "WebshopScraper_log.log")
        queue_handler = QueueHandler(self.log_queue)
        logging.basicConfig(level=logging.INFO, handlers=[queue_handler], format="%(asctime)s - %(levelname)s - %(message)s")

        # Start a listener thread that pulls logs from the queue and writes them to the final log handlers
        file_handler = logging.FileHandler(log_file_path)
        listener = QueueListener(self.log_queue, file_handler)
        listener.start()

    def log(self, message, level=logging.INFO):
        """Log messages to the log file."""
        self.log_output.config(state=tk.NORMAL)
        self.log_output.insert(tk.END, message + "\n")
        self.log_output.yview(tk.END)
        self.log_output.config(state=tk.DISABLED)

        # Logging to the file through the queue
        logging.log(level, message)

    def on_closing(self):
        """Handle the window close event."""
        if self.scraping_thread and self.scraping_thread.is_alive() and messagebox.askokcancel("Quit", "Do you want to quit? Any running scraping task will be cancelled."):
            # Stop scraping if running
            self.stop_scraping()
        self.root.destroy()