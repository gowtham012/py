import os
import csv
import time
import math
import multiprocessing
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

####################
# CONFIG
####################
LINKS_FILENAME = "found_links.txt"  # This file must exist (created in Phase 1)
CSV_FILENAME = "AllRecipes.csv"
NUM_PROCESSES = 4  # Adjust based on your CPU; more processes may be faster but require more resources.

####################
# LOCAL HEADLESS DRIVER
####################
def init_local_driver():
    """
    Initialize and return a local headless Chrome WebDriver.
    Ensure Chrome and matching ChromeDriver are installed on your system.
    """
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(5)
    driver.set_window_size(1920, 1080)
    return driver

####################
# HELPER METHODS
####################
def is_valid_recipe(driver):
    """
    Check if the current page has essential recipe elements:
      1) recipe_name (heading)
      2) recipe_description
      3) at least one image (recipe_image != "N/A")
      4) non-empty directions list
      5) non-empty ingredients list
    """
    try:
        heading = driver.find_element(By.CSS_SELECTOR, "h1.article-heading.text-headline-400")
        if not heading.is_displayed():
            return False

        desc = driver.find_element(By.CSS_SELECTOR, "p.article-subheading.text-body-100")
        if not desc.is_displayed():
            return False

        images = driver.find_elements(By.CSS_SELECTOR, "div.img-placeholder img.universal-image__image")
        if len(images) == 0:
            return False

        directions = driver.find_elements(By.CSS_SELECTOR, "ol.mntl-sc-block-group--OL li p:first-of-type")
        if len(directions) == 0:
            return False

        ingredients = driver.find_elements(By.CSS_SELECTOR, "ul.mm-recipes-structured-ingredients__list li")
        if len(ingredients) == 0:
            return False

        return True
    except:
        return False

def get_text(driver, by, selector, default="N/A", timeout=5):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )
        return element.text.strip()
    except:
        return default

def get_nutrition_values(driver, nutrient_name):
    try:
        element = driver.find_element(By.XPATH, f"//span[contains(text(), '{nutrient_name}')]/parent::td")
        weight_value = element.text.split()[-1]
        percent_value = element.find_element(By.XPATH, "following-sibling::td").text.strip()
        return weight_value, percent_value
    except:
        return ("N/A", "N/A")

####################
# SCRAPE FUNCTION (Worker)
####################
def scrape_link(args):
    """
    Each process calls this with (cat_name, url, recipe_id).
    It opens a local headless Chrome, scrapes the recipe, and returns a dict or None.
    Only recipes with all essential data (name, description, image, directions, ingredients) are considered valid.
    """
    cat_name, url, recipe_id = args
    driver = None
    try:
        driver = init_local_driver()
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

        if not is_valid_recipe(driver):
            print(f"[SKIP] Not a valid recipe: {url}")
            return None

        # Gather essential fields
        recipe_name = get_text(driver, By.CSS_SELECTOR, "h1.article-heading.text-headline-400")
        recipe_desc = get_text(driver, By.CSS_SELECTOR, "p.article-subheading.text-body-100")
        
        images = driver.find_elements(By.CSS_SELECTOR, "div.img-placeholder img.universal-image__image")
        if images:
            recipe_img = images[0].get_attribute("data-src")
            if recipe_img and "video" in recipe_img.lower() and len(images) > 1:
                recipe_img = images[1].get_attribute("data-src")
        else:
            recipe_img = "N/A"
        
        directions = [step.text for step in driver.find_elements(
            By.CSS_SELECTOR, "ol.mntl-sc-block-group--OL li p:first-of-type"
        )]
        ingredients = {
            i+1: ing.text for i, ing in enumerate(
                driver.find_elements(By.CSS_SELECTOR, "ul.mm-recipes-structured-ingredients__list li")
            )
        }

        # Check that essential fields are non-empty
        if (not recipe_name or recipe_name == "N/A" or
            not recipe_desc or recipe_desc == "N/A" or
            recipe_img == "N/A" or
            len(directions) == 0 or
            len(ingredients) == 0):
            print(f"[SKIP] Missing essential data for {url}")
            return None

        # Optional: Gather additional details
        prep_time = get_text(driver, By.XPATH, "//div[contains(text(), 'Prep Time:')]/following-sibling::div")
        cook_time = get_text(driver, By.XPATH, "//div[contains(text(), 'Cook Time:')]/following-sibling::div")
        chill_time = get_text(driver, By.XPATH, "//div[contains(text(), 'Chill Time:')]/following-sibling::div", default="N/A")
        total_time = get_text(driver, By.XPATH, "//div[contains(text(), 'Total Time:')]/following-sibling::div")
        servings = get_text(driver, By.XPATH, "//div[contains(text(), 'Servings:')]/following-sibling::div")
        calories_total = get_text(driver, By.XPATH, "//td[contains(@class, 'mm-recipes-nutrition-facts-summary__table-cell')]")

        try:
            show_label_button = driver.find_element(By.CSS_SELECTOR, ".mm-recipes-nutrition-facts-label__button")
            driver.execute_script("arguments[0].click();", show_label_button)
            time.sleep(1)
        except:
            pass

        record = {
            "recipe_id": recipe_id,
            "category_name": cat_name,
            "recipe_url": url,
            "recipe_name": recipe_name,
            "recipe_description": recipe_desc,
            "recipe_image": recipe_img,
            "directions": directions,
            "ingredients": ingredients,
            "preparation_time": prep_time,
            "cooking_time": cook_time,
            "chill_time": chill_time,
            "total_time": total_time,
            "serving_size": servings,
            "calories_total": calories_total,

            "total_fat_weight": get_nutrition_values(driver, "Total Fat")[0],
            "total_fat_percent": get_nutrition_values(driver, "Total Fat")[1],

            "saturated_fat_weight": get_nutrition_values(driver, "Saturated Fat")[0],
            "saturated_fat_percent": get_nutrition_values(driver, "Saturated Fat")[1],

            "cholesterol_weight": get_nutrition_values(driver, "Cholesterol")[0],
            "cholesterol_percent": get_nutrition_values(driver, "Cholesterol")[1],

            "sodium_weight": get_nutrition_values(driver, "Sodium")[0],
            "sodium_percent": get_nutrition_values(driver, "Sodium")[1],

            "total_carbohydrate_weight": get_nutrition_values(driver, "Total Carbohydrate")[0],
            "total_carbohydrate_percent": get_nutrition_values(driver, "Total Carbohydrate")[1],

            "dietary_fiber_weight": get_nutrition_values(driver, "Dietary Fiber")[0],
            "dietary_fiber_percent": get_nutrition_values(driver, "Dietary Fiber")[1],

            "sugar_weight": get_nutrition_values(driver, "Total Sugars")[0],
            "sugar_percent": get_nutrition_values(driver, "Total Sugars")[1],

            "protein_weight": get_nutrition_values(driver, "Protein")[0],
            "protein_percent": get_nutrition_values(driver, "Protein")[1],
        }

        print(f"[OK] ID {recipe_id} from '{cat_name}'")
        return record

    except Exception as e:
        print(f"[ERR] {url}: {e}")
        return None
    finally:
        if driver:
            driver.quit()

####################
# MAIN
####################
def main():
    """
    Phase 2 local code running in headless mode with parallel processes.
    Reads 'found_links.txt', scrapes each link, and writes results to 'AllRecipes.csv'.
    """
    if not os.path.isfile(LINKS_FILENAME):
        print(f"Error: '{LINKS_FILENAME}' not found. Did you complete Phase 1?")
        return

    start = time.time()

    # Load all lines from found_links.txt and create a list of tuples: (cat_name, url, recipe_id)
    links_data = []
    with open(LINKS_FILENAME, "r", encoding="utf-8") as lf:
        idx = 1
        for line in lf:
            line = line.strip()
            if not line:
                continue
            parts = line.split("|", maxsplit=1)
            if len(parts) < 2:
                continue
            cat_name = parts[0].strip()
            url = parts[1].strip()
            links_data.append((cat_name, url, idx))
            idx += 1

    print(f"Scraping {len(links_data)} total links with concurrency={NUM_PROCESSES} (headless).")

    # CSV setup
    fieldnames = [
        "recipe_id", "category_name", "recipe_url", "recipe_name", "recipe_description",
        "recipe_image", "directions", "ingredients", "preparation_time", "cooking_time",
        "chill_time", "total_time", "serving_size", "calories_total",
        "total_fat_weight", "total_fat_percent",
        "saturated_fat_weight", "saturated_fat_percent",
        "cholesterol_weight", "cholesterol_percent",
        "sodium_weight", "sodium_percent",
        "total_carbohydrate_weight", "total_carbohydrate_percent",
        "dietary_fiber_weight", "dietary_fiber_percent",
        "sugar_weight", "sugar_percent",
        "protein_weight", "protein_percent"
    ]
    file_exists = os.path.isfile(CSV_FILENAME)
    with open(CSV_FILENAME, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists or os.stat(CSV_FILENAME).st_size == 0:
            writer.writeheader()

        total_written = 0
        with multiprocessing.Pool(processes=NUM_PROCESSES) as pool:
            results_iter = pool.imap_unordered(scrape_link, links_data)
            for record in results_iter:
                if record is not None:
                    writer.writerow(record)
                    total_written += 1

    elapsed = time.time() - start
    print(f"\n[END] Wrote {total_written} valid recipes to '{CSV_FILENAME}' in {elapsed:.2f}s using concurrency={NUM_PROCESSES} (headless).")

if __name__ == "__main__":
    main()
