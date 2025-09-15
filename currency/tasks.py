import requests
from django.utils import timezone

from .models import Exchange
from decimal import Decimal
from bs4 import BeautifulSoup
from celery import shared_task


@shared_task()
def fetch_exchange_rates_bcp():
    url = "https://www.bcp.gov.py/webapps/web/cotizacion/monedas"
    response = requests.get(url)
    if response.status_code != 200:
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table', {'class': 'table table-bordered table-striped table-condensed'})
    if not table:
        return

    rows = table.find_all('tr')[1:]
    rates = {}
    for row in rows:  # Skip header row
        cols = row.find_all('td')
        if len(cols) < 4:
            continue
        currency_code = cols[0].text.strip()
        buy_rate = cols[1].text.strip().replace('.', '').replace(',', '.')
        sell_rate = cols[2].text.strip().replace('.', '').replace(',', '.')
        rates[currency_code] = {
            'buy': Decimal(buy_rate),
            'sell': Decimal(sell_rate)
        }

    timestamp = timezone.now()
    source = "Banco Central del Paraguay"
    base_currency = 'PYG'
    for currency, rate in rates.items():
        if currency == base_currency:
            continue
        Exchange.objects.create(
            base_currency=base_currency,
            currency=currency,
            buy=rate['buy'],
            sell=rate['sell'],
            source=source,
            timestamp=timestamp
        )
    return f"Fetched and stored exchange rates for {len(rates) - 1} currencies."


@shared_task
def fetch_exchange_rates_cambios_chaco():
    url = "https://www.cambioschaco.com.py/"
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        return f"Failed with {response.status_code}"

    soup = BeautifulSoup(response.content, "html.parser")
    tbody = soup.find("tbody", id="main-exchange-content")
    if not tbody:
        return "No exchange table found"

    rows = tbody.find_all("tr")
    base_currency = "PYG"
    source = "Cambios Chaco"
    count = 0



    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        name = cols[0].get_text(strip=True)

        mapping = {
            "Dólar Americano": "USD",
            "Euro": "EUR",
            "Real": "BRL",
            "Peso Argentino": "ARS",
            "Peso Chileno": "CLP",
            "Libra Esterlina": "GBP",
            # add others if needed
        }

        currency = mapping.get(name)
        if not currency or currency == base_currency:
            continue

        buy_tag = cols[1].find("span", class_="purchase")
        sell_tag = cols[2].find("span", class_="sale")
        if not buy_tag or not sell_tag:
            continue

        buy = Decimal(buy_tag.text.strip().replace(".", "").replace(",", "."))
        sell = Decimal(sell_tag.text.strip().replace(".", "").replace(",", "."))

        Exchange.objects.create(
            currency=currency,
            buy=buy,
            sell=sell,
            source=source,
        )
        count += 1

    return f"Cambios Chaco: saved {count} currencies"


@shared_task
def fetch_exchange_rates_maxi():
    url = "https://www.maxicambios.com.py/"
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        return f"Failed with {response.status_code}"

    soup = BeautifulSoup(response.content, "html.parser")
    cards = soup.find_all("div", class_="cotizDivSmall")
    base_currency = "PYG"
    source = "MaxiCambios"
    count = 0

    mapping = {
        "Dólar": "USD",
        "Euro": "EUR",
        "Real": "BRL",
        "Peso Arg": "ARS",
        "Peso Chileno": "CLP",
        "Libra Esterlina": "GBP",
    }

    for card in cards:
        name_tag = card.find("p")
        if not name_tag:
            continue
        name = name_tag.text.strip()

        currency = mapping.get(name)
        if not currency or currency == base_currency:
            continue

        numbers = card.find_all("p", style=lambda s: s and "font-size" in s)
        if len(numbers) >= 2:
            buy_text = numbers[0].contents[0].strip()
            sell_text = numbers[1].contents[0].strip()

            try:
                buy = Decimal(buy_text.replace(".", "").replace(",", "."))
                sell = Decimal(sell_text.replace(".", "").replace(",", "."))
            except Exception:
                continue

            Exchange.objects.create(
                currency=currency,
                buy=buy,
                sell=sell,
                source=source,
            )
            count += 1

    return f"MaxiCambios: saved {count} currencies"
