import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urlunparse
import threading
import json
import os
import csv
import logging
from constants import GENERAL_BLACKLIST

class Scraper:
    def __init__(self):
        self.stop_flag = threading.Event()
        self.settings = {}
        self.adv_settings = {}

    def start_scraping(self):
        self.stop_flag.clear()

        # reformat any settings to be used
        self.adv_settings["formatted_blacklist"] = self.str_to_array_by_linebrake(self.adv_settings["blacklist"])

        # Perform the scraping task using the extracted settings
        self.scrape_task()

    def stop_scraping(self):
        self.stop_flag.set()

    def scrape_task(self):

        # Extract settings for the scrape task
        start_url = self.settings.get("url")
        mode = self.settings.get("mode")
        product_identifier = self.settings.get("product_identifier")
        prod_els = self.settings.get("prod_els")
        log_queue = self.settings.get("log_queue")

        if not self.is_valid_url(start_url):
            log_queue.put("Invalid URL. Please provide a valid URL.")
            return
        
        log_queue.put("Starting scraping ...")
        logging.info("Starting scraping...")

        domain = urlparse(start_url).netloc
        visited = set()
        to_visit = {start_url}
        product_qty = 0

        # Prepare the CSV file on the user's desktop
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        csv_file_path = os.path.join(desktop_path, "scraped_products.csv")

        with open(csv_file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=['name', 'image', 'desc', 'sku', 'price', 'url'])
            writer.writeheader()

            while to_visit and not self.stop_flag.is_set():
                current_url = to_visit.pop()

                if current_url in visited:
                    continue

                logging.info(f"Crawling: {current_url}")
                visited.add(current_url)

                # actually visit the site
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"}

                try:
                    response = requests.get(current_url, headers=headers, timeout=10)
                    soup = BeautifulSoup(response.text, 'html.parser')

                    if response.status_code == 403:
                        logging.error("The websites forbids the access: 403 error. See extract_product_info function.")
                        log_queue.put("The websites forbids the access: 403 error. See extract_product_info function.")
                        return None
                
                except Exception as e:
                    logging.error(f"Error while scraping {current_url}: {e}")
                    log_queue.put(f"Error while scraping {current_url}: {e}")
                    return None

                # Get product info from the current page
                try:
                    if product_identifier in current_url:
                        product_info = self.extract_product_info(current_url, mode, prod_els, log_queue, soup)
                        if product_info:
                            writer.writerow(product_info)
                            product_qty += 1

                except Exception as e:
                    logging.error(f"Error while processing {current_url}: {e}")
                    log_queue.put(f"Error while processing {current_url}: {e}")
                    return None

                # Find more links to visit
                try:
                    new_links = self.get_all_links(current_url, domain, log_queue, soup)
                    to_visit.update(new_links - visited)
                    log_queue.put(f"Visited: {len(visited)} | Queuing: {len(to_visit)} | product{"" if product_qty == 1 else "s"}: {product_qty}.")

                except Exception as e:
                    logging.error(f"Error extracting links from {current_url}: {e}")
                    log_queue.put(f"Error extracting links from {current_url}: {e}")

            logging.info(f"Scraping job finished.")
            log_queue.put(f"Scraping job finished.")
            self.stop_scraping()

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

        try:
            # First, get all <a> tags directly (as in original code)
            for a_tag in soup.find_all("a", href=True):
                relative_link = a_tag['href']
                full_link = urljoin(base_url, relative_link)
                parsed_link = urlparse(full_link)

                normalized_link = urlunparse(parsed_link._replace(fragment=""))

                if (
                    domain in normalized_link 
                    and not any(blacklisted_url in normalized_link for blacklisted_url in self.adv_settings["formatted_blacklist"]) 
                    and not any(general_url in normalized_link for general_url in GENERAL_BLACKLIST)
                ):
                    links.add(normalized_link)
                    logging.info(f"Link found: {normalized_link}")
            
            # Look deeper into nested divs or other elements if necessary
            for div in soup.find_all(['div', 'nav', 'ul', 'li', 'span']):
                nested_a_tags = div.find_all("a", href=True)
                for nested_a_tag in nested_a_tags:

                    relative_link = nested_a_tag['href']
                    full_link = urljoin(base_url, relative_link)
                    parsed_link = urlparse(full_link)

                    normalized_link = urlunparse(parsed_link._replace(fragment=""))
                    
                    if domain in normalized_link and not any(blacklisted_url in normalized_link for blacklisted_url in self.adv_settings["formatted_blacklist"]):
                        links.add(normalized_link)
                        logging.info(f"Nested link found: {normalized_link}")
                        if len(normalized_link) > 200: # for testing only
                            print(f"{url} Nested link found: {normalized_link}")

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