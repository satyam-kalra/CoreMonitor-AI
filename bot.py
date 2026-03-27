import os
import smtplib
import yfinance as yf
import pandas as pd
import requests
import nltk
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from textblob import TextBlob

# --- GITHUB ACTIONS OVERHEAD ---
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    nltk.download('brown')
    nltk.download('punkt_tab')

# --- CONFIGURATION ---
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASS = os.getenv("SENDER_PASS")

WATCHLIST = ["AAPL", "NVDA", "TSLA", "MSFT"]

class StockBot:
    def __init__(self):
        self.report_data = []

    def get_sentiment(self, text):
        if not text: return 0
        return TextBlob(text).sentiment.polarity

    def get_trend_label(self, score):
        """Converts -1.0 to +1.0 scale into -10 to +10 scale with labels"""
        scaled_score = round(score * 10)
        
        if scaled_score >= 1:
            return f"Expect Profits (+{scaled_score})"
        elif scaled_score <= -1:
            return f"Expect a Decline ({scaled_score})"
        else:
            return "Neutral (0)"

    def run_analysis(self):
        print(f"Starting analysis for: {', '.join(WATCHLIST)}")
        for ticker in WATCHLIST:
            try:
                # 1. Fetch Price Data
                df = yf.download(ticker, period="5d", interval="1d", progress=False)
                if df.empty:
                    print(f"No data found for {ticker}")
                    continue
                
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                price = df['Close'].iloc[-1]

                # 2. Fetch News
                end = datetime.now().strftime('%Y-%m-%d')
                start = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
                url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={start}&to={end}&token={FINNHUB_API_KEY}"
                
                response = requests.get(url, timeout=10)
                news = response.json()
                
                if not isinstance(news, list):
                    news = []

                # 3. Analyze Sentiment & Apply New Labeling
                headlines = [n.get('headline', '') for n in news[:5]]
                sent_scores = [self.get_sentiment(h) for h in headlines]
                avg_sent = sum(sent_scores)/len(sent_scores) if sent_scores else 0
                
                # Use your new labeling function here
                trend_label = self.get_trend_label(avg_sent)

                self.report_data.append({
                    "Ticker": ticker, 
                    "Price": f"${float(price):.2f}", 
                    "Trend on scale of -10 to +10": trend_label,
                    "Score": f"{avg_sent:.2f}",
                    "Backup by News Articles": len(news[:5])
                })
                print(f"Processed {ticker}")
            except Exception as e:
                print(f"Error processing {ticker}: {e}")

    def send_email(self):
        if not self.report_data:
            print("No data to send.")
            return False

        df = pd.DataFrame(self.report_data)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        body = f"Daily Market Intelligence Report\nGenerated: {timestamp}\n\n{df.to_string(index=False)}"
        
        msg = MIMEText(body)
        msg['Subject'] = f"Stock Alert: {datetime.now().strftime('%Y-%m-%d')}"
        msg['From'] = SENDER_EMAIL
        msg['To'] = SENDER_EMAIL

        try:
            # Port 587 is standard for modern cloud environments
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls() 
            server.login(SENDER_EMAIL, SENDER_PASS)
            server.send_message(msg)
            server.quit()
            print("Email sent successfully!")
            return True
        except Exception as e:
            print(f"SMTP Error: {e}")
            return False

if __name__ == "__main__":
    bot = StockBot()
    bot.run_analysis()
    if bot.send_email():
        print("Workflow Complete.")
    else:
        print("Workflow finished with errors.")
