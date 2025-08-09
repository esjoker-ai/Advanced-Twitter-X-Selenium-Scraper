from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import time
import pandas as pd
from getpass import getpass
import os
import random # For randomized delays
import re # For regex parsing of engagement metrics

# --- Setup ---
EMAIL = input("Enter your Twitter email or username: ")
PASSWORD = getpass("Enter your Twitter password (hidden): ")
SEARCH_TERM = input("Enter search term (e.g., bitcoin): ").strip() or "bitcoin"
NUM_SCROLLS = 1000 # Increased, but watch for detection. Start with 5-10 for testing.
SCROLL_PAUSE_TIME_MIN = 2 # Minimum pause time
SCROLL_PAUSE_TIME_MAX = 4 # Maximum pause time
MAX_TWEETS_PER_RUN = 10000

# --- Environment variable to tell Selenium Manager to ignore proxy ---
os.environ["NO_PROXY"] = "msedgedriver.azureedge.net,localhost,127.0.0.1"
os.environ["no_proxy"] = "msedgedriver.azureedge.net,localhost,127.0.0.1"

options = Options()
options.add_argument("--start-maximized")
# UNCOMMENT THE NEXT LINE TO SEE THE BROWSER AND DEBUG!
# options.add_argument("--headless") # Comment this line out while debugging!
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("--no-proxy-server") # Explicitly tell browser not to use proxy

service = Service()
driver = webdriver.Edge(service=service, options=options)

# --- Login to Twitter ---
print("Attempting to log in...")
driver.get("https://twitter.com/login")
wait = WebDriverWait(driver, 20)

try:
    # First login field (could be email or username)
    user_field = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@autocomplete='username' or @name='text' or @data-testid='ocf-text-input']")))
    user_field.send_keys(EMAIL)
    user_field.send_keys(Keys.ENTER)
    time.sleep(random.uniform(2, 4)) # Randomized pause

    # Handle potential "confirm your email/phone" or "Enter your username/email" step
    # This element often has autocomplete='username' if it's asking for a confirmation email/phone
    try:
        confirm_field = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@autocomplete='username' and @name='text']")))
        print("Confirmation/second username step detected, entering email/username again...")
        confirm_field.send_keys(EMAIL)
        confirm_field.send_keys(Keys.ENTER)
        time.sleep(random.uniform(2, 4))
    except TimeoutException:
        print("No confirmation/second username step detected or skipped.")
        pass

    # Password field
    pass_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))
    pass_field.send_keys(PASSWORD)
    pass_field.send_keys(Keys.ENTER)
    
    # Wait for the URL to change to the home page or a known post-login URL
    wait.until(EC.any_of(
        EC.url_contains("home"),
        EC.url_contains("feed"),
        EC.url_contains("settings") # Sometimes redirects to settings if login is successful but profile needs completion
    ))
    print("Successfully logged in.")
    time.sleep(random.uniform(4, 7)) # Longer pause for full page load
except Exception as e:
    print(f"Login failed: {e}")
    driver.quit()
    exit()

# --- Search Keyword ---
from datetime import datetime, timedelta  # <-- Add this at the top

# --- Search Keyword ---
print(f"Searching for '{SEARCH_TERM}'...")
try:
    # Try finding the search input by data-testid first, then aria-label
    search_input_xpath = '//input[@data-testid="SearchBox_Search_Input"]'
    search_input = wait.until(EC.presence_of_element_located((By.XPATH, search_input_xpath)))

    # === Dynamically calculate date range ===
    today = datetime.today().date()
    since_date = (today - timedelta(days=5)).isoformat()
    until_date = today.isoformat()
    search_query = f"{SEARCH_TERM}"

    # Enter query
    search_input.send_keys(search_query)
    search_input.send_keys(Keys.ENTER)

    # Wait for the URL to contain the search term, or for search results to appear
    wait.until(EC.any_of(
        EC.url_contains("search?q="),
        EC.presence_of_element_located((By.XPATH, '//article[@role="article"]'))
    ))
    print("Search results loaded.")
    time.sleep(random.uniform(3, 5))
except TimeoutException:
    print("Could not find search input or navigate to search results.")
    driver.quit()
    exit()


