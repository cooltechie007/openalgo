#!/usr/bin/env python3
from datetime import datetime, timedelta
from openalgo import api

# Initialize the client
client = api(
    api_key="daeb594b3a696d6612b962913435d35e1ebda64564c0670255627514296e783e",
    host="http://127.0.0.1:5000",   # Use your OpenAlgo server address
    ws_url="ws://127.0.0.1:8765"    # Use your OpenAlgo WebSocket address
)


# Fetch the price quote for a specific symbol on a given exchange
response = client.quotes(symbol="NIFTY04NOV2525500CE,NIFTY04NOV2525500PE", exchange="NFO")
print(response)
asasasa
response = client.expiry(
    symbol="NIFTY",
    exchange="NFO",
    instrumenttype="options"
)
print(response)
from expiry_sorter import get_next_expiry
start_time = datetime.now()
next_expiry = get_next_expiry(response['data'], current_date=datetime.now()+ timedelta(days=3))
print(next_expiry)

a =client.search(query="NIFTY"+next_expiry.replace("-", "")+"25000CE", exchange="NFO")
print(a)
end_time = datetime.now()
print(end_time - start_time)

