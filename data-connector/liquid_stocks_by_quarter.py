"""
АНАЛИЗАТОР ЛИКВИДНОСТИ АКЦИЙ

Что делает: Находит самые активно торгуемые акции по кварталам за последние Х лет (по умолчанию 5).
Анализирует объемы торгов в рублях и отбирает топ-Х (по умолчанию 40) самых ликвидных акций.

Что нужно:
- Папка Data/Tinkoff/ с файлами TQBR.СИМВОЛ_D1.txt (дневные данные акций)
- Опционально: TinkoffPy для размеров лотов

Как запустить: python liquid_stocks_by_quarter.py

Результат: файл liquid_stocks_by_quarter.csv с топ акциями по кварталам
"""

# 13.08.2025
# Михаил Шардин, https://shardin.name/?utm_source=python

import os
import sys
import pandas as pd
import logging
import glob
from datetime import datetime, timedelta
from collections import defaultdict
from TinkoffPy import TinkoffPy

# Настройка кодировки для корректного вывода русского текста
if sys.platform == 'win32':
    os.system('chcp 65001')  # UTF-8 для Windows консоли
    sys.stdout.reconfigure(encoding='utf-8')

class LiquidityAnalyzer:
    def __init__(self, data_folder="Data/Tinkoff/", years_back=5, top_n_stocks=40):
        """
        Анализатор ликвидности акций по кварталам
        
        Args:
            data_folder: путь к папке с данными
            years_back: количество лет назад для анализа
            top_n_stocks: количество самых ликвидных акций для отбора
        """
        self.data_folder = data_folder
        self.years_back = years_back
        self.top_n_stocks = top_n_stocks
        self.tp_provider = None
        self.lot_sizes = {}
        
        # Настройка логирования
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%d.%m.%Y %H:%M:%S',
            level=logging.INFO,
            handlers=[
                logging.FileHandler('liquidity_analysis.log', encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('LiquidityAnalyzer')
    
    def get_quarter_string(self, date):
        """
        Получение строкового представления квартала
        
        Args:
            date: дата в формате datetime или Timestamp
        
        Returns:
            str: строка вида "2024-Q1"
        """
        quarter = (date.month - 1) // 3 + 1
        return f"{date.year}-Q{quarter}"
    
    def connect_to_tinkoff(self):
        """Подключение к Tinkoff API для получения размеров лотов"""
        try:
            self.tp_provider = TinkoffPy()
            self.logger.info("Подключение к Tinkoff API установлено")
        except Exception as e:
            self.logger.error(f"Ошибка подключения к Tinkoff API: {e}")
            raise
    
    def get_lot_size(self, ticker):
        """
        Получение размера лота для тикера
        
        Args:
            ticker: тикер без префикса TQBR (например, SBER)
        
        Returns:
            int: размер лота
        """
        if ticker in self.lot_sizes:
            return self.lot_sizes[ticker]
        
        try:
            dataname = f"TQBR.{ticker}"
            class_code, security_code = self.tp_provider.dataname_to_class_code_symbol(dataname)
            si = self.tp_provider.get_symbol_info(class_code, security_code)
            
            if si:
                lot_size = si.lot
                self.lot_sizes[ticker] = lot_size
                self.logger.info(f"Размер лота для {ticker}: {lot_size}")
                return lot_size
            else:
                self.logger.warning(f"Информация о тикере {ticker} не найдена")
                return 1  # По умолчанию
        except Exception as e:
            self.logger.error(f"Ошибка получения размера лота для {ticker}: {e}")
            return 1
    
    def debug_file_format(self, file_path, max_lines=5):
        """
        Отладочная функция для проверки формата файла
        
        Args:
            file_path: путь к файлу
            max_lines: максимальное количество строк для вывода
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:max_lines]
                self.logger.info(f"Первые {len(lines)} строк файла {os.path.basename(file_path)}:")
                for i, line in enumerate(lines):
                    self.logger.info(f"  {i}: {line.rstrip()}")
        except Exception as e:
            self.logger.error(f"Ошибка чтения файла {file_path}: {e}")
    
    def load_stock_data(self, file_path):
        """
        Загрузка данных по акции из файла
        
        Args:
            file_path: путь к файлу с данными
        
        Returns:
            pd.DataFrame: данные акции
        """
        try:
            # Для отладки показываем формат файла
            if self.logger.level <= logging.DEBUG:
                self.debug_file_format(file_path)
            
            df = pd.read_csv(file_path, sep='\t')
            
            # Проверяем наличие колонки datetime
            if 'datetime' not in df.columns:
                self.logger.error(f"Колонка 'datetime' не найдена в файле {file_path}")
                self.logger.error(f"Доступные колонки: {list(df.columns)}")
                return None
            
            # Преобразуем колонку datetime в правильный формат
            try:
                df['datetime'] = pd.to_datetime(df['datetime'], format='%d.%m.%Y %H:%M')
            except ValueError:
                # Пробуем другие форматы
                try:
                    df['datetime'] = pd.to_datetime(df['datetime'])
                except Exception as e:
                    self.logger.error(f"Не удалось преобразовать datetime в файле {file_path}: {e}")
                    return None
            
            df.set_index('datetime', inplace=True)
            
            # Проверяем наличие необходимых колонок
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                self.logger.error(f"Отсутствуют колонки в файле {file_path}: {missing_columns}")
                return None
            
            self.logger.debug(f"Успешно загружено {len(df)} записей из {file_path}")
            return df
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки файла {file_path}: {e}")
            return None
    
    def calculate_quarterly_liquidity(self):
        """
        Расчет ликвидности акций по кварталам
        
        Returns:
            dict: словарь с ликвидностью по кварталам
        """
        # Получаем все файлы с данными
        pattern = os.path.join(self.data_folder, "TQBR.*_D1.txt")
        files = glob.glob(pattern)
        
        if not files:
            self.logger.error(f"Не найдены файлы в папке {self.data_folder}")
            return {}
        
        self.logger.info(f"Найдено {len(files)} файлов для обработки")
        
        # Подключаемся к Tinkoff API
        try:
            self.connect_to_tinkoff()
        except Exception as e:
            self.logger.error(f"Не удалось подключиться к Tinkoff API: {e}")
            # Продолжаем работу без API, используя размер лота = 1
        
        # Определяем диапазон дат
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * self.years_back)
        
        # Словарь для хранения данных по кварталам
        quarterly_data = defaultdict(dict)
        
        self.logger.info(f"Анализируем период с {start_date.date()} по {end_date.date()}")
        
        processed_count = 0
        error_count = 0
        
        for file_path in files:
            try:
                # Извлекаем тикер из имени файла
                filename = os.path.basename(file_path)
                ticker = filename.split('.')[1].split('_')[0]
                
                self.logger.info(f"Обрабатываем тикер: {ticker} ({processed_count + 1}/{len(files)})")
                
                # Загружаем данные
                df = self.load_stock_data(file_path)
                if df is None:
                    error_count += 1
                    continue
                
                # Фильтруем по датам
                df = df[(df.index >= start_date) & (df.index <= end_date)]
                if df.empty:
                    self.logger.warning(f"Нет данных для {ticker} в указанном периоде")
                    continue
                
                # Получаем размер лота
                lot_size = self.get_lot_size(ticker) if self.tp_provider else 1
                
                # Рассчитываем объем в рублях
                df['volume_rub'] = df['volume'] * lot_size * df['close']
                
                # Группируем по кварталам
                df['quarter'] = df.index.to_period('Q')
                quarterly_volumes = df.groupby('quarter')['volume_rub'].sum()
                
                # Сохраняем данные по кварталам
                for quarter, volume in quarterly_volumes.items():
                    quarter_end = quarter.end_time
                    quarterly_data[quarter_end][ticker] = volume
                
                processed_count += 1
                
            except Exception as e:
                self.logger.error(f"Ошибка обработки файла {file_path}: {e}")
                error_count += 1
                continue
        
        # Закрываем соединение с Tinkoff API
        if self.tp_provider:
            try:
                self.tp_provider.close_channel()
            except Exception as e:
                self.logger.warning(f"Ошибка закрытия соединения с Tinkoff API: {e}")
        
        self.logger.info(f"{'=' * 70}")
        self.logger.info(f"Обработано файлов: {processed_count}, ошибок: {error_count}")
        return quarterly_data
    
    def select_top_liquid_stocks(self, quarterly_data):
        """
        Отбор самых ликвидных акций по кварталам
        
        Args:
            quarterly_data: данные о ликвидности по кварталам
        
        Returns:
            dict: топ акций по кварталам
        """
        top_stocks_by_quarter = {}
        
        for quarter_date, stocks_data in quarterly_data.items():
            # Сортируем акции по объему торгов
            sorted_stocks = sorted(stocks_data.items(), key=lambda x: x[1], reverse=True)
            
            # Берем топ акций
            top_stocks = [stock[0] for stock in sorted_stocks[:self.top_n_stocks]]
            top_stocks_by_quarter[quarter_date] = top_stocks
            
            # Исправленное форматирование квартала
            quarter_str = self.get_quarter_string(quarter_date)
            self.logger.info(f"Квартал {quarter_str}: {len(top_stocks)} акций")
            self.logger.info(f"Топ-5: {top_stocks[:5]}")
        
        return top_stocks_by_quarter
    
    def save_to_csv(self, top_stocks_by_quarter, filename="liquid_stocks_by_quarter.csv"):
        """
        Сохранение результатов в CSV файл
        
        Args:
            top_stocks_by_quarter: топ акций по кварталам
            filename: имя файла для сохранения
        """
        rows = []
        
        for quarter_date, stocks in sorted(top_stocks_by_quarter.items()):
            stocks_str = ",".join(stocks)
            quarter_str = self.get_quarter_string(quarter_date)
            rows.append({
                'date': quarter_date.strftime('%Y-%m-%d'),
                'quarter': quarter_str,
                'stocks': stocks_str,
                'stocks_count': len(stocks)
            })
        
        df = pd.DataFrame(rows)
        df.to_csv(filename, index=False, encoding='utf-8')
        
        self.logger.info(f"Результаты сохранены в файл: {filename}")
        return filename
    
    def run_analysis(self):
        """
        Запуск полного анализа ликвидности
        
        Returns:
            str: путь к файлу с результатами
        """
        self.logger.info("Начинаем анализ ликвидности акций")
        
        try:
            # Рассчитываем ликвидность по кварталам
            quarterly_data = self.calculate_quarterly_liquidity()
            
            if not quarterly_data:
                self.logger.error("Не удалось получить данные для анализа")
                return None
            
            # Отбираем топ ликвидных акций
            top_stocks = self.select_top_liquid_stocks(quarterly_data)
            
            if not top_stocks:
                self.logger.error("Не удалось отобрать топ акций")
                return None
            
            # Сохраняем результаты
            filename = self.save_to_csv(top_stocks)
            
            self.logger.info("Анализ завершен успешно")
            return filename
            
        except Exception as e:
            self.logger.error(f"Критическая ошибка анализа: {e}")
            return None

# Поиск
if __name__ == '__main__':
    # 1. Определяем абсолютный путь к директории, где лежит наш скрипт
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Строим полный, надежный путь к папке с данными
    #    os.path.join корректно соединит пути для любой ОС (Windows/Linux/Mac)
    data_path = os.path.join(script_dir, "Data", "Tinkoff")

    print(f"Путь к скрипту: {script_dir}")
    print(f"Итоговый путь к данным: {data_path}")

    # 3. Передаем этот надежный путь в наш анализатор
    analyzer = LiquidityAnalyzer(
        data_folder=data_path,
        years_back=20,
        top_n_stocks=40
    )
    
    # Устанавливаем уровень отладки
    analyzer.logger.setLevel(logging.DEBUG)
    
    # Сначала тестируем загрузку одного файла
    test_files = glob.glob(os.path.join(analyzer.data_folder, "TQBR.*_D1.txt"))
    if test_files:
        test_file = test_files[0]
        print(f"\nТестируем загрузку файла: {test_file}")
        
        # Показываем содержимое файла
        analyzer.debug_file_format(test_file, max_lines=3)
        
        # Пробуем загрузить данные
        df = analyzer.load_stock_data(test_file)
        if df is not None:
            print(f"Успешно загружено {len(df)} записей")
            print(f"Диапазон дат: {df.index.min()} - {df.index.max()}")
            print(f"Колонки: {list(df.columns)}")
            print(f"Первые 3 записи:")
            print(df.head(3))
        else:
            print("Ошибка загрузки данных")
            exit(1)
    
    # Запускаем полный анализ
    result_file = analyzer.run_analysis()
    
    if result_file:
        print(f"Результаты сохранены в файл: {result_file}")
        
        # Показываем результат
        try:
            df = pd.read_csv(result_file)
            print("\nРезультат:")
            print(df.head())
        except Exception as e:
            print(f"Ошибка чтения результата: {e}")
    else:
        print("Анализ не задался")