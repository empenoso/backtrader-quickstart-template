# Этот скрипт обращается к Московской бирже (MOEX) по интернету
# и получает список всех доступных тикеров акций на основном рынке (TQBR).
# Затем он формирует строку вида:
# security_codes = ('SBER', 'GAZP', ...)
# которую можно использовать например в Python-программе скачивания котировок Bars.py библиотеки TinkoffPy.

# 24.05.2025
# Михаил Шардин, https://shardin.name/?utm_source=python

import requests

# Делаем запрос к серверу
url = "https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json"
params = {
    "iss.meta": "off",
    "iss.only": "marketdata",
    "marketdata.columns": "SECID"
}
response = requests.get(url, params=params)
response.raise_for_status()  # проверка на ошибку

# Извлекаем тикеры
data = response.json()
tickers = [item[0] for item in data['marketdata']['data']]

# Формируем строку
security_codes_str = f"security_codes = {tuple(tickers)}"
print(security_codes_str)
