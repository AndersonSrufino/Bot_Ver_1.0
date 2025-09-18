import requests

from bs4 import BeautifulSoup

url = "https://news.ycombinator.com/"
response = requests.get(url)

if response.estatus_code == 200:
    soup = BeautifulSoup(response.text, "html.parser")
    headings = soup.select(".titleline a")

    for heading in headings:
        print(heading.text)
    else:
        print('A requisição falhou.')