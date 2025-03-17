from openai import OpenAI
import requests
import yfinance as yf
import datetime
from matplotlib import pyplot as plt
import pandas as pd

# import keys
API_KEY = ... # INSERT API KEY HERE FOR LLM USAGE
NEWS_API_KEY = ... # INSERT KEY HERE FOR FINANCIAL API USAGE

# establish LLM client for invoking
client = OpenAI(api_key=API_KEY)

def steering_agent(user_question: str) -> int:
  prompt = f"""
  Classify the user's stock-related question into one of the following categories and return **ONLY** the corresponding integer:

  1 - General finance or stock-related concepts (e.g., definitions of finance/stock vocabulary, investing basics, stock evaluation).
  2 - Stock price or trend inquiries for a **SPECIFIC** company.
  3 - **News-related** requests about a company's stock or financial status.
  4 - Retrieval of the PE ratios of multiple various companies.
  5 - Any other question that does not fit the above categories or is unrelated to stocks/finance.

  Return **ONLY** the number as corresponding to the category, and nothing else, without any explanation.

  Examples:
  - What is the current price of Apple's stock? -> 2
  - Can you give me some stock anaylsis about Tesla? -> 2
  - What are some key factors to consider when evaluating a stock's potential for growth? -> 1
  - Give me some of the latest news regarding Nvidia's stock. -> 3
  - Can you provide me the PE ratios of various companies? -> 4
  - What is the weather like today? -> 5
  - What's the latest regarding Tesla? -> 3
  - What's the difference between a stock and a bond? -> 1
  - Can you show me the historical trend of Meta's stock? -> 2
  - What's a recipe for a delicious cheesecake? -> 5
  - Which companies have the lowest PE ratios? -> 4
  - What is a stock in finance? -> 1

  User's question: {user_question}
  """
  try:
    response = client.chat.completions.create(
      model="gpt-4",
      messages=[
        {"role": "system",
        "content": "You are a classification agent that categorizes user questions about stocks and finance into predefined types. Return only the corresponding category number."},
        {"role": "user",
        "content": prompt}
      ]
    )
    return int(response.choices[0].message.content)
  except Exception as e:
    return f"API call failed: {e}"
  
def stock_information_agent(user_question: str) -> str:
  prompt = f"""
  Provide a clear and accurate response to the user's question about stocks or finances.
  Keep explanations simple and easy to understand, assuming the user has little to no prior knowledge of stocks or finance.
  DO NOT use bullet points or any indentations when formatting your answer.
  User's question: {user_question}
  """
  try:
    response = client.chat.completions.create(
      model="gpt-4",
      messages=[
        {"role": "system",
         "content": "You are a stock market expert who explains financial concepts in a simple, accurate, and informative manner."},
        {"role": "user",
         "content": prompt
        }
      ])
    return response.choices[0].message.content  # Fixed return type
  except Exception as e:
    return f"API call failed: {e}"

