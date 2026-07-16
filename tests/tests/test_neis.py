import requests
from config.settings import NEIS_API_KEY

url = "https://open.neis.go.kr/hub/schoolInfo"

params = {
    "KEY": NEIS_API_KEY,
    "Type": "json",
    "pIndex": 1,
    "pSize": 3
}

response = requests.get(url, params=params)

print(response.status_code)
print(response.text)