import time
import requests
import json
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from win10toast import ToastNotifier

last_listing_nb = 0
sleep_time = 5
base_url_de = "https://us-central1-digitaleyes-prod.cloudfunctions.net/offers-retriever?price=asc&collection="
base_url_solanart = "https://qzlsklfacc.medianetwork.cloud/nft_for_sale?collection="
base_url_magiceden = "https://api-mainnet.magiceden.io/rpc/getListedNFTsByQuery"
base_url_alphart = "https://apis.alpha.art/api/v1/collection"
token_url_de = "https://digitaleyes.market/item/"
token_url_solanart = "https://solanart.io/search/?token="
token_url_magiceden = "https://magiceden.io/item-details/"
token_url_alphart = "https://alpha.art/t/"
base_url_moonrank = "https://moonrank.app/mints/"
is_sale = 0
fp = 999
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'}

def get_attributes():
  with open('listen_for.json') as json_file:
    return json.load(json_file)

def get_collection_mapping():
  with open('collection_mapping.json') as json_file:
    return json.load(json_file)
    
attributes = get_attributes()
collection_mapping = get_collection_mapping()

def filter_solanart(r, attr):
  filtered_array = []
  for offer in r:
    attributes = offer['attributes'].split(',')
    for attribute in attributes:
      attribute_mapping = attribute.split(': ')
      if attribute_mapping[0] == attr['attribute_name'] and attribute_mapping[1] == attr['attribute_value']:
        filtered_array.append(offer)

  return filtered_array

def get_token_url(site):
  if site == 'solanart':
    return token_url_solanart
  if site == 'de':
    return token_url_de
  if site == 'magiceden':
    return token_url_magiceden
  if site == 'alphart':
    return token_url_alphart
  else:
    return 'no_url'

def get_solanart(attr):
  while True:
    try:
      data = requests.get(base_url_solanart + collection_mapping[attr['collection']]['solanart'], headers=headers).json() 
      if 'attribute_value' in attr:
        filtered_offers = filter_solanart(data, attr)
      else:
        filtered_offers = data
      parsed_results = []
      for offer in filtered_offers:
        parsed_results.append({
          "price": offer['price'],
          "mint": offer['token_add'],
          "site": "solanart"
        })
      return parsed_results
    except Exception as e:
      print(f'Error obtaining NFT data: {e}')

def get_de(attr):
  while True:
    try:
      if 'attribute_value' in attr:
        data = requests.get(base_url_de + collection_mapping[attr['collection']]['de'] + "&" + attr['attribute_name'] + "=" + attr['attribute_value'], headers=headers).json()
      else:
        data = requests.get(base_url_de + collection_mapping[attr['collection']]['de'], headers=headers).json()
      offers = data['offers']
      parsed_offers = []
      for offer in offers:
        parsed_offers.append({
          "price": (offer['price'] / 1000000000),
          "mint": offer['mint'],
          "site": "de"
        })
      return parsed_offers
    except Exception as e:
      print(f'Error obtaining NFT data: {e}')

def get_magiceden(attr):
  while True:
    try:
      if 'attribute_value' in attr:
        params = '{"$match":{"collectionSymbol":"'+collection_mapping[attr['collection']]['magiceden']+'","$and":[{"$or":[{"attributes.trait_type":"'+ attr['attribute_name'] +'","attributes.value":"'+ attr['attribute_value'] +'"}]}]},"$sort":{"takerAmount":1,"createdAt":-1},"$skip":0,"$limit":20}'
      else:
        params = '{"$match":{"collectionSymbol":"' + collection_mapping[attr['collection']]['magiceden'] + '"},"$sort":{"takerAmount":1,"createdAt":-1},"$skip":0,"$limit":20}'
      data = requests.get(base_url_magiceden, params={'q': params} , headers=headers).json()
      offers = data['results']
      parsed_offers = []
      for offer in offers:
        if offer['price'] > 0:
          parsed_offers.append({
            "price": offer['price'],
            "mint": offer['mintAddress'],
            "site": "magiceden"
          })
      return parsed_offers
    except Exception as e:
      print(f'Error obtaining NFT data: {e}')

def get_alphart(attr):
  while True:
    try:
      if 'attribute_value' in attr:
        query = {
            "collectionId": collection_mapping[attr['collection']]['alphart'],
            "orderBy": "PRICE_LOW_TO_HIGH",
            "status": [
              "BUY_NOW"
            ],
            "traits": [
              {
                "key": attr['attribute_name'],
                "values": [
                  attr['attribute_value']
                ]
              }
            ]
        } 
      else:
        query = {
          "collectionId": collection_mapping[attr['collection']]['alphart'],
          "orderBy": "PRICE_LOW_TO_HIGH",
          "status": [
            "BUY_NOW"
          ],
          "traits": [            
          ]
        }
      data = requests.post(base_url_alphart, json= query , headers=headers).json()
      offers = data['tokens']
      parsed_offers = []
      for offer in offers:
        parsed_offers.append({
          "price": (int(offer['price']) / 1000000000),
          "mint": offer['mintId'],
          "site": "alphart"
        })
      return parsed_offers
    except Exception as e:
      print(f'Error obtaining NFT data: {e}')

def check_attribute(r, attr):
  is_sale = 0
  rank = 0
  fp = 999
  for offer in r:
    if (fp > offer['price'] ):
      fp = offer['price']
    if ((offer['price'] < attr['value'])):
        is_sale = 1
        print("-------------------------------------------")
        if len(collection_mapping[attr['collection']]['moonrank']): 
          r = requests.get(base_url_moonrank + collection_mapping[attr['collection']]['moonrank']).json()
          data = r['mints']
          if list(filter(lambda x:x["mint"]==offer['mint'],data)):
            [details] = list(filter(lambda x:x["mint"]==offer['mint'],data))   
            rank = details['rank']
        if 'attribute_value' in attr:
          print("Rank #%s: %s from %s at %.2f!" %(rank, attr['attribute_value'], attr['collection'], (offer['price'])))
        else:
          print("Rank #%s: random item from %s at %.2f!" %(rank, attr['collection'], (offer['price'])))          
        print(get_token_url(offer['site']) + "%s" %(offer['mint']))
        # print("-------------------------------------------")
  if (is_sale):
    toaster = ToastNotifier()
    if (rank > 0):
        msg = '¡RARE! #'+ str(details['rank'])+ ' ' + str(attr['collection']) + " at " + str(fp)        
    else:
        msg = str(attr['collection']) + " at " + str(fp)
    toaster.show_toast("¡Floor price alert!",
                msg,
                icon_path=None,
                duration=5)
    # Wait for threaded notification to finish
    # while toaster.notification_active(): time.sleep(0.1)

while True:
  print('GM, checking for good deals ...')
  for attr in attributes:
    if len(collection_mapping[attr['collection']]['de']):
      r_de = get_de(attr)
    else:
      r_de = []
    if len(collection_mapping[attr['collection']]['solanart']): 
      r_solanart = get_solanart(attr)
    else:
      r_solanart = []
    if len(collection_mapping[attr['collection']]['magiceden']): 
      r_magiceden = get_magiceden(attr)
    else:
      r_magiceden = []
    if len(collection_mapping[attr['collection']]['alphart']): 
      r_alphart = get_alphart(attr)
    else:
      r_alphart = []

    r = r_de + r_solanart + r_magiceden + r_alphart
    check_attribute(r, attr)
  print("Sleeping for %d seconds, GN!" %(sleep_time))
  time.sleep(sleep_time)