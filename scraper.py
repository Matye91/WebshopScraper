from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urlunparse
import threading
import json
import os
import csv
import logging
import asyncio
import aiohttp
from constants import GENERAL_BLACKLIST, SIMULTANEOUS_SCRAPS, RESPONSE_TIMEOUT, RESPONSE_RETRY, SPEED_TEST_MODE, SPEED_TEST_DURATION, EXCLUDED_EXTENSIONS
from threading import Timer
from datetime import datetime
import psutil
import time

class Scraper:
    def __init__(self):
        self.stop_flag = asyncio.Event()
        self.settings = {}
        self.adv_settings = {}
        self.product_qty = 0

        if SPEED_TEST_MODE:
            self.average_cpu_usage = 0
            self.max_memory_usage = 0

    async def fetch(self, session, url, headers, log_queue, retries=RESPONSE_RETRY, initial_timeout=RESPONSE_TIMEOUT):
        """ Asynchronous HTTP GET request with retries and exponential backoff for timeouts """
        for attempt in range(1, retries + 1):
            try:
                async with session.get(url, headers=headers, timeout=initial_timeout) as response:
                    if response.status == 403:
                        log_queue.put(f"Access denied: 403 Forbidden for {url}")
                        logging.error(f"Access denied: 403 Forbidden for {url}")
                        return None
                    elif response.status != 200:
                        log_queue.put(f"Non-200 status code {response.status} ({response.reason}) for {url}")
                        logging.error(f"Non-200 status code {response.status} ({response.reason}) for {url}")
                        return None
                    return await response.text()
            
            except asyncio.TimeoutError:
                log_queue.put(f"Timeout error for {url} on attempt {attempt}/{retries}")
                logging.error(f"Timeout error for {url} on attempt {attempt}/{retries}")
                if attempt < retries:
                    # Wait before retrying, with exponential backoff
                    backoff_time = 2 ** (attempt - 1)
                    await asyncio.sleep(backoff_time)
                else:
                    log_queue.put(f"Failed to fetch {url} after {retries} attempts due to timeout.")
                    logging.error(f"Failed to fetch {url} after {retries} attempts due to timeout.")
                    return None

            except aiohttp.ClientConnectionError as e:
                log_queue.put(f"Connection error for {url}: {e}")
                logging.error(f"Connection error for {url}: {e}")
                return None

            except Exception as e:
                log_queue.put(f"Unexpected error fetching {url}: {e.__class__.__name__} - {e}")
                logging.error(f"Unexpected error fetching {url}: {e.__class__.__name__} - {e}")
                return None

    async def start_scraping(self):
        self.stop_flag.clear()

        log_queue = self.settings.get("log_queue")

        # Prepare the CSV file path
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        csv_file_path = os.path.join(desktop_path, "scraped_products.csv")

        if SPEED_TEST_MODE:
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            print(f"{current_time}: Timer started")
            t = Timer(SPEED_TEST_DURATION, self.stop_flag.set)
            t.start()
            monitoring_thread = threading.Thread(target=self.monitor)
            monitoring_thread.daemon = True
            monitoring_thread.start()

        # reformat any settings to be used
        self.adv_settings["formatted_blacklist"] = self.str_to_array_by_linebrake(self.adv_settings["blacklist"])

        # Open session for aiohttp and initiate the scraping process
        async with aiohttp.ClientSession() as session:
            with open(csv_file_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=['name', 'image', 'desc', 'sku', 'price', 'url'])
                writer.writeheader()

                await self.scrape_task(session, writer, log_queue)

    def stop_scraping(self):
        if SPEED_TEST_MODE:
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            print(f"{current_time}: Timer stopped")
            time.sleep(0.5)

            # Print the max CPU and memory usage
            self.average_cpu_usage = round(self.average_cpu_usage, 1)
            self.max_memory_usage = round(self.max_memory_usage, 0)
            print(f"Average CPU Usage: {self.average_cpu_usage}%")
            print(f"Max Memory Usage: {self.max_memory_usage} MB")

        self.stop_flag.set()

    async def scrape_task(self, session, writer, log_queue):
        """ Main asynchronous scraping task """
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"}
        start_url = self.settings.get("url")
        mode = self.settings.get("mode")
        product_identifier = self.settings.get("product_identifier")
        prod_els = self.settings.get("prod_els")

        if not self.is_valid_url(start_url):
            log_queue.put("Invalid URL. Please provide a valid URL.")
            return
        
        log_queue.put("Starting scraping ...")
        logging.info("Starting scraping...")

        # domain = urlparse(start_url).netloc where does this go?
        to_visit = {start_url}
        visited = set()
        tasks = []

        while to_visit or tasks:
            # If stop_flag is set, break out of the loop
            if self.stop_flag.is_set():
                break

            if to_visit:
                current_url = to_visit.pop()
                if current_url not in visited:
                    # logging.info(f"Crawling: {current_url}")
                    visited.add(current_url)
                    task = self.process_url(session, current_url, headers, visited, to_visit, product_identifier, mode, prod_els, writer, log_queue)
                    tasks.append(task)

            # Limit the number of concurrent tasks
            if len(tasks) >= SIMULTANEOUS_SCRAPS or not to_visit:
                await asyncio.gather(*tasks)
                tasks = []  # Reset task list after processing

        logging.info(f"Scraping job finished.")
        log_queue.put(f"Scraping job finished.")
        self.stop_scraping()

    async def process_url(self, session, url, headers, visited, to_visit, product_identifier, mode, prod_els, writer, log_queue):
        """ Process a single URL asynchronously """
        response_text = await self.fetch(session, url, headers, log_queue)
        if response_text is None:
            return

        soup = BeautifulSoup(response_text, 'lxml')

        # If the URL contains the product identifier, extract product info
        if product_identifier in url:
            product_info = self.extract_product_info(url, mode, prod_els, log_queue, soup)
            if product_info:
                writer.writerow(product_info)
                self.product_qty += 1

        # Find additional links to queue up for scraping
        new_links = self.get_all_links(url, urlparse(url).netloc, log_queue, soup)
        to_visit.update(new_links - visited)

        # console log
        log_queue.put(f"Visited: {len(visited)} | Queuing: {len(to_visit)} | product{"" if self.product_qty == 1 else "s"}: {self.product_qty}.")


    def extract_product_info(self, url, mode, prod_els, log_queue, soup):
        try:
            product_info = {}

            # Handle different modes: JSON-LD or HTML
            if mode == "json":
                schema_markups = soup.find_all("script", {"type": "application/ld+json"})
                for markup in schema_markups:
                    json_data = markup.string

                    try:
                        data = json.loads(json_data)

                        if data.get("@type") == "Product":
                            product_info['name'] = data.get("name", "")
                            image = data.get("image", "")
                            product_info['image'] = image[0] if isinstance(image, list) else image
                            product_info['desc'] = data.get("description", "")
                            product_info['sku'] = data.get("sku", "")
                            product_info['price'] = data.get("offers", {}).get("price", "").replace(".", ",")
                            product_info['url'] = data.get("offers", {}).get("url", url)
                            return product_info
                        
                    except json.JSONDecodeError as e:
                        logging.error(f"Error parsing JSON from {url}: {e}")
                        log_queue.put(f"Error parsing JSON from {url}: {e}")

            elif mode == "html":
                # For HTML mode, use the provided product element classes or default itemprops
                product_info['name'] = self.find_element(soup, prod_els.get('name'), 'name', log_queue)
                product_info['image'] = self.find_element(soup, prod_els.get('image'), 'image', log_queue)
                product_info['desc'] = self.find_element(soup, prod_els.get('desc'), 'description', log_queue)
                product_info['sku'] = self.find_element(soup, prod_els.get('sku'), 'sku', log_queue)
                product_info['price'] = self.find_element(soup, prod_els.get('price'), 'price', log_queue)
                product_info['url'] = url

                return product_info if any(product_info.values()) else None

        except Exception as e:
            logging.error(f"Error while scraping {url}: {e}")
            log_queue.put(f"Error while scraping {url}: {e}")
            return None

    def find_element(self, soup, class_name, itemprop_name, log_queue):
        # Helper method to find elements by class or itemprop.
        if class_name:
            tag = soup.find(class_=class_name)
        else:
            tag = soup.find(attrs={"itemprop": itemprop_name})

        if not tag:
            logging.error(f"{itemprop_name} not found using {'class' if class_name else 'itemprop'}.")
            log_queue.put(f"{itemprop_name} not found using {'class' if class_name else 'itemprop'}.")
            return f"No {itemprop_name} found."

        # handle special case for image
        if itemprop_name == "image":
            if class_name:
                image_tag = tag.find("img")
                if image_tag and "src" in image_tag.attrs:
                    return image_tag["src"]
                else:
                    error_msg = "No image found in parent element!"
                    logging.error(error_msg)
                    log_queue.put(error_msg)
                    return error_msg
            else:
                if "content" in tag.attrs:
                    return tag["content"]
                if "src" in tag.attrs:
                    return tag["src"]
                else:
                    error_msg = "Image not found with itemprop."
                    logging.error(error_msg)
                    log_queue.put(error_msg)
                    return error_msg

        # handle special case for description in html format
        if itemprop_name == "description":
            if class_name:
                return str(tag)
            else:
                if tag.name == "meta":
                    return tag.get("content", "")
                # else default 
                
        # handle special case for price in html format
        if itemprop_name == "price":
            if not class_name:
                offer = soup.find(attrs={"itemprop": "offers", "itemscope": True})
                if offer:
                    if tag.name == "meta":
                        return tag.get("content", "").replace(".", ",")
                    else:
                        return tag.get_text(strip=True).replace(".", ",")
                else:
                    error_msg = "No itemprop offer found to get price from!"
                    logging.error(error_msg)
                    log_queue.put(error_msg)
                    return error_msg

        # handles default case
        if tag.name == "meta":
            return tag.get("content", "")
        else:
            return tag.get_text(strip=True)        

    def get_all_links(self, url, domain, log_queue, soup):
        links = set()

        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        def add_link(normalized_link):
            if (
                domain in normalized_link
                and not any(blacklisted_url in normalized_link for blacklisted_url in self.adv_settings["formatted_blacklist"])
                and not any(general_url in normalized_link for general_url in GENERAL_BLACKLIST)
                and not normalized_link.endswith(EXCLUDED_EXTENSIONS)
            ):
                links.add(normalized_link)
                # logging.info(f"Link found: {normalized_link}")

        try:
            # First, get all <a> tags directly (as in original code)
            for a_tag in soup.find_all("a", href=True):
                relative_link = a_tag['href']
                full_link = urljoin(base_url, relative_link)
                parsed_link = urlparse(full_link)
                normalized_link = urlunparse(parsed_link._replace(fragment=""))

                add_link(normalized_link)
            
            # Look deeper into nested divs or other elements if necessary
            for div in soup.find_all(['div', 'nav', 'ul', 'li', 'span']):
                nested_a_tags = div.find_all("a", href=True)
                for nested_a_tag in nested_a_tags:

                    relative_link = nested_a_tag['href']
                    full_link = urljoin(base_url, relative_link)
                    parsed_link = urlparse(full_link)
                    normalized_link = urlunparse(parsed_link._replace(fragment=""))

                    add_link(normalized_link)
                    
        except Exception as e:
            logging.error(f"Error while fetching links from {url}: {e}")
            log_queue.put(f"Error while fetching links from {url}: {e}")
        return links

    def is_valid_url(self, url):
        parsed = urlparse(url)
        return bool(parsed.scheme) and bool(parsed.netloc)
    
    def str_to_array_by_linebrake(self, str):
        array = [line.strip() for line in str.splitlines() if line.strip()]
        return array
    
    def monitor(self):
        process = psutil.Process()
        sample_count = 0
        cumulative_cpu_usage = 0
        while True:
            # Get current CPU and memory usage
            sample_count += 1
            cpu_usage = process.cpu_percent(interval=0.1)
            memory_usage = process.memory_info().rss / (1024 * 1024)  # in MB

            # Update max values if the current usage exceeds previous max
            cumulative_cpu_usage += cpu_usage
            self.average_cpu_usage = cumulative_cpu_usage / sample_count
            self.max_memory_usage = max(self.max_memory_usage, memory_usage)
            time.sleep(0.1)  # Adjust the interval as needed