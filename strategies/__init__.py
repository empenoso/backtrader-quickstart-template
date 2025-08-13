# strategies/__init__.py

# 📂 Автоматический загрузчик стратегий 📂
#
# Этот системный файл работает как "авто-обнаружитель". Он автоматически сканирует папку 'strategies',
# находит в ней все файлы с торговыми стратегиями и делает их доступными для выбора в главном
# скрипте main.py. Благодаря ему, для добавления новой стратегии достаточно просто создать
# соответствующий файл в этой папке.
#
# Функционал:
# - Сканирует папку 'strategies' на наличие Python-файлов.
# - Игнорирует системные файлы ('__init__.py', 'base_strategy.py').
# - Находит внутри каждого файла класс торговой стратегии.
# - Составляет единый список всех доступных стратегий.
# - Выводит в консоль названия загруженных стратегий при запуске.
# - Позволяет легко расширять систему, не меняя код в main.py.
#
# Автор: Михаил Шардин https://shardin.name/
# Дата создания: 10.08.2025
# Версия: 1.0
# Новая версия всегда здесь: https://github.com/empenoso/backtrader-quickstart-template/
#
# Чтобы добавить новую стратегию, просто поместите ее файл в эту папку.
#

import os
import importlib
import inspect
from .base_strategy import BaseStrategy

# Словарь для хранения доступных стратегий: {'ИмяКласса': Класс}
available_strategies = {}

# Путь к текущей директории (папке strategies)
package_dir = os.path.dirname(__file__)

for filename in os.listdir(package_dir):
    if filename.endswith('.py') and filename not in ['__init__.py', 'base_strategy.py']:
        module_name = f"strategies.{filename[:-3]}"
        
        try:
            module = importlib.import_module(module_name)
            
            # Ищем в модуле классы, которые являются наследниками BaseStrategy
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BaseStrategy) and obj is not BaseStrategy:
                    available_strategies[name] = obj
                    print(f"Загружена стратегия: '{name}' из модуля '{module_name}'")

        except ImportError as e:
            print(f"Ошибка импорта модуля {module_name}: {e}")

if not available_strategies:
    print("Внимание: ни одной стратегии не найдено в папке 'strategies'.")