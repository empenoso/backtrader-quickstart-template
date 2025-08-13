# strategies/base_strategy.py

# 🧱 Базовый шаблон для торговых стратегий 🧱
#
# Этот файл является "фундаментом" или "шаблоном", на основе которого строятся все торговые стратегии.
# Он задает общие правила и определяет, какие обязательные параметры (начальный капитал, комиссия)
# и функции должна содержать каждая стратегия. Это обеспечивает единообразие и упрощает
# создание новых торговых алгоритмов.
#
# Функционал:
# - Определяет общую структуру для всех стратегий.
# - Устанавливает обязательные для заполнения поля: список акций ('tickers'), начальный капитал, комиссия.
# - Предоставляет общие вспомогательные функции, например, для логирования информации о сделках.
# - Гарантирует, что все новые стратегии будут совместимы с основной системой.
#
# Автор: Михаил Шардин https://shardin.name/
# Дата создания: 10.08.2025
# Версия: 1.0
# Новая версия всегда здесь: https://github.com/empenoso/backtrader-quickstart-template/
#
# Этот файл не содержит торговой логики, а лишь задает каркас для других стратегий.
#

import backtrader as bt

class BaseStrategy(bt.Strategy):
    """
    Базовый класс для всех стратегий.
    Определяет обязательные атрибуты, которые должны быть установлены в дочерних классах.
    """
    # --- КОНФИГУРАЦИЯ СТРАТЕГИИ (должна быть переопределена в дочерних классах) ---
    tickers = []  # Список тикеров для тестирования, e.g., ['TQBR.SBER_D1.txt']
    start_cash = 1_000_000.0  # Начальный капитал
    commission = 0.001  # Комиссия брокера (0.1%)
    
    # Параметры для оптимизации. ДОЛЖНО БЫТЬ РОВНО ДВА ПАРАМЕТРА для построения тепловой карты.
    # e.g. opt_params = {'fast_ma': range(5, 15), 'slow_ma': range(20, 50)}
    opt_params = {}

    def __init__(self):
        """Логика, общая для всех стратегий, может быть здесь."""
        # Можно добавить логирование или общие индикаторы
        pass

    def log(self, txt, dt=None):
        """Вспомогательная функция для логирования"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} | {txt}')

    # --- МЕТОДЫ, КОТОРЫЕ НУЖНО РЕАЛИЗОВАТЬ В ДОЧЕРНИХ СТРАТЕГИЯХ ---
    def next(self):
        """
        Этот метод должен быть реализован в каждой конкретной стратегии.
        Содержит основную логику принятия решений.
        """
        raise NotImplementedError("Метод `next` должен быть реализован в дочерней стратегии.")

    def notify_order(self, order):
        """Обработка статуса ордера"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

    def notify_trade(self, trade):
        """Обработка закрытия сделки"""
        if not trade.isclosed:
            return
        self.log(f'OPERATION PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}')