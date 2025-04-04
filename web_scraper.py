import pandas as pd
import os
import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import time
import re
from bs4 import Tag

class WebScraper:

    def __init__(self, item_df):
        # intialise df variables
        self._data_image_key = item_df["data-image-key"]
        self._WIKI_URL = item_df["URL"]
        self._levels = item_df["levels"]
        self._regex = item_df['regex']
        self._no_regex = not(self._regex)

        # create directory string for directory path to be created
        self._BASE_DIR = "items\\" + self._data_image_key

        # create directory path
        os.makedirs(self._BASE_DIR, exist_ok=True)

        # Headers to mimic a real browser request
        self._HEADERS = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }


    def _remove_duplicate_images(self, img_elements):
        """
        Removes duplicate image elements based on their 'data-image-key' attribute using regex masks.

        :param img_elements: List of image elements.
        :return: List of unique image elements.
        """
        unique_imgs = list({img['data-image-key'].strip(): img for img in img_elements if isinstance(img, Tag) and img.has_attr('data-image-key')}.values())

        return unique_imgs
    

    def _filter_images(self, img_elements, level):
        """
        Filters <img> elements to only include those images from that particular building level.

        :param img_elements: List of image elements.
        :param level: Level that is wanted to be retrieved.
        :return: List of image elements that match that particular level.
        """
        if self._no_regex: 
            pattern = re.compile(f"{self._data_image_key}{level}(-[1-5])?\.png")
        else:
            pattern = re.compile(f"{self._data_image_key}{level}(-[1-5])?{self._regex}\.png")

        return [
            img for img in img_elements 
            if img.has_attr("data-image-key") and pattern.match(img["data-image-key"])
        ]


    def _fetch_item_images(self):
        """
        Fetches images of all levels of a particular building and filters it into levels.

        :return: A singular URL to the download_image function for it to be downloaded and saved to the directory
        """
        response = requests.get(self._WIKI_URL, headers=self._HEADERS)
        if response.status_code != 200:
            print("Failed to fetch the Wiki page.")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
    
        if self._no_regex:   
            gallery = soup.find_all("img", attrs={"data-image-key": re.compile(f"{self._data_image_key}\d+(-[1-5])?\.png")})
        else:
            gallery = soup.find_all("img", attrs={"data-image-key": re.compile(f"{self._data_image_key}\d+(-[1-5])?{self._regex}\.png")})

        if not(gallery):
            print(f"❌ Failed to find {self._data_image_key}!")
            return

        for item in range(self._levels):
            item_level = item + 1

            # Find all images for item
            item_images_filtered = self._filter_images(gallery, item_level)

            item_images_filtered = self._remove_duplicate_images(item_images_filtered)

            # check filtered items list isn't empty
            if not(item_images_filtered):
                print(f"❌ No {self._data_image_key} found!")

            item_num = 1

            for figure in item_images_filtered:

                # create path for checking whether image exists
                if self._no_regex:
                    path_join = os.path.join(self._BASE_DIR,f"{self._data_image_key}_{item_level}", f"{self._data_image_key}_{item_level}_{item_num}.png")
                else:
                    path_join = os.path.join(self._BASE_DIR,f"{self._data_image_key}_{item_level}{self._regex}", f"{self._data_image_key}_{item_level}_{item_num}{self._regex}.png")

                # check whether image already exists
                if os.path.isfile(path_join):
                    print(f"✅ Skipped {self._data_image_key}_{item_level}_{item_num} due to the image already existing")
                    # increment item number and then skip over item
                    item_num += 1
                    continue

                if figure and "data-src" in figure.attrs:
                    img_url = figure["data-src"]
                    
                    img_url = img_url.split("/revision")[0]  # Remove unnecessary URL parts
                    
                    self._download_image(img_url, item_level, item_num)

                item_num += 1


    def _download_image(self, img_url, level, item_num):
        """
        Downloads images from provided list of URLs.

        :param img_url: single URL of an image.
        :param level: the level of the given image
        :param item_num: the number of the current variation of the item
        :return: downloads the image to its file directory
        """
        if self._no_regex:
            folder_path = os.path.join(self._BASE_DIR, f"{self._data_image_key}_{level}")
        else:
            folder_path = os.path.join(self._BASE_DIR, f"{self._data_image_key}_{level}{self._regex}")
        os.makedirs(folder_path, exist_ok=True)

        try:
            response = requests.get(img_url, stream=True)
            response.raise_for_status()

            image = Image.open(BytesIO(response.content))
            image_format = image.format.lower()
            if not self._regex:   
                image_path = os.path.join(folder_path, f"{self._data_image_key}_{level}_{item_num}.{image_format}")
            else:
                image_path = os.path.join(folder_path, f"{self._data_image_key}_{level}_{item_num}{self._regex}.{image_format}")

            image.save(image_path)
            print(f"✅ Saved: {image_path}")

            time.sleep(1)  # Avoid hitting the server too fast
        except Exception as e:
            print(f"❌ Failed to download {self._data_image_key}_{level}_{item_num} image: {e}")
            


def scrape_item_images(item_df: pd.DataFrame):
    """
    Executes the higher level function of web scraping and downloads

    :param item_df: df of all the items in which web scraping needs to be applied on,
    containing: URL, data-image-key and levels
    :returns: Directory saved with all images of items from item_df
    """
    for index, row in item_df.iterrows():
        web_scraper = WebScraper(row)

        print(f"🔎 Fetching and donwloading {web_scraper._data_image_key} images...")
        web_scraper._fetch_item_images()

    print(f"✅ All defensive building images downloaded successfully!")
    