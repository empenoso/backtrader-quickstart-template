# strategies/sma_cross_strategy.py

# 📈 Стратегия "Пересечение скользящих средних" 📈
#
# Исправленная версия для корректной работы в асинхронном режиме (runonce=False)
#
# Версия: 1.2 (исправлена для асинхронной загрузки данных)

import math
import backtrader as bt
from .base_strategy import BaseStrategy


class SmaCrossStrategy(BaseStrategy):
    """
    SMA Crossover strategy — версия для мульти-инструментных бэктестов
    с асинхронной обработкой данных (runonce=False).

    Основные исправления:
    - Добавлена проверка доступности данных на каждом баре
    - Улучшена логика определения "живых" инструментов
    - Добавлена защита от работы с недоступными данными
    - Оптимизирована инициализация капитала per ticker
    """

    # --- Конфигурация (можно менять) ---
    tickers = [
        'SBER','VTBR','GAZP','LKOH','NVTK', 'YDEX'
    ]

    start_cash = 500_000.0
    commission = 0.001

    # Параметры стратегии (можно оптимизировать)
    params = (
        ('fast_ma', 20),
        ('slow_ma', 50),
        # процент капитала, который будет использован на один тикер при открытии позиции
        ('alloc_percent_per_ticker', 0.90),  # 90% от выделенной доли на тикер
        # минимальный допустимый размер (в бумагах/лотах), если цена очень высока
        ('min_size', 1),
    )

    # Параметры для оптимизации (2 параметра обязательно если используете OPTIMIZATION)
    opt_params = {
        'fast_ma': range(5, 21, 5),
        'slow_ma': range(30, 61, 10),
    }

    def __init__(self):
        super().__init__()

        # Количество подключённых data feeds
        self.n_data = max(1, len(self.datas))

        # Словарь для хранения индикаторов, привязанных к каждому data feed
        self.indicators = {}
        
        # Множество для отслеживания бумаг, по которым уже пошли данные
        self.live_datas = set()
        
        # Словарь для отслеживания минимальной длины данных для начала торговли
        self.min_periods = {}

        for d in self.datas:
            # Создаём индикаторы и сохраняем их в словарь по ключу `d` (объект data)
            self.indicators[d] = {
                'fast_sma': bt.indicators.SimpleMovingAverage(d.close, period=self.p.fast_ma),
                'slow_sma': bt.indicators.SimpleMovingAverage(d.close, period=self.p.slow_ma),
            }
            # Crossover создаем на основе уже созданных SMA для этого же data feed
            self.indicators[d]['crossover'] = bt.indicators.CrossOver(
                self.indicators[d]['fast_sma'],
                self.indicators[d]['slow_sma'],
                plot=False
            )
            
            # Определяем минимальный период для начала торговли по этому инструменту
            self.min_periods[d] = max(self.p.fast_ma, self.p.slow_ma)

        # Кэш капитала на тикер
        self._capital_per_ticker = None

    def _ensure_capital_per_ticker(self):
        """Вычисляем, сколько капитала выделить на каждый тикер."""
        if self._capital_per_ticker is not None:
            return

        cash = float(self.broker.getcash()) if self.broker.getcash() > 0 else float(self.start_cash)
        self._capital_per_ticker = cash / float(self.n_data)
        self.log(f"[INIT] n_data={self.n_data}, cash={cash:.2f}, capital_per_ticker={self._capital_per_ticker:.2f}")

    def _is_data_ready(self, data):
        """
        Проверяет, готов ли инструмент для торговли:
        - Есть ли данные на текущем баре
        - Достаточно ли исторических данных для индикаторов
        """
        try:
            # Проверяем, что текущий бар существует
            current_price = data.close[0]
            if math.isnan(current_price) or current_price <= 0:
                return False
                
            # Проверяем, что накоплено достаточно данных для индикаторов
            data_len = len(data)
            min_required = self.min_periods.get(data, max(self.p.fast_ma, self.p.slow_ma))
            if data_len < min_required:
                return False
                
            # Проверяем, что индикаторы рассчитались корректно
            fast_sma = self.indicators[data]['fast_sma'][0]
            slow_sma = self.indicators[data]['slow_sma'][0]
            crossover = self.indicators[data]['crossover'][0]
            
            if math.isnan(fast_sma) or math.isnan(slow_sma) or math.isnan(crossover):
                return False
                
            return True
            
        except (IndexError, KeyError) as e:
            # Данные недоступны на текущем баре
            return False

    def next(self):
        """Основной метод торговой логики."""
        # Убедимся, что у нас есть значение капитала на тикер
        self._ensure_capital_per_ticker()

        for d in self.datas:
            # Проверяем, готов ли инструмент для торговли
            if not self._is_data_ready(d):
                continue

            # Логируем подключение новой бумаги (только один раз)
            if d not in self.live_datas:
                self.live_datas.add(d)
                current_date = bt.num2date(d.datetime[0]).strftime('%Y-%m-%d')
                self.log(f"[ADD] {d._name} подключен к торгам с {current_date}")

            # Получаем значения индикаторов
            crossover_val = self.indicators[d]['crossover'][0]
            fast_sma = self.indicators[d]['fast_sma'][0]
            slow_sma = self.indicators[d]['slow_sma'][0]
            
            # Получаем текущую позицию и цену
            pos = self.getposition(d)
            price = d.close[0]

            # Торговая логика
            if pos.size == 0:
                # Нет позиции - проверяем сигнал на покупку
                if crossover_val > 0:  # Быстрая SMA пересекла медленную снизу вверх
                    self._execute_buy_signal(d, price)
            else:
                # Есть позиция - проверяем сигнал на закрытие
                if crossover_val < 0:  # Быстрая SMA пересекла медленную сверху вниз
                    self._execute_sell_signal(d, price, pos)

    def _execute_buy_signal(self, data, price):
        """Исполняет сигнал на покупку."""
        try:
            alloc = self._capital_per_ticker * float(self.p.alloc_percent_per_ticker)
            size = int(alloc / price)

            if size < int(self.p.min_size):
                self.log(f"Недостаточно средств для покупки {data._name}: "
                        f"price={price:.2f}, alloc={alloc:.2f}, size={size}")
                return

            self.log(f"BUY SIGNAL for {data._name}: price={price:.2f}, size={size}, alloc={alloc:.2f}")
            order = self.buy(data=data, size=size)
            
        except Exception as e:
            self.log(f"Ошибка при выполнении покупки {data._name}: {e}")

    def _execute_sell_signal(self, data, price, position):
        """Исполняет сигнал на продажу (закрытие позиции)."""
        try:
            self.log(f"SELL SIGNAL for {data._name}: closing position size={position.size} at price={price:.2f}")
            order = self.close(data=data)
            
        except Exception as e:
            self.log(f"Ошибка при закрытии позиции {data._name}: {e}")

    def notify_order(self, order):
        """Логирование статуса ордера."""
        super().notify_order(order)
        
        if order.status in [order.Completed]:
            data_name = getattr(order.data, '_name', 'unknown')
            if order.isbuy():
                self.log(f"BUY EXECUTED, Price: {order.executed.price:.2f}, "
                        f"Cost: {order.executed.value:.2f}, "
                        f"Comm: {order.executed.comm:.2f}")
                self.log(f"ORDER COMPLETED BUY for {data_name}: "
                        f"price={order.executed.price:.2f}, size={order.executed.size}")
            elif order.issell():
                self.log(f"SELL EXECUTED, Price: {order.executed.price:.2f}, "
                        f"Cost: {order.executed.value:.2f}, "
                        f"Comm: {order.executed.comm:.2f}")
                self.log(f"ORDER COMPLETED SELL for {data_name}: "
                        f"price={order.executed.price:.2f}, size={order.executed.size}")

    def notify_trade(self, trade):
        """Логирование завершенных сделок."""
        super().notify_trade(trade)
        
        if trade.isclosed:
            data_name = getattr(trade.data, '_name', 'unknown') 
            self.log(f'OPERATION PROFIT for {data_name}, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}')