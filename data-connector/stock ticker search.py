# Этот скрипт обращается к Московской бирже (MOEX) по интернету
# и получает список всех доступных тикеров акций на основном рынке (TQBR).
# Затем он формирует строку вида:
# security_codes = ('SBER', 'GAZP', ...)
# которую можно использовать например в Python-программе скачивания котировок Bars.py библиотеки TinkoffPy.

# 24.05.2025
# Михаил Шардин, https://shardin.name/?utm_source=python

# security_codes = ('ABIO', 'ABRD', 'AFKS', 'AFLT', 'AGRO', 'AKRN', 'ALRS', 'AMEZ', 'APRI', 'APTK', 'AQUA', 'ARSA', 'ASSB', 'ASTR', 'AVAN', 'BANE', 'BANEP', 'BELU', 'BISVP', 'BLNG', 'BRZL', 'BSPB', 'BSPBP', 'CARM', 'CBOM', 'CHGZ', 'CHKZ', 'CHMF', 'CHMK', 'CNRU', 'CNTL', 'CNTLP', 'DATA', 'DELI', 'DIAS', 'DIOD', 'DVEC', 'DZRD', 'DZRDP', 'EELT', 'ELFV', 'ELMT', 'ENPG', 'ETLN', 'EUTR', 'FEES', 'FESH', 'FIXR', 'FLOT', 'GAZA', 'GAZAP', 'GAZC', 'GAZP', 'GAZS', 'GAZT', 'GCHE', 'GECO', 'GEMA', 'GEMC', 'GMKN', 'GTRK', 'HEAD', 'HIMCP', 'HNFG', 'HYDR', 'IGST', 'IGSTP', 'IRAO', 'IRKT', 'IVAT', 'JNOS', 'JNOSP', 'KAZT', 'KAZTP', 'KBSB', 'KCHE', 'KCHEP', 'KFBA', 'KGKC', 'KGKCP', 'KLSB', 'KLVZ', 'KMAZ', 'KMEZ', 'KOGK', 'KRKN', 'KRKNP', 'KRKOP', 'KROT', 'KROTP', 'KRSB', 'KRSBP', 'KUZB', 'KZOS', 'KZOSP', 'LEAS', 'LENT', 'LIFE', 'LKOH', 'LMBZ', 'LNZL', 'LNZLP', 'LPSB', 'LSNG', 'LSNGP', 'LSRG', 'LVHK', 'MAGE', 'MAGEP', 'MAGN', 'MBNK', 'MDMG', 'MFGS', 'MFGSP', 'MGKL', 'MGNT', 'MGNZ', 'MGTS', 'MGTSP', 'MISB', 'MISBP', 'MOEX', 'MRKC', 'MRKK', 'MRKP', 'MRKS', 'MRKU', 'MRKV', 'MRKY', 'MRKZ', 'MRSB', 'MSNG', 'MSRS', 'MSTT', 'MTLR', 'MTLRP', 'MTSS', 'MVID', 'NAUK', 'NFAZ', 'NKHP', 'NKNC', 'NKNCP', 'NKSH', 'NLMK', 'NMTP', 'NNSB', 'NNSBP', 'NSVZ', 'NVTK', 'OGKB', 'OKEY', 'OMZZP', 'OZON', 'OZPH', 'PAZA', 'PHOR', 'PIKK', 'PLZL', 'PMSB', 'PMSBP', 'POSI', 'PRFN', 'PRMB', 'PRMD', 'QIWI', 'RAGR', 'RASP', 'RBCM', 'RDRB', 'RENI', 'RGSS', 'RKKE', 'RNFT', 'ROLO', 'ROSN', 'ROST', 'RTGZ', 'RTKM', 'RTKMP', 'RTSB', 'RTSBP', 'RUAL', 'RUSI', 'RZSB', 'SAGO', 'SAGOP', 'SARE', 'SAREP', 'SBER', 'SBERP', 'SELG', 'SFIN', 'SGZH', 'SIBN', 'SLEN', 'SMLT', 'SNGS', 'SNGSP', 'SOFL', 'SPBE', 'STSB', 'STSBP', 'SVAV', 'SVCB', 'SVET', 'SVETP', 'T', 'TASB', 'TASBP', 'TATN', 'TATNP', 'TGKA', 'TGKB', 'TGKBP', 'TGKN', 'TNSE', 'TORS', 'TORSP', 'TRMK', 'TRNFP', 'TTLK', 'TUZA', 'UGLD', 'UKUZ', 'UNAC', 'UNKL', 'UPRO', 'URKZ', 'USBN', 'UTAR', 'UWGN', 'VEON-RX', 'VGSB', 'VGSBP', 'VJGZ', 'VJGZP', 'VKCO', 'VLHZ', 'VRSB', 'VRSBP', 'VSEH', 'VSMO', 'VSYD', 'VSYDP', 'VTBR', 'WTCM', 'WTCMP', 'WUSH', 'X5', 'YAKG', 'YDEX', 'YKEN', 'YKENP', 'YRSB', 'YRSBP', 'ZAYM', 'ZILL', 'ZVEZ')

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
