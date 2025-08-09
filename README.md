# Advanced-Twitter-X-Selenium-Scraper
A robust Selenium-based scraper for Twitter (X.com) that logs in with real credentials, navigates to the “Latest” tab for a given search term, scrolls through tweets, and extracts complete tweet details including author info, timestamp, tweet text, engagement metrics (replies, reposts, likes, views), and tweet URLs. Saves data to CSV.
# Advanced Twitter/X Selenium Scraper

A robust Python Selenium-based scraper for **Twitter (X.com)** that:
- Logs in with your actual Twitter/X credentials
- Searches for any keyword
- Navigates to the "Latest" tab
- Scrolls through results and scrapes tweets
- Extracts:
  - Tweet ID
  - Author name
  - Username
  - Tweet text
  - Timestamp
  - Replies, Reposts, Likes, Views
  - Tweet URL
- Saves data to CSV for later analysis

## 🚀 Features
- **Real login** (bypasses guest limitations)
- **Randomized delays** to reduce bot detection
- **Configurable** scroll count and max tweets per run
- **Engagement metrics parsing** using regex
- **CSV export** with UTF-8 encoding

## 📦 Requirements
- Python 3.8+
- Microsoft Edge Browser
- Microsoft Edge WebDriver (matching your browser version)

Install dependencies:
```bash
pip install selenium pandas
⚙️ Usage
Clone this repository:

bash
Copy
Edit
git clone https://github.com/YOUR_USERNAME/twitter-x-selenium-scraper.git
cd twitter-x-selenium-scraper
Run the script:

bash
Copy
Edit
python scraper.py
Enter:

Twitter email/username

Password

Search term (default is "bitcoin")

The scraper will:

Log in

Search the keyword

Click the “Latest” tab

Scroll and scrape tweets

Save results to tweets_full_data_<keyword>.csv

⚠️ Disclaimer
This project is for educational purposes only.

Scraping Twitter/X may violate their Terms of Service — use responsibly.

Avoid excessive requests to prevent account suspension.

📄 Example Output
CSV columns:

sql
Copy
Edit
TweetID,AuthorName,Username,TweetText,Timestamp,Replies,Retweets,Likes,Views,TweetURL
