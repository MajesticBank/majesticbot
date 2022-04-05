MajesticExchangeBot

Recommended to first create, and switch to, a project venv. 

Install requirements with:
```
pip install -r requirements.txt
```

Run with:
```
python3.10 server.py
```

Caution! Do **NOT** run more than instance at once!



Insert values into MajesticBank/__init__.py

API_KEY = ""  # From Telegram Bot

DEFAULT_REFERRAL_CODE = "" # Register on majesticbank website and get from dashboard



Telegram Botfather commands:

/setcommands

```
help - List of commands
estimate - Estimate a trade
trade - Trade with a floating rate
fixed - Trade with a fixed rate
track - Transaction status
rates - Current rates on all currency pairs
limits - Min & max trade amount for the currency selected
```

/setabouttext

```
Exchange XMR, BTC, and LTC in Telegram. No signup required.
```

/setdescription

```
MajesticExchangeBot allows you to trade between Monero, Bitcoin, and Litecoin without leaving Telegram. 
Fixed conversion available for payments / invoices.
Fast. Reliable. Private.
```