# strategies/sma_cross_strategy.py

# 📈 Стратегия "Пересечение скользящих средних" — асинхронная версия
#
# Полностью переработанная версия, адаптированная для асинхронного режима Backtrader
# (runonce=False, preload=False, oldsync=False, exactbars=-1).
#
# Основные идеи и улучшения:
# - Параметры заданы через params = dict(...) для удобства и гибкости.
# - Индикаторы создаются для каждого data feed, но в next используются только "живые" данные.
# - Защита работы в prenext/nextstart: стратегия корректно работает если разные бумаги
#   начинают поставлять котировки в разное время.
# - Капитал и аллокация пересчитываются в момент торговли в зависимости от числа доступных инструментов.
# - Логирование подключения инструмента однократно.
# - Простая и предсказуемая логика открытия/закрытия позиций на пересечении SMA.
#
# Автор: Михаил Шардин https://shardin.name/
# Дата: 2025-08-21
# Версия: 1.3
#

import math
import collections
import backtrader as bt
from .base_strategy import BaseStrategy


class SmaCrossStrategy(BaseStrategy):
    """
    SMA Crossover strategy — асинхронная версия.

    Стратегия работает отдельно для каждого data feed и начинает торговать по инструменту
    с того момента, когда для него накопилось достаточно баров для расчёта индикаторов.
    """

    # --- Параметры стратегии (удобно оптимизировать/переопределять) ---
    params = dict(
        fast_ma=20,
        slow_ma=50,
        alloc_percent_per_ticker=0.90,  # доля выделяемого капитала на тикер
        min_size=1,                     # минимальный лот/штука для открытия позиции
        rebal_weekday=None,             # если нужно использовать таймеры, задать 0..6 (Mon..Sun), None — отключено
        log_on_connect=True,            # логировать подключение инструмента
    )

    # Список тикеров и базовые финансовые параметры (берутся из BaseStrategy, но можно переопределить)
    tickers = [
        'SBER', 'VTBR', 'GAZP', 'LKOH', 'NVTK', 'YDEX', 'T'
    ]
    start_cash = 500_000.0
    commission = 0.001

    # Параметры для оптимизации (должно быть ровно 2 ключа для генерации тепловой карты в main.py)
    opt_params = {
        'fast_ma': range(5, 21, 5),
        'slow_ma': range(30, 61, 10),
    }

    def __init__(self):
        super().__init__()

        # ---- структуры данных ----
        # Индикаторы для каждого data feed
        self.inds = collections.defaultdict(dict)

        # Список data feeds, которые уже "живут" (накопили минимально необходимое число баров)
        self.d_with_len = []  # будет заполняться в prenext / nextstart

        # Множество data feeds, которые мы уже логировали как "подключённые"
        self.live_logged = set()

        # кеш минимальных периодов для каждого data
        self.min_periods = {}

        # Кэш для расчёта капитала на тикер (пересчитывается при необходимости)
        self._capital_per_active_ticker = None
        self._capital_calc_for_len = None  # длина, для которой посчитан кэш

        # создаём индикаторы для каждого data (они будут возвращать nan до накопления данных)
        for d in self.datas:
            # индикаторы создаём в общем виде, чтобы Backtrader следил за их буферами
            self.inds[d]['fast_sma'] = bt.ind.SMA(d.close, period=self.p.fast_ma)
            self.inds[d]['slow_sma'] = bt.ind.SMA(d.close, period=self.p.slow_ma)
            self.inds[d]['crossover'] = bt.ind.CrossOver(self.inds[d]['fast_sma'],
                                                         self.inds[d]['slow_sma'],
                                                         plot=False)

            # минимальный период данных для этого инструмента
            self.min_periods[d] = max(int(self.p.fast_ma), int(self.p.slow_ma))

        # если нужен таймер — добавим его (опционально)
        if self.p.rebal_weekday is not None:
            # таймер вызывает notify_timer по расписанию; можно использовать для периодического ребаланса
            self.add_timer(when=bt.Timer.SESSION_START,
                           weekdays=[self.p.rebal_weekday],
                           weekcarry=True)

    # -------------------------
    # Хуки для асинхронных данных
    # -------------------------
    def prenext(self):
        """
        Вызывается когда ещё не все гарантии (т.е. не все индикаторы/данные готовые),
        но некоторые данные уже приходят. Сохраняем список доступных data и делегируем в next.
        """
        # Сохраняем data feeds, у которых len > 0
        self.d_with_len = [d for d in self.datas if len(d)]
        # Сбрасываем кэш капитала, т.к. число активных инструментов изменилось
        self._capital_per_active_ticker = None
        # Делаем торговую логику (защищённую внутри next)
        self.next()

    def nextstart(self):
        """
        Вызывается ровно один раз, когда все гарантии выполнены впервые.
        Здесь мы считаем, что все data feeds "доступны".
        """
        # Теперь все данные соответствуют требованиям
        self.d_with_len = list(self.datas)
        self._capital_per_active_ticker = None
        self.next()

    # -------------------------
    # Вспомогательные функции
    # -------------------------
    def _ensure_capital_per_ticker(self):
        """
        Вычисляет и кэширует капитал, выделяемый на каждый *активный* тикер.
        Переоценивается автоматически, если число активных инструментов изменилось.
        """
        active_n = max(1, len(self.d_with_len) if len(self.d_with_len) else len(self.datas))
        if self._capital_per_active_ticker is not None and self._capital_calc_for_len == active_n:
            return

        cash = float(self.broker.getcash()) if self.broker.getcash() is not None else float(self.start_cash)
        # делим текущие наличные на число активных инструментов
        capital_per = cash / float(active_n)
        self._capital_per_active_ticker = capital_per
        self._capital_calc_for_len = active_n
        self.log(f"[CAPITAL] cash={cash:.2f}, active_n={active_n}, capital_per_ticker={capital_per:.2f}")

    def _data_ready(self, d):
        """
        Проверка готовности конкретного data feed для торговли:
        - len(d) >= минимального требуемого значения
        - индикаторы дали значения (не NaN)
        - текущая цена положительна
        """
        try:
            # данные должны быть вообще
            if len(d) < 1:
                return False

            # минимальная длина для расчёта индикаторов
            if len(d) < self.min_periods.get(d, 0):
                return False

            # текущее значение цены
            price = d.close[0]
            if price is None or price <= 0 or (isinstance(price, float) and math.isnan(price)):
                return False

            # индикаторы: fast and slow SMA и crossover
            fast = self.inds[d]['fast_sma'][0]
            slow = self.inds[d]['slow_sma'][0]
            xo = self.inds[d]['crossover'][0]

            # Проверяем на NaN (Backtrader может вернуть float('nan') до заполнения)
            for v in (fast, slow, xo):
                if v is None:
                    return False
                if isinstance(v, float) and math.isnan(v):
                    return False

            return True

        except Exception:
            # безопасно отлавливаем любые ошибки доступа к data/индикаторам
            return False

    # -------------------------
    # Основной цикл (защищённый)
    # -------------------------
    def next(self):
        """
        Основная логика — работает только с self.d_with_len (подмножество доступных данных).
        Все вычисления защищены и не предполагают одинаковой длины data feeds.
        """
        # Обновляем список доступных data feeds на каждом шаге (пристаревшая записанная d_with_len могло измениться)
        # — но делаем это быстро, используя len(d)
        current_available = [d for d in self.datas if len(d)]
        # если список изменился — обновим кэш и уведомим
        if set(current_available) != set(self.d_with_len):
            self.d_with_len = current_available
            self._capital_per_active_ticker = None  # пересчитать капитал
        # Убедимся, что вычислен капитал для текущего набора активных тикеров
        self._ensure_capital_per_ticker()

        # Перебираем только те data feeds, которые готовы к торговле
        for d in list(self.d_with_len):
            # защита: есть ли достаточно данных и индикаторов для этого инструмента
            if not self._data_ready(d):
                continue

            # логируем факт "подключения" инструмента только один раз
            if self.p.log_on_connect and d not in self.live_logged:
                self.live_logged.add(d)
                try:
                    current_date = bt.num2date(d.datetime[0]).strftime('%Y-%m-%d')
                except Exception:
                    current_date = str(d.datetime[0])
                self.log(f"[ADD] {getattr(d, '_name', 'unknown')} подключен к торгам с {current_date}")

            # значения индикаторов
            xo = self.inds[d]['crossover'][0]
            fast = self.inds[d]['fast_sma'][0]
            slow = self.inds[d]['slow_sma'][0]

            # текущая цена и позиция
            price = d.close[0]
            pos = self.getposition(d)

            # Торговая логика: простое пересечение SMA
            # открываем длинную позицию при пересечении снизу-вверх
            if pos.size == 0:
                if xo > 0:
                    self._execute_buy_signal(d, price)
            else:
                # закрываем позицию при пересечении сверху-вниз
                if xo < 0:
                    self._execute_sell_signal(d, price, pos)

    # -------------------------
    # Исполнение ордеров
    # -------------------------
    def _execute_buy_signal(self, data, price):
        """Исполняет сигнал на покупку для одного инструмента."""
        try:
            alloc = float(self._capital_per_active_ticker) * float(self.p.alloc_percent_per_ticker)
            size = int(alloc / price) if price > 0 else 0

            if size < int(self.p.min_size):
                self.log(f"[BUY SKIP] {getattr(data,'_name','unknown')} — недостаточный size (price={price:.2f}, alloc={alloc:.2f}, size={size})")
                return

            self.log(f"[BUY] {getattr(data,'_name','unknown')} price={price:.2f} size={size} alloc={alloc:.2f}")
            self.buy(data=data, size=size)

        except Exception as e:
            self.log(f"[ERROR BUY] {getattr(data,'_name','unknown')}: {e}")

    def _execute_sell_signal(self, data, price, position):
        """Закрытие позиции по инструменту."""
        try:
            self.log(f"[SELL] {getattr(data,'_name','unknown')} closing size={position.size} price={price:.2f}")
            self.close(data=data)
        except Exception as e:
            self.log(f"[ERROR SELL] {getattr(data,'_name','unknown')}: {e}")

    # -------------------------
    # notify hooks
    # -------------------------
    def notify_order(self, order):
        """Расширенное логирование статусов ордера."""
        super().notify_order(order)

        # стандартная обработка уже выполнена в BaseStrategy; добавим дополнительные строки при необходимости
        if order.status in [order.Completed]:
            dname = getattr(order.data, '_name', 'unknown')
            if order.isbuy():
                # order.executed.price / .size / .value / .comm обычно доступны
                self.log(f"[ORDER DONE BUY] {dname} price={order.executed.price:.2f} size={getattr(order.executed, 'size', 'n/a')}")
            elif order.issell():
                self.log(f"[ORDER DONE SELL] {dname} price={order.executed.price:.2f} size={getattr(order.executed, 'size', 'n/a')}")

    def notify_trade(self, trade):
        """Логирование закрытых сделок."""
        super().notify_trade(trade)
        if trade.isclosed:
            dname = getattr(trade.data, '_name', 'unknown') if hasattr(trade, 'data') else 'unknown'
            self.log(f"[TRADE CLOSED] {dname} GROSS {trade.pnl:.2f} NET {trade.pnlcomm:.2f}")

    def notify_timer(self, timer, when, *args, **kwargs):
        """
        Если активирован таймер (rebal_weekday), можно реализовать периодические действия.
        По умолчанию — просто логируем событие и оставляем возможность расширить поведение.
        """
        try:
            self.log(f"[TIMER] when={when} timer={timer} args={args} kwargs={kwargs}")
            # Пример: можно вызывать ребаланс/функции раз в неделю здесь.
        except Exception as e:
            self.log(f"[TIMER ERROR] {e}")
