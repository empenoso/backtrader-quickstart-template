#  установка описана здесь: https://habr.com/ru/articles/912528/

# Выполняете установку:
# cd c:\Users\Михаил\SynologyProjects\2025_08_Backtrader_universal\data-connector\
# pip install -e .

# Чтобы удалить пакет:
# pip uninstall TinkoffPy

from setuptools import setup, find_packages

setup(
    name="TinkoffPy",
    version="1.0.0",
    description="Tinkoff Invest API Python wrapper",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.6",
)