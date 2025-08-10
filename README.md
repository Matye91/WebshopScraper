# Webshop Scraper

Webshop Scraper is a program based on the programming language Python. Its purpose is scraping specified web shops and summarizing all products that it finds in a CSV file. The data includes the product name, SKU, price, description, image URL, and page URL. Scraping the online shops of the competition is a common tool, especially used in the trading industry to monitor prices and offerings. Particularly in industries with many products – such as the office supplies trading industry of my own company, Panda Office GmbH – this comes in very handy since regular manual comparison of some 10,000 products is frankly impossible.

## How to Get Started

Simply execute the program via the common `python main.py` (without any command line arguments). Upon starting, a GUI (graphical user interface) will open and ask you for your input details. After filling in your specifications, simply click “Start Scraping” and the scraper will start searching through the provided domain. To abort the script, simply click “Stop Scraping,” and the program will terminate the job.

## What Input Needs to Be Provided?

- **Enter URL** (Mandatory): This is the URL you want to start searching. Webshop Scraper will automatically detect the domain name and collect all links it can find in the form of links (href html tag) and store them into a set(). Sequentially the program will also look for any shop products to be written into a csv-file.
- **Special Product URL Identifier** (optional): To make the scraping faster and more accurate a special string to identify product pages can be defined here. In many online shop systems products URL contain a common part, e.g.: www.mydomian.com/products/ballpoint-pen-1234 in this case enter /products/ as the Special Product URL Identifier. Pages that don’t include this string won’t be scanned for any product data.
- **Mode** (Mandatory): Here you can switch between a JSON/LD mode, or a HTML-tag based mode. Using the first one requires the website to have working Schema Markup of the @Product type. If you are unsure, use https://validator.schema.org/ to test one URL of the website on which there is product. This validator then shows you all mark it found. If there has been a Product-type markup found, feel free to use the simpler JSON/LD mode.

In case the markup is relatively unstructured throughout the website, or it is not existent, there is also an HTML mode available. In this mode additional input fields are available, asking you to specify the DOM element class names of the product name, SKU, price, description and image parent. Those fields are not mandatory. If there is no input provided, Webshop Scraper will look for an itemprop attribute in the DOM with the respective definition:

- **Name** itemprop="name"
- **SKU** itemprop="sku"
- **Price** itemprop="price"
- **Description** itemprop="desc"
- **Image** itemprop="image"

You can search the source code of any product page on the target website for those tags. If they are not provided, it is possible to use the mentioned additional input fields to specify the exact class name of the DOM element(s) in which the respective data can be found.
To do so, right-click on for instance the product name on any product page of your target website and click investigate. The DOM element in which the product name can be found might look like this: `<h1 class="product-title header-h1" itemprop="name">Ballpoint Pen 1234</h1>`. In this example you could use “product-title” as the class name. It’s necessary to specify a unique class name. in this example, for instance, the class header-h1 might also be used for other information than a product name, but product-title very much sounds like a unique class that’s only used for product names. It’s up to you how many and which additional input fields you want to use. Webshop Scraper will fall back to try finding the itemprop attribute for any empty property.

### Advanced Settings

In the advanced settings there are currently only two functions: (1) an input field of blacklisted URL parts that should not be scrapped. This way you not only able to avoid searching in common side pages like `/contact`, which certainly don’t contain any products, but you are also able to exclude whole copies of the target websites just in another language by for instance excluding `/es`. (2) you can export your entire settings to a .json file, which later can be imported again. This is very helpful, if you are scrapping the same website on a regular base.

## Tips on How to Get More Out of It

Webshop Scraper automatically detects the domain you are providing and collects all URLs that can be found as links (href html tag) page by page. Therefore, even if you start at a deeply nested URL, it will still search for pages of this domain. Webshop Scraper will simply start searching at the provided URL and move on from there. Hence, in order to get a large number of searchable links, it is beneficial if you provide the sitemap page of the domain you are targeting. This page generally provides the largest number of links and a comprehensive overview of the domain.

## Software Architecture

Webshop Scraper is designed in modular and object-based architecture. It consists of the `main.py` file, `constants.py`, `scraper.py`, and the `/gui` folder containing `main_gui.py` and `adv_settings.py`.

### main.py

This file is the center of the application. It initiates the program by initializing the main Tkinter window, importing and loading the ScraperApp class. Therefore, it imports the module tkinter, which is the most widely used module for GUI applications in Python.

### constants.py

In this file we store the constants of Webshop Scraper. It contains the `GENERAL_BLACKLIST`, which is always respected (unchangeable in the GUI). Here we exclude links to facebook-profiles or mailto links. Furthermore, the `DEFAULT_BLACKLIST` is stored here, which is a common list of excluded URL components, which however might be specific to certain target website and therefore can be modified in the advanced settings GUI.

### gui/main_gui.py

Defines the prototype of the `ScraperApp` class, which contains the general look and behavior of the GUI. Upon init, this method creates all the buttons and input fields and shows them in a GUI window. I choose a grid structure to be able to put input field and their labels next to each other and align them in an appealing way.
Furthermore, init initialize the Scraper object from scraper.py with the actual scraping logic in it, prepares an advanced settings extension of the GUI, a logger for the GUI and an extended logger into a .log file.

Using the `set_html_mode` and `set_json_mode methods`, it is possible to toggle between those two modes and have the interface look match the required input for the respective mode.

The `show_prod_desc_field` and `hide_prod_desc_field` methods are used to show and hide (`grid_forget`) the additional fields which are only useful in the HTML mode. All those input fields are placed into a tkinter Frame to show and hide (`grid_forget`) them conveniently.

The `start_scraping` collects the values of all input fields and hands them off to the Scraper class, which will be started on a different thread using the threading module.

The `stop_scraping` method stops the current scraping job. It joins back the additional scraping thread and sets a flag to coordinate this commands.

In order to visualize the current progress of Webshop Scraper I have used a `scrolledtext` from the `tkinter` module. It is prompting information about the current scraping job, such as how many pages in total have been visited, and how many pages are still queuing, and how many products have been found. I decided to put all this into the GUI, to make Webshop Scraper usable without a terminal.

Since the speed of the program overloaded the scrolledtext in an earlier version. I have built a more robust and code-vise complex solution. All messages to be logged, will first be appended using the put method to the log_queue, which is a Queue object, both from the queue module. Every 0.3 seconds the `process_log_queue` will then append the next message from the queue object to the scrolledtext. This provides thread-safe logging.

The `show_adv_settings` settings initiates a secondary GUI window from `gui/adv_settings.py` containing more advanced settings. It takes the adv_settings dict as an argument to exchange the settings between those two GUIs.

Furthermore, there is a listener on closing the advanced settings window that calls the `save_and_close_adv_settings` method, which feeds back the advanced settings to the adv_settings dict of the main GUI, so that the settings aren’t lost upon closing the window.

The method `setup_logger` is been called during the init of the `ScrapperApp`. It initiates a `log_queue` which will contain an extended log containing each found and visited URL. The method will save this log to a `.log-file` to the desktop of the current user.

`log` is followingly the method which inserts new logs into the `.log-file`.

`on_closing` is a method that’s been called from a listener on closing the main GUI. In case there is a running scrap job, it asks the user to confirm termination and if so, it stops the scraping before closing the GUI.

### gui/adv_settings.py

This file contains the design and logic of the advanced settings secondary GUI window.
In init we create a new tkinter window, with the blacklist input field and the Import/Export buttons. It fills the blacklist with either, if previously already opened and modified, the blacklist of this instance or the default blacklist from `constants.py`. There are also two sub-methods integrated, `show_tooltip` and `hide_toolbar`, to show and hide the explanation of how to correctly enter blacklist items.

The `export_settings` method collects all settings, also the ones from the main GUI, into a nested dict and allows the user to store them to a `.json-file`.

The `import_settings` method allows the user then to select a `.json-file` and import the complete settings of a prior export.

### scraper.py

This file contains the actual scrapping logic, which is all build into the Scraper class.
Upon init, only the class variables are defined. The variables will then be filled by the `ScrapperApp` (`gui/main_gui.py`) which also inits this class.

The `start_scraping` method is been called by the ScrapperApp.start_scraping. This method is an additional layer to prepare the input data for scrapping. It could be omitted, but I decided to integrate it to provide an opportunity to alter the settings inside the Scraper class before starting the actual job.

The `stop_scraping` method simply sets a flag which will interrupt the scrapping job in a clean way after completing the current loop of the job. It will be called from the ScrapperApp.stop_scraping function upon clicking the button in the GUI or after the entire job has been finished.

The `scrape_task` is the brain of the Webshop Scraper. First, it extracts the settings for the scrape task, it checks the validity of the provided URL, it start documenting the job in both log outputs, creates a new csv-file using the csv module and finally loops over the dict of URLs `to_visit` (which initially only contains the provided `start_url`) until all URLs `to_visit` have been visited or the `stop_flag` has been set.

In this while-loop it pops of the last element of the dict of URLs to visit, it checks whether it has been visited before, it visits the URL using the `requests` module parses the html using the `BeautifulSoup` module.

This HTML content then is send to the method `extract_product_info` (if the URL contains the Special Product URL Identifier or it is empty) and to `get_all_links`. If `extract_product_info` successfully returns a products property, they will be stored into the `csv-file`. Any links `get_all_links` returns will be subtracted by the already visited ones and then added to the URLs `to_visit`.

`extract_product_info` is the method which checks the html content for product data. The mode is either `json` which lets this method extract all schema markup data of the type Product or html. In the latter one the `find_element` method gets called on every property of a product. This method then returns the product properties to the `scrape_task` method.

`find_element` extracts the specific product property from the provided html content. If a `class_name` of the specific property has been provided, it will try to find the content of a HTML element with this class, if not it will try to find the corresponding `itemprop` tag. Furthermore, there is some additional logic for specific properties such as the image or description one, which need slightly different handling.

`get_all_links` receives an HTML content and will search though it for any links (`a` tags). It parses and normalizes any found URLs and checks whether any blacklist criteria are appliable. It then also searches for nested links by using `find_all` on any `div`, `nav`, `ul`, `li` and `span` to look for links again inside them. The set of new links has then been returned to the `scrape_task` method.

`is_valid_url` is a simple method that helps the `scrape_task` method to validate the user input `start_url`.

`str_to_array_by_linebrake` method converts the blacklist separated by line breaks from the GUI to an array for the `scrape_task` method.

## Showcases

### Used to build [garden-shop.at](https://www.garden-shop.at/)
