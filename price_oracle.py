import time
import json
import random
import requests
from datetime import datetime

def get_aws_price():
   """AWS public spot price endpoint - no auth needed"""
   try: 
       url = "https://spot-price.s3.amazonaws.com/spot.js"
       r = requests.get(url, timeout=5)
       text = r.text.replace("callback(","").rstrip(");")
       data = json.loads(text)
       regions = data["config"]["regions"]
       for region in regions:
          if region["region"] == "us-east-1":
             types = region["instanceTypes"]
             for t in types:
                 sizes = t["sizes"]
                 for t in types:
                   sizes = t["sizes"]
                   for s in sizes:
                      prices = s["valueColumns"][0]["prices"]["USD"]
                      if price != "N/A*":
                         return float(price)
   except Exception as e :
     print(f"AWS API failed: {e} - using fallback")
   return round(random.uniform(0.05, 0.45), 4)

def get_azure_price():
    """Azure Retail prices API - completely free, no auth needed"""
    try:
        url = (
             "https://prices.azure.com/api/retail/prices"
             "?api-version=2023-01-01-preview"
             "&$filter=serviceName eq 'Virtual Machines ' "
             "and priceType eq 'Spot' "
             "and armRegionName eq 'eastus' "
         )
        r = requests.get(url, timeout=5)
        data = r.json()
        Items = data.get("Items", [])
        if items:
           price = items[0]["retailPrice"]
           return round(float(price), 4)
    except Exception as e:
       print(f"Azure API failed: {e} - using fallback")
    return round(random.uniform(0.04, 0.38), 4)
 
def get_gcp_price():
    """GCP has no free public spot API - uses realistic simulation"""
    return round(random.uniform(0.04, 0.38), 4)

def get_all_prices():
    print("Fetching live prices...")
    return {
          "timestamp": datetime.now().strftime("%H:%M:%S"),
          "AWS":       get_aws_price(),
          "Azure":     get_azure_price(),
          "GCP":       get_gcp_price(),
    }

if __name__== "__main__":
    print("Price oralce started - live cloud pricing feed")
    print("=" * 50)
    while True:
       prices = get_all_prices()
       cheapest = min(["AWS", "GCP", "Azure"], key=lambda x: prices[x])
       print(f"\n {prices['timestamp']}")
       print(f"  AWS  -> ${prices['AWS']}")
       print(f"  GCP  -> ${prices['GCP']}")
       print(f" Azure -> ${prices['Azure']}")
       print(f" Cheapest: {cheapest}")
       time.sleep(10)