def get_stock_symbol(user_question: str) -> str:
    prompt = f"""
    Given the user's inquiry about the stock/finances of a particular company or its subsidiaries, return the **stock symbol** of the publicly traded parent company.
    Return **ONLY** the stock symbol and nothing else, without any explanation.
    
    - If the company is publicly traded, return its stock symbol.
    - If the company is a subsidiary of another publicly traded company, return the parent's stock symbol.
    - If no identifiable company is found, return 'Not Found'.
    - Try to infer the correct company even if there are typos or misspellings.

    Examples:
    - What is the current price of Apple's stock? -> AAPL
    - Give me some of the latest news regarding Meta's stock. -> META
    - How is Instagram performing financially? -> META
    - What is the forecast for Tesla shares? -> TSLA
    - How is YouTube’s stock doing? -> GOOGL
    - What is the current state of the economy? -> Not Found

    User's question: {user_question}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system",
                 "content": "You are a helpful assistant that extracts stock symbols from a user's inquiry. If a company is owned by a parent company, return the parent's stock symbol. If no stock symbol is found, respond with 'Not Found'."},
                {"role": "user",
                 "content": prompt}
            ])
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"API call failed: {e}"

def get_current_price(symbol):
    try:
        price = yf.Ticker(symbol).history(period="1d")['Close'].iloc[-1]
        return f"${price:.2f}"
    except:
        return "Price unavailable."

def get_stock_trend(symbol, period="1y"):
    end = datetime.date.today()
    days = {"1y": 365, "3y": 3*365, "5y": 5*365}
    start = end - datetime.timedelta(days=days.get(period, 365))
    data = yf.download(symbol, start=start, end=end, progress = False, auto_adjust=False)
    return data['Close'] if not data.empty else None

def get_tabular_data(user_question: str):
   symbol = get_stock_symbol(user_question)
   company_trend = get_stock_trend(symbol)
   return company_trend

def get_stock_info(user_question: str):
  symbol = get_stock_symbol(user_question)

  if symbol == "Not Found":
    return "No stock information available for this company."

  company_current_price = get_current_price(symbol)
  company_trend = get_stock_trend(symbol)

  # get the PE ratio 
  stock = yf.Ticker(symbol)
  pe_ratio = stock.info.get("trailingPE", None)

  # grab the recent and upcoming earnings date
  earnings_dates = stock.earnings_dates
  # Reset index if "Earnings Date" is the index
  earnings_dates = earnings_dates.reset_index()

  # Ensure "Earnings Date" is in datetime format (remove timezone)
  earnings_dates["Earnings Date"] = pd.to_datetime(earnings_dates["Earnings Date"]).dt.normalize()

  # Sort the DataFrame by date
  earnings_dates = earnings_dates.sort_values(by="Earnings Date")

  # Get the last earnings date (most recent past date with actual EPS)
  last_earnings = earnings_dates[earnings_dates["Reported EPS"].notna()]["Earnings Date"].max()

  # Get the next earnings date (first future date)
  next_earnings = earnings_dates[earnings_dates["Earnings Date"] > last_earnings]["Earnings Date"].min()

  answer = f"The current stock price of {symbol} is {company_current_price}, and it's current PE (Price-to-Earnings) ratio is {pe_ratio}. It's most recent earnings date was {last_earnings.strftime('%Y-%m-%d')}, and it's next earnings date is {next_earnings.strftime('%Y-%m-%d')}."
  
  price_listing = ""
  for idx, price in enumerate(company_trend[symbol].values):
    price_listing += f"Day {idx+1}: ${price:.2f}\n"
  price_listing = price_listing.rstrip('\n')
  prompt = f"""
  You are provided the most recent stock prices of a company from the past 250 days. Given this data, provide a concise and brief, but insightful
  and informative analysis of the company's financial performance and outlook. Here is the data:

  (Least Recent)
  {price_listing}
  (Most Recent)
  """
  try:
    response = client.chat.completions.create(
      model="gpt-4",
      messages=[
        {"role": "system",
         "content": "You are an expert financial analyst that can provide useful and interesting insights about company stock prices."},
        {"role": "user",
         "content": prompt
        }
      ])
    anaylsis = response.choices[0].message.content
    final_answer = f"{answer}\n\n{anaylsis}"
    return final_answer
  except Exception as e:
    return f"API call failed: {e}"

def get_stock_news(user_question: str):
  symbol = get_stock_symbol(user_question)

  if symbol == "Not Found":
    return "No news available for this company."

  url = f"https://newsapi.org/v2/everything?q={symbol}&language=en&apiKey={NEWS_API_KEY}"
  response = requests.get(url).json()
  articles = response.get('articles', [])
  if len(articles) == 0:
    return "No news available for this company."
  else:
    response = "Here are some recent headlines I think you'd be interested in:\n\n"
    for idx, article in enumerate(articles[:5]):
      response += f"{idx+1}.) {article['title']}\n{article['url']}\n\n"
    return response

def get_pe_ratios():
  # List of stock tickers (You can expand this list or get from an index)
  tickers = {
      "Apple": "AAPL",
      "Microsoft": "MSFT",
      "Google": "GOOG",
      "Amazon": "AMZN",
      "Tesla": "TSLA",
      "Nvidia": "NVDA",
      "Meta": "META",
      "Berkshire Hathaway": "BRK-B",
      "JPMorgan Chase": "JPM",
      "Visa": "V",
      "Adobe": "ADBE",
      "AMD": "AMD",
      "Airbnb": "ABNB",
      "Alphabet (Google)": "GOOGL",
      "Amgen": "AMGN",
      "ASML": "ASML",
      "Broadcom": "AVGO",
      "Costco": "COST",
      "Netflix": "NFLX",
      "PayPal": "PYPL",
      "PepsiCo": "PEP",
      "Qualcomm": "QCOM",
      "Starbucks": "SBUX",
      "T-Mobile": "TMUS",
      "Intel": "INTC",
      "Intuit": "INTU",
      "Intuitive Surgical": "ISRG",
      "Lam Research": "LRCX",
      "Micron Technology": "MU",
      "Palantir": "PLTR",
      "Palo Alto Networks": "PANW",
      "Regeneron": "REGN"
  }

  # Fetch P/E ratios
  pe_ratios = {}
  for company_name, ticker in tickers.items():
      stock = yf.Ticker(ticker)
      pe_ratio = stock.info.get("trailingPE", None)  # Get P/E ratio (trailing 12 months)

      if pe_ratio:  # Only add if P/E ratio is available
          pe_ratios[f"{company_name} ({ticker})"] = pe_ratio

  # Convert to DataFrame and sort
  df = pd.DataFrame(list(pe_ratios.items()), columns=["Ticker", "PE Ratio"])
  df = df.sort_values(by="PE Ratio")
  df = df.reset_index(drop=True)

  df_str = "Here are the top five companies on Nasdaq with the lowest PE ratio:\n\n" + "\n\n".join(
    [f"{i+1}.) **{row['Ticker']}** - PE Ratio: {row['PE Ratio']:.2f}" for i, row in df.head(5).iterrows()]
  )

  return df_str