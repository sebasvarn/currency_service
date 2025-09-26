import requests
from django.utils import timezone

from .models import Exchange
from decimal import Decimal
from bs4 import BeautifulSoup
from celery import shared_task
from monedas.models import Moneda, TasaCambio

COMISIONES = [
     {"currency": "USD", "commission_buy": 50, "commission_sell": 100, "base_currency": "PYG"},
     {"currency": "EUR", "commission_buy": 60, "commission_sell": 120, "base_currency": "PYG"},
     {"currency": "BRL", "commission_buy": 10, "commission_sell": 20, "base_currency": "PYG"},
     {"currency": "ARS", "commission_buy": 1, "commission_sell": 2, "base_currency": "PYG"},
     {"currency": "CLP", "commission_buy": 2, "commission_sell": 4, "base_currency": "PYG"},
     {"currency": "JPY", "commission_buy": 8, "commission_sell": 16, "base_currency": "PYG"},
     {"currency": "GBP", "commission_buy": 70, "commission_sell": 140, "base_currency": "PYG"},
     {"currency": "CHF", "commission_buy": 60, "commission_sell": 120, "base_currency": "PYG"},
     {"currency": "AUD", "commission_buy": 35, "commission_sell": 70, "base_currency": "PYG"}
]

COMISIONES_MAP = {
    c["currency"]: {"buy": Decimal(str(c["commission_buy"])), "sell": Decimal(str(c["commission_sell"]))}
    for c in COMISIONES
}

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
    fuente = "Cambios Chaco"
    base_currency = "PYG"
    count = 0

    mapping = {
        "Dólar Americano": "USD",
        "Euro": "EUR",
        "Real": "BRL",
        "Peso Argentino": "ARS",
        "Peso Chileno": "CLP",
        "Libra Esterlina": "GBP",
    }

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        name = cols[0].get_text(strip=True)
        codigo = mapping.get(name)
        if not codigo or codigo == base_currency:
            continue

        buy_tag = cols[1].find("span", class_="purchase")
        sell_tag = cols[2].find("span", class_="sale")
        if not buy_tag or not sell_tag:
            continue

        try:
            raw_buy = Decimal(buy_tag.text.strip().replace(".", "").replace(",", "."))
            raw_sell = Decimal(sell_tag.text.strip().replace(".", "").replace(",", "."))
        except Exception:
            continue
        print(f"Raw buy: {raw_buy}, Raw sell: {raw_sell}")
        pb = (raw_buy + raw_sell) / 2

        com = COMISIONES_MAP.get(codigo, {"buy": Decimal("0"), "sell": Decimal("0")})
        comision_buy = com["buy"]
        comision_sell = com["sell"]

        # Fórmula: Venta (PYG -> moneda extranjera)
        tc_venta = pb + comision_sell

        # Fórmula: Compra (moneda extranjera -> PYG)
        tc_compra = pb - comision_buy

        # asegurar moneda existe
        moneda, _ = Moneda.objects.get_or_create(codigo=codigo, defaults={"nombre": name})

        # guardar en tasas
        TasaCambio.objects.create(
            moneda=moneda,
            compra=tc_compra,
            venta=tc_venta,
            fuente=fuente,
            es_automatica=True,
        )
        count += 1

    return f"Cambios Chaco: saved {count} tasas (con comisiones)"

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