# --- Click "Latest" Tab ---
print("Clicking 'Latest' tab...")
try:
    # Look for the 'Latest' tab by its href attribute, which usually contains 'f=live' or similar
    # The text "Latest" itself is often inside a span.
    latest_tab_xpath = '//a[contains(@href, "f=live")] | //span[text()="Latest"]/ancestor::a'
    latest_tab = wait.until(EC.element_to_be_clickable((By.XPATH, latest_tab_xpath)))
    driver.execute_script("arguments[0].click();", latest_tab) # Use JS click for more reliability
    
    # Wait for URL to update to latest tab or for content to reload
    wait.until(EC.url_contains("f=live"))
    print("Switched to 'Latest' tab.")
    time.sleep(random.uniform(3, 5))
except TimeoutException:
    print("Could not find or click 'Latest' tab. Proceeding without it, might get Top tweets.")
    pass

# --- Scroll and Scrape Tweets ---
tweet_data = []
scraped_tweet_ids = set()

print("Starting to scrape tweets...")
last_height = driver.execute_script("return document.body.scrollHeight")
for i in range(NUM_SCROLLS):
    print(f"Scrolling {i+1}/{NUM_SCROLLS}...")
    
    # Give the page a moment to render new content before finding elements
    time.sleep(random.uniform(SCROLL_PAUSE_TIME_MIN, SCROLL_PAUSE_TIME_MAX))
    
    cards = driver.find_elements(By.XPATH, '//article[@role="article"]')
    print(f"Found {len(cards)} potential tweet cards on screen.")

    if not cards:
        print("No tweet cards found on the current view. This might indicate an XPath issue or no content.")
        break # Exit if no cards are found at all

    for j, card in enumerate(cards):
        try:
            # 1. Tweet Link and ID
            tweet_link_element = card.find_element(By.XPATH, ".//a[contains(@href, '/status/')]")
            tweet_url = tweet_link_element.get_attribute("href")
            tweet_id = tweet_url.split('/')[-1]

            if tweet_id not in scraped_tweet_ids:
                # 2. Author Name (display name)
                author_name = "N/A"
                try:
                    # Look for the span that is not the username, within data-testid="User-Name"
                    # This XPath tries to get the bold name, usually the first span within User-Name that doesn't start with '@'
                    author_name_element = card.find_element(By.XPATH, ".//div[@data-testid='User-Name']//span[not(starts-with(text(),'@')) and string-length(text()) > 0 and not(contains(text(), '·'))][1]")
                    author_name = author_name_element.text.strip()
                except NoSuchElementException:
                    # print(f"  DEBUG: Could not find AuthorName for tweet {tweet_id}") # Too verbose, uncomment for deep debug
                    pass
                except StaleElementReferenceException:
                    print(f"  DEBUG: StaleElementReferenceException for AuthorName in tweet {tweet_id}")
                    continue # Skip this tweet if it went stale

                # 3. Username (handle)
                username = "N/A"
                try:
                    username_element = card.find_element(By.XPATH, ".//div[@data-testid='User-Name']//span[starts-with(text(),'@')]")
                    username = username_element.text.strip()
                except NoSuchElementException:
                    # print(f"  DEBUG: Could not find Username for tweet {tweet_id}") # Too verbose
                    pass
                except StaleElementReferenceException:
                    print(f"  DEBUG: StaleElementReferenceException for Username in tweet {tweet_id}")
                    continue

                # 4. Tweet Text
                full_tweet_text = "N/A"
                try:
                    tweet_text_element = card.find_element(By.XPATH, ".//div[@data-testid='tweetText']")
                    full_tweet_text = tweet_text_element.text.strip()
                except NoSuchElementException:
                    # Sometimes tweets are just images or retweets without direct text in tweetText
                    # print(f"  DEBUG: Could not find TweetText for tweet {tweet_id}") # Too verbose
                    pass
                except StaleElementReferenceException:
                    print(f"  DEBUG: StaleElementReferenceException for TweetText in tweet {tweet_id}")
                    continue

                # 5. Timestamp
                timestamp = "N/A"
                try:
                    timestamp_element = card.find_element(By.XPATH, ".//time")
                    timestamp = timestamp_element.get_attribute("datetime")
                except NoSuchElementException:
                    # print(f"  DEBUG: Could not find Timestamp for tweet {tweet_id}") # Too verbose
                    pass
                except StaleElementReferenceException:
                    print(f"  DEBUG: StaleElementReferenceException for Timestamp in tweet {tweet_id}")
                    continue

                # --- Enhanced Engagement Metrics Extraction ---
                replies = 0
                retweets = 0 # Renamed to 'reposts' on X.com
                likes = 0
                views = "N/A" # Default to N/A
                
                # Attempt to find the element that contains all engagement metrics in its aria-label
                # This XPath needs careful verification on the live site.
                # It's often a div with role="group" or a specific data-testid that combines these.
                # Based on the sample, it's likely a div with an aria-label like "X replies, Y reposts, Z likes..."
                # We'll look for a div containing "reply", "retweet", "like" data-testids as descendants.
                
                # A common parent for all engagement buttons is often a div with data-testid="socialContext"
                # or a div containing all the 'reply', 'retweet', 'like' buttons.
                # Let's target a common parent element, then try to get the aria-label from within it.
                # Alternatively, search for the 'analyticsButton' which often has a comprehensive aria-label.
                
                # Attempt 1: Target the 'analyticsButton' as it often holds the comprehensive aria-label
                all_metrics_element_xpath = ".//div[@data-testid='analyticsButton']"
                
                try:
                    all_metrics_element = card.find_element(By.XPATH, all_metrics_element_xpath)
                    metrics_string = all_metrics_element.get_attribute("aria-label")
                    
                    if metrics_string:
                        # Parse the string to extract individual numbers
                        # Example string: "11882 replies, 9777 reposts, 66222 likes, 3696 bookmarks, 9039187 views"
                        # Or just "11882 replies, 9777 reposts, 66222 likes, 9039187" (where last number is views)
                        
                        # Initialize for parsing
                        parsed_replies = 0
                        parsed_reposts = 0
                        parsed_likes = 0
                        parsed_views_text = "N/A"

                        # Use regex to find numbers associated with labels
                        match_replies = re.search(r'(\d[\d,]*) replies', metrics_string)
                        if match_replies:
                            parsed_replies = int(match_replies.group(1).replace(',', ''))
                        
                        match_reposts = re.search(r'(\d[\d,]*) reposts', metrics_string) # Use 'reposts'
                        if match_reposts:
                            parsed_reposts = int(match_reposts.group(1).replace(',', ''))
                        
                        match_likes = re.search(r'(\d[\d,]*) likes', metrics_string)
                        if match_likes:
                            parsed_likes = int(match_likes.group(1).replace(',', ''))
                            
                        # Views parsing (can be tricky, look for "views" explicitly or largest number)
                        match_views = re.search(r'(\d[\d,]*) views', metrics_string)
                        if match_views:
                            parsed_views_text = match_views.group(1).replace(',', '')
                        else:
                            # Fallback: if "views" label isn't found, try to find the last (often largest) number
                            all_numbers_in_string = [int(num.replace(',', '')) for num in re.findall(r'(\d[\d,]*)', metrics_string)]
                            if all_numbers_in_string:
                                # The last number is often the view count if it's not explicitly labeled
                                # This is a heuristic, and might not always be correct (e.g., if bookmarks is last and larger)
                                # Consider if it's significantly larger than other counts
                                if len(all_numbers_in_string) > 0: # Ensure there's at least one number
                                    parsed_views_text = str(all_numbers_in_string[-1]) # Take the last number as a string

                        replies = parsed_replies
                        retweets = parsed_reposts # Use 'reposts' for consistency with X.com terminology
                        likes = parsed_likes
                        views = parsed_views_text
                        
                except NoSuchElementException:
                    # If analyticsButton not found, try to get individual counts directly from buttons
                    # This is a fallback if the comprehensive aria-label isn't available
                    try:
                        replies_elem = card.find_element(By.XPATH, ".//div[@data-testid='reply']//span[@data-testid='app-text-transition-container' or contains(@data-testid, 'count')]")
                        replies = int(replies_elem.text.strip().replace(',', '')) if replies_elem.text.strip() else 0
                    except (NoSuchElementException, ValueError): pass
                    
                    try:
                        reposts_elem = card.find_element(By.XPATH, ".//div[@data-testid='retweet']//span[@data-testid='app-text-transition-container' or contains(@data-testid, 'count')]")
                        retweets = int(reposts_elem.text.strip().replace(',', '')) if reposts_elem.text.strip() else 0
                    except (NoSuchElementException, ValueError): pass

                    try:
                        likes_elem = card.find_element(By.XPATH, ".//div[@data-testid='like']//span[@data-testid='app-text-transition-container' or contains(@data-testid, 'count')]")
                        likes = int(likes_elem.text.strip().replace(',', '')) if likes_elem.text.strip() else 0
                    except (NoSuchElementException, ValueError): pass
                    
                    try: # Try to get views from other common locations if analyticsButton wasn't found
                        views_elem = card.find_element(By.XPATH, ".//div[contains(@aria-label, 'views')]")
                        views = views_elem.get_attribute("aria-label").replace(" views", "").strip()
                    except NoSuchElementException: pass

                    print(f"  DEBUG: Could not find comprehensive metrics element for tweet {tweet_id}. Attempting individual counts.")
                except StaleElementReferenceException:
                    print(f"  DEBUG: StaleElementReferenceException for metrics in tweet {tweet_id}. Skipping metrics for this tweet.")
                    # Keep replies, retweets, likes as 0 and views as N/A
                except Exception as e:
                    print(f"  DEBUG: Error parsing metrics for tweet {tweet_id}: {e}")
                    # Keep replies, retweets, likes as 0 and views as N/A


                tweet_data.append({
                    "TweetID": tweet_id,
                    "AuthorName": author_name,
                    "Username": username,
                    "TweetText": full_tweet_text,
                    "Timestamp": timestamp,
                    "Replies": replies,
                    "Retweets": retweets, # This will now reflect 'reposts'
                    "Likes": likes,
                    "Views": views, # This will try to capture the actual views number or N/A
                    "TweetURL": tweet_url
                })
                scraped_tweet_ids.add(tweet_id)
                
                # Print a success message for a scraped tweet
                print(f"  Scraped tweet {tweet_id} by {username} - R:{replies}, RT:{retweets}, L:{likes}, V:{views} ({len(tweet_data)} total)")
            
            if len(tweet_data) >= MAX_TWEETS_PER_RUN:
                print(f"Reached maximum of {MAX_TWEETS_PER_RUN} tweets. Stopping scrape.")
                break
        except StaleElementReferenceException:
            # This happens if the element disappears from DOM while we're trying to interact with it
            print(f"  DEBUG: StaleElementReferenceException caught for card {j}. Skipping.")
            continue
        except NoSuchElementException as e:
            # This means one of the inner elements (like text, username) wasn't found in a card
            # print(f"  DEBUG: NoSuchElementException for card {j}: {e}") # Uncomment for more verbose debugging
            continue
        except Exception as e:
            print(f"  DEBUG: General error processing card {j}: {e}")
            continue
    
    if len(tweet_data) >= MAX_TWEETS_PER_RUN:
        break

    # Scroll down and wait
    current_scroll_position = driver.execute_script("return window.pageYOffset;")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(random.uniform(SCROLL_PAUSE_TIME_MIN, SCROLL_PAUSE_TIME_MAX))

    new_height = driver.execute_script("return document.body.scrollHeight")
    if new_height == last_height:
        print("No more new content loaded after scrolling. Reached end of available content or hit rate limit.")
        break
    last_height = new_height

driver.quit()

# --- Save to CSV ---
df = pd.DataFrame(tweet_data)
df.drop_duplicates(subset=['TweetID'], inplace=True)
df.to_csv(f"tweets_full_data_{SEARCH_TERM}.csv", index=False, encoding="utf-8-sig")
print(f"\n✅ Scraped {len(df)} unique tweets for '{SEARCH_TERM}' saved to 'tweets_full_data_{SEARCH_TERM}.csv'")