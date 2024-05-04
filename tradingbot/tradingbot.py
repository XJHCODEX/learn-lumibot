from lumibot.brokers import Alpaca # Alpaca is our broker
from lumibot.backtesting import YahooDataBacktesting # YahooData will give us our framework
from lumibot.strategies.strategy import Strategy # Strategy will be our trading bot
from lumibot.traders import Trader # For live deployment
from datetime import datetime, timedelta
from alpaca_trade_api import REST
from finbert_utils import estimate_sentiment
import os

os.environ['KMP_DUPLICATE_LIB_OK']='True'

# endpoint
BASE_URL = "https://paper-api.alpaca.markets/v2"
# key
API_KEY = "PK6JJ4ZC7XEL4O50AXZU" # dont forget to delete endpoint, key, and secret
# secret
API_SECRET = "10fFaDBfpPKCULhNTViz6Glz3lrxr26qs9E8BQdr"

# Dictionary for Alpaca Broker

ALPACA_CREDS = {
    "API_KEY" : API_KEY,
    "API_SECRET" : API_SECRET,
    # Paper trading
    "PAPER" : True
}

# Trading logic - Inherit from strategy class
class JTrader(Strategy):
    def initialize(self, symbol:str = "SPY", cash_at_risk:float = .5): # stock ticker is SPY
        self.symbol = symbol
        # Dictates how long it trades
        self.sleep = "12H"
        self.last_trade = None
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url = BASE_URL, key_id = API_KEY, secret_key = API_SECRET)

    def position_sizing(self):
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        # how many units we will get per risk
        quantity = round(cash * self.cash_at_risk / last_price)
        return cash, last_price, quantity
    def get_dates(self):
        today = self.get_datetime()
        three_days_prior = today - timedelta(days = 3)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')
    
    def get_sentiment(self):
        today, three_days_prior = self.get_dates()
        news = self.api.get_news(symbol = self.symbol, start = three_days_prior,
                                 end = today)
        news = [ev.__dict__["_raw"]["headline"]for ev in news]
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment
        
    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_sizing()
        probability, sentiment = self.get_sentiment()
                # sell order
        if cash > last_price:
            if sentiment == "positive" and probability > .999:
                if self.last_order == "sell":
                    self.sell_all
                order = self.create_order(
                    self.symbol,
                    quantity,
                    "buy",
                    type="bracket",# market # for out stop loss / take profit we use bracket
                    take_profit_price = last_price * 1.20,# 20 % take profit
                    stop_loss_price = last_price * .95 # 5 % stop loss
                )
                self.submit_order(order)
                self.last_trade = "buy"
                
                # buy order
            elif sentiment == "negative" and probability > .999:
                if self.last_order == "buy":
                    self.sell_all
                order = self.create_order(
                    self.symbol,
                    quantity,
                    "sell",
                    type="bracket",# market # for out stop loss / take profit we use bracket
                    take_profit_price = last_price * .85,# 20 % take profit
                    stop_loss_price = last_price * 1.05 # 5 % stop loss
                )
                self.submit_order(order)
                self.last_trade = "sell"
    

broker = Alpaca(ALPACA_CREDS)
strategy = JTrader(name = 'mlstrat', broker = broker, parameters = {"symbol":"SPY",
                                                                     "cash_at_risk": .5})

start_date = datetime(2024,4,25) # 2024, April 25th
end_date = datetime(2024,5,3) # 2024, May 3rd

strategy.backtest(
    YahooDataBacktesting,
    start_date,
    end_date,
    parameters = {"symbol":"SPY",
                  "cash_at_risk": .5}
)