import requests

header = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/W.X.Y.Z Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
}


def bypass_paywall(url: str) -> str:
    response = requests.get(url, headers=header)
    response.encoding = response.apparent_encoding
    return response.text
