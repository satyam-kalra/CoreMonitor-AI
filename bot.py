import os
import smtplib
import yfinance as yf
import pandas as pd
import requests
import nltk
from email.mime.text import MIMEText
from datetime import datetime
from textblob import TextBlob

# --- 1. SETUP ---
# Download the 'brain' for the AI to understand English
try:
    nltk.data.find('tokenizers/punkt')
except:
    nltk.download('punkt', quiet=True)

# Get your keys from GitHub Settings
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")
MY_EMAIL = os.getenv("SENDER_EMAIL")
MY_PASS = os.getenv("SENDER_PASS")

# The 4 stocks we check EVERY day
WATCHLIST = ["AAPL", "NVDA", "TSLA", "MSFT"]

# --- 2. THE ANALYSER ---
class StaticAnalyser:
    def __init__(self):
        self.all_results = []

    def calculate_trend(self, score):
        # Convert AI decimal (0.7) to your 1-10 scale (+7)
        number = round(score * 10)
        if number >= 1:
            return f"Expect Profits (+{number})"
        elif number <= -1:
            return f"Expect a Decline ({number})"
        else:
            return "Neutral (0)"

    def start(self):
        print(f"Starting morning check for: {WATCHLIST}")
        
        for ticker in WATCHLIST:
            try:
                # Get Price
                data = yf.download(ticker, period="1mo", interval="1d", progress=False)
                current_price = data['Close'].iloc[-1]
                
                # Get News from Finnhub
                url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&token={FINNHUB_KEY}"
                news_list = requests.get(url).json()[:5] # Take top 5 stories
                
                # Calculate Mood Score
                total_score = 0
                for story in news_list:
                    text = story.get('headline', '')
                    total_score += TextBlob(text).sentiment.polarity
                
                avg_score = total_score / len(news_list) if news_list else 0
                
                # Add to our final list
                self.all_results.append({
                    "Ticker": ticker,
                    "Price": f"${current_price:.2f}",
                    "Trend": self.calculate_trend(avg_score),
                    "Articles": len(news_list)
                })
                print(f"Done with {ticker}")

            except Exception as e:
                print(f"Skipped {ticker} due to error: {e}")

    def email_me(self):
        if not self.all_results: return
        
        # Create the table
        df = pd.DataFrame(self.all_results)
        email_body = f"Good morning Satyam,\n\nHere is your daily stock check:\n\n{df.to_string(index=False)}"
        
        # Setup the email
        msg = MIMEText(email_body)
        msg['Subject'] = f"Daily Stock Report: {datetime.now().strftime('%Y-%m-%d')}"
        msg['From'] = MY_EMAIL
        msg['To'] = MY_EMAIL

        # Send it
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(MY_EMAIL, MY_PASS)
            server.send_message(msg)
        print("Report sent to your inbox!")

# --- 3. RUN THE SCRIPT ---
if __name__ == "__main__":
    bot = StaticAnalyser()
    bot.start()
    bot.email_me()
