# strategies/sma_cross_strategy.py

# 📈 Стратегия "Пересечение скользящих средних" 📈
#
# Этот файл содержит конкретную торговую стратегию, основанную на популярном техническом индикаторе
# "пересечение скользящих средних" (SMA Crossover). Стратегия анализирует график цены и принимает
# решения о покупке или продаже на основе пересечения двух линий: быстрой и медленной средней цены.
#
# Функционал:
# - Реализует полную торговую логику на основе пересечения двух SMA.
# - Определяет параметры специально для этой стратегии: список акций для торговли, начальный капитал.
# - Рассчитывает две скользящие средние: быструю (короткий период) и медленную (длинный период).
# - Генерирует сигнал на ПОКУПКУ, когда быстрая линия пересекает медленную снизу вверх ("золотой крест").
# - Генерирует сигнал на ПРОДАЖУ (закрытие позиции), когда быстрая линия пересекает медленную сверху вниз ("крест смерти").
# - Содержит параметры по умолчанию для одиночного теста и диапазоны для режима оптимизации (поиска лучших периодов).
#
# Автор: Михаил Шардин https://shardin.name/
# Дата создания: 10.08.2025
# Версия: 1.0
# Новая версия всегда здесь: https://github.com/empenoso/backtrader-quickstart-template/
#
# Имя этой стратегии ('SmaCrossStrategy') нужно указывать в main.py для ее запуска.
#

import backtrader as bt
from .base_strategy import BaseStrategy

class SmaCrossStrategy(BaseStrategy):
    # --- Конфигурация ---
    tickers = ['TQBR.SBER_D1.txt']  # Тестируем на Сбере
    start_cash = 500_000.0
    commission = 0.001

    # Параметры по умолчанию для бэктеста
    params = (
        ('fast_ma', 10),
        ('slow_ma', 50),
    )
    
    # Параметры для оптимизации (ровно два!)
    opt_params = {
        'fast_ma': range(5, 21, 5),   # от 5 до 20 с шагом 5
        'slow_ma': range(30, 61, 10) # от 30 до 60 с шагом 10
    }

    def __init__(self):
        super().__init__()
        self.crossover = {}
        for d in self.datas:
            fast_sma = bt.indicators.SimpleMovingAverage(d.close, period=self.p.fast_ma)
            slow_sma = bt.indicators.SimpleMovingAverage(d.close, period=self.p.slow_ma)
            self.crossover[d._name] = bt.indicators.CrossOver(fast_sma, slow_sma)

    def next(self):
        for d in self.datas:
            pos = self.getposition(d)
            if not pos:  # Если нет открытой позиции
                if self.crossover[d._name][0] > 0:  # Быстрая MA пересекла медленную снизу вверх
                    self.buy(data=d, size=100)
            else:  # Если есть открытая позиция
                if self.crossover[d._name][0] < 0:  # Быстрая MA пересекла медленную сверху вниз
                    self.close(data=d)