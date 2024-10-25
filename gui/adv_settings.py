from constants import DEFAULT_BLACKLIST
import tkinter as tk
from tkinter import filedialog, messagebox
import json

class AdvSettingsGUI:
    def __init__(self, root, app_instance, adv_settings):
        """Initializes the Advanced Settings window."""
        self.root = root
        self.app_instance = app_instance

        root.title("Advanced Settings")
        root.geometry("400x300")

        # Blacklist Label with Tooltip
        self.blacklist_label = tk.Label(root, text="Blacklist:")
        self.blacklist_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # Tooltip for blacklist label
        def show_tooltip(event):
            tooltip = tk.Toplevel(root)
            tooltip.wm_overrideredirect(True)
            tooltip.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
            label = tk.Label(tooltip, text="URLs containing these components won't be scraped. One entry per line.",
                             background="yellow", relief="solid", borderwidth=1)
            label.pack()
            root.tooltip = tooltip

        def hide_tooltip(event):
            if hasattr(root, 'tooltip'):
                root.tooltip.destroy()

        self.blacklist_label.bind("<Enter>", show_tooltip)
        self.blacklist_label.bind("<Leave>", hide_tooltip)

        # Scrollable Textbox for Blacklist
        self.blacklist_frame = tk.Frame(root)
        self.blacklist_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        self.scrollbar = tk.Scrollbar(self.blacklist_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.blacklist_text = tk.Text(self.blacklist_frame, height=10, width=40, wrap=tk.NONE, yscrollcommand=self.scrollbar.set)
        self.blacklist_text.pack(side=tk.LEFT, fill=tk.BOTH)
        self.scrollbar.config(command=self.blacklist_text.yview)

        # Set the default blacklist content
        blacklist_content = adv_settings.get('blacklist', DEFAULT_BLACKLIST)
        self.blacklist_text.insert(tk.END, blacklist_content)

        # Export and Import Buttons
        self.export_btn = tk.Button(root, text="Export Settings", command=lambda: self.export_settings(self.root))
        self.export_btn.grid(row=2, column=0, padx=10, pady=5, sticky="w")

        self.import_btn = tk.Button(root, text="Import Settings", command=lambda: self.import_settings(self.app_instance, self.root))
        self.import_btn.grid(row=2, column=1, padx=10, pady=5, sticky="w")

    def export_settings(self, adv_window):
        """Export current settings from the main GUI to a file."""
        all_settings = {
            "settings": {
                "url": self.app_instance.url_entry.get(),
                "product_identifier": self.app_instance.product_identifier_entry.get(),
                "prod_name": self.app_instance.prod_name_el.get(),
                "prod_sku": self.app_instance.prod_sku_el.get(),
                "prod_price": self.app_instance.prod_price_el.get(),
                "prod_desc": self.app_instance.prod_desc_el.get(),
                "prod_image": self.app_instance.prod_image_el.get(),
            },
            "adv_settings": {
                "blacklist": self.blacklist_text.get("1.0", tk.END).strip(), 
            },
        }
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, 'w') as file:
                json.dump(all_settings, file, indent=4)
            messagebox.showinfo("Export Successful", f"Settings have been exported to {file_path}")
            adv_window.focus_force()

    def import_settings(self, app_instance, adv_window):
        """Import settings and apply them to the main GUI."""
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        
        if file_path:
            with open(file_path, 'r') as file:
                loaded_data = json.load(file)
            
            # Set the input fields of the main window based on imported settings
            settings = loaded_data.get("settings", {})
            self.app_instance.url_entry.delete(0, tk.END)
            self.app_instance.url_entry.insert(0, settings.get("url", ""))

            self.app_instance.product_identifier_entry.delete(0, tk.END)
            self.app_instance.product_identifier_entry.insert(0, settings.get("product_identifier", ""))

            self.app_instance.prod_name_el.delete(0, tk.END)
            self.app_instance.prod_name_el.insert(0, settings.get("prod_name", ""))

            self.app_instance.prod_sku_el.delete(0, tk.END)
            self.app_instance.prod_sku_el.insert(0, settings.get("prod_sku", ""))

            self.app_instance.prod_price_el.delete(0, tk.END)
            self.app_instance.prod_price_el.insert(0, settings.get("prod_price", ""))
 
            self.app_instance.prod_desc_el.delete(0, tk.END)
            self.app_instance.prod_desc_el.insert(0, settings.get("prod_desc", ""))

            self.app_instance.prod_image_el.delete(0, tk.END)
            self.app_instance.prod_image_el.insert(0, settings.get("prod_image", ""))

            # handle the advanced setting
            adv_settings = loaded_data.get("adv_settings", {})

            # Set the blacklist text
            self.blacklist_text.delete("1.0", tk.END)

            blacklist = adv_settings.get("blacklist", DEFAULT_BLACKLIST)

            self.blacklist_text.insert(tk.END, blacklist)

            app_instance.adv_settings = adv_settings

            messagebox.showinfo("Import Successful", f"Settings have been imported from {file_path}")
            adv_window.destroy()