# Create average faces from the images on a supplied URL

import pandas as pd
import matplotlib.pyplot as plt
from facer import facer
import time
import os
import sys
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import json
import matplotlib.pyplot as plt
import cv2
from skimage import io
from collections import Counter


class ImageScraper(object):
# https://stackoverflow.com/questions/52633697/selenium-python-how-to-capture-network-traffics-response

    def __init__(self, wait_time=1):
        # Run this once to start the Chrome instance
        caps = DesiredCapabilities.CHROME
        caps['loggingPrefs'] = {'performance': 'ALL'}
        self.driver = webdriver.Chrome(desired_capabilities=caps)
        self.browser_log = None
        self.responses = None
        self.wait_time = wait_time # seconds

        # Maximize the window
        kwargs = dict(x=0, y=0, width=1340, height=900)
        self.driver.set_window_rect(**kwargs)

    def _load_page(self, url):
        # Load the page
        self.driver.delete_all_cookies()
        self.driver.get(url)
        time.sleep(0.5)

        # Scroll to the bottom & top of page, prompting image loads
        elem = self.driver.find_element_by_tag_name("body")
        no_of_pagedowns = 8
        while no_of_pagedowns:
            elem.send_keys(Keys.PAGE_DOWN)
            time.sleep(0.5)
            no_of_pagedowns-=1
        time.sleep(0.3)
        for pos in 2 * ["0", "document.body.scrollHeight"]:
            scroll = f"window.scrollTo(0, {pos});"
            self.driver.execute_script(scroll)
            time.sleep(0.2)
        time.sleep(0.3)
        self.browser_log = self.driver.get_log('performance')
        return

    def _process_browser_log_entry(self, entry):
        return json.loads(entry['message'])['message']

    def get_all_image_links(self, url):
        """Returns a list of all image URLs on the page"""
        self._load_page(url)

        # Parse the network events
        events = [self._process_browser_log_entry(entry) for entry in self.browser_log]
        events = [event for event in events if 'Network.response' in event['method']]
        events = pd.DataFrame([event['params'] for event in events])
        responses = pd.DataFrame(events[events.type == "Image"]['response'].tolist())
        self.responses = responses
        return responses['url'].drop_duplicates()

    def close(self):
        print("Closing browser... ", end="")
        self.driver.quit()
        print("Done.")

    def __del__(self):
        self.close()


def shape_or_ratio_is_good(imshape, most_common_shape, most_common_ratio):
    get_ratio = lambda x: round(1000 * x[0] / x[1])
    return (imshape == most_common_shape) or (get_ratio(imshape) == most_common_ratio)

def mimeType_is_valid(mimeType):
    return mimeType.rsplit("/", 1)[-1].lower() in ["png", "jpg", "jpeg", "webp"]

def download_image_links(links, company):
    images = {}
    sizes, skips = [], []
    for n, image_url in enumerate(links):
        alt = f"{company}_image_{n:02.0f}"
        fp = image_url.rsplit(".", 1)[0] + ".jpg"
        try:
            image = io.imread(image_url)[..., ::-1]
            cv2.imwrite(fp, image)
        except Exception as e:
            print(f"Error while downloading image:\n\t{e}")
            skips.append(image_url)
            continue

        # Keep the image URL, image array, and image size
        images[alt] = [image_url, image]
        sizes.append(image.shape)
    return images, sizes, skips

def save_labeled_face_image(company, image):
    # Plot the image
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.imshow(image)

    # Add a title
    kwargs = {"fontsize": 20, "fontweight": "heavy", "color": "gray", "alpha":0.9}
    title = f"{company} average face\n(Corporate leadership)"
    ax.set_title(title, **kwargs)

    # Touch up the image
    ax.set(**{"xlabel": '', "ylabel": '', "xticks": [], "yticks": []})
    plt.tight_layout()
    kwargs = {'fontsize': 17, 'color': 'black', 'weight': 'heavy', 'alpha': 0.6, 'ha': 'right'}
    x, y = image.shape[:2]
    x, y = 0.98 * x, 0.97 * y
    ax.text(x, y, "@johnwmillr", **kwargs)

    # Save the image
    fp = os.path.join("one-off", "average_faces", f"average_face_{company}_labeled.png")
    fig.savefig(fp, dpi=300)
    return

def create_average_face(company, path_to_average_face_image=None):
    folder = f"./one-off/{company.replace(' ', '_')}/"
    print(f"Target folder: {folder}")
    images = facer.load_images(folder, verbose=True)
    if len(images) == 0:
        return

    # Detect landmarks for each face
    landmarks, faces = facer.detect_face_landmarks(images, verbose=True)

    # Use  the detected landmarks to create an average face
    if path_to_average_face_image:
        average_face = cv2.imread(path_to_average_face_image)[..., ::-1]
    else:
        fp = os.path.join("one-off", "average_faces", f"average_face_{company}.jpg")
        average_face = facer.create_average_face(faces, landmarks, output_file=fp, save_image=True)

    # Save a labeled version of the average face
    save_labeled_face_image(company, average_face)
    return

def main(company, url, skip_downloads=False, path_to_avg_face=None):
    t0 = time.time()
    print(f"\nCompany: {company}\n")

    if not skip_downloads or not path_to_avg_face:
        # Create the scraper instance, opening Chrome
        scraper = ImageScraper()

        # Download images
        company = company.replace(" ", "_")

        # Get a link to every image on the pank
        image_links = scraper.get_all_image_links(url)

        # Attempt to read each image
        images, sizes, skips = download_image_links(image_links, company)
        print(f"Downloaded {len(images)} images.")
        if len(images) == 0:
            print("Couldn't find any images on the website.")
            return False

        # What's the most common image shape and ratio?
        get_ratio = lambda x: round(1000 * x[0] / x[1])
        most_common_shape = Counter([s[:2] for s in sizes]).most_common(1)[0][0]
        most_common_ratio = Counter(list(map(get_ratio, sizes))).most_common(1)[0][0]

        # Create a company images folder if it doesn't already exist
        folder = f"./one-off/{company}"
        if not os.path.exists(folder):
            os.mkdir(folder)

        # Save all images, but note the ones with questionable ratios
        for label, (image_url, array) in images.items():
            if not shape_or_ratio_is_good(array.shape[:2], most_common_shape, most_common_ratio):
                label += "_bad_size"
            label += ".jpg"
            fp = os.path.join(folder, label)
            cv2.imwrite(fp, array)
        time.sleep(0.2)

        # Close the browser
        scraper.close()
        del(scraper)

    # Create the average face
    try:
        create_average_face(company, path_to_avg_face)
    except Exception as e:
        print(f"Error: {e}\nSkipping company.\n\n")
    msg = f"All done! Total time elapsed: {(time.time() - t0) / 60:.2f} minutes."
    print(msg)


if __name__ == "__main__":
    if len(sys.argv) not in  [3, 4]:
        print("\nMust supply a company name and URL.")
        print("Usage:\n\t$python3 facesOfFortune.py 'Apple' https://www.apple.com/leadership/\n")

    args = sys.argv[1:]
    if len(args) == 2:
        company, url = sys.argv[1:]
        skip_downloads = False
    else:
        company, url, skip_downloads = sys.argv[1:]
    main(company, url, skip_downloads)
