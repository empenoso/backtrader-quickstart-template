# utils/sortino_analyzer.py

# 📉 Анализатор: Коэффициент Сортино 📉
#
# Этот модуль добавляет в систему возможность рассчитывать Коэффициент Сортино — продвинутый
# финансовый показатель для оценки эффективности торговой стратегии с поправкой на "плохой" риск.
# В отличие от других метрик, он учитывает только просадки портфеля, а не общую волатильность,
# что дает более точную оценку доходности на единицу риска потерь.
#
# Функционал:
# - Интегрируется в движок Backtrader как кастомный анализатор.
# - Отслеживает доходность портфеля на каждом шаге симуляции.
# - Рассчитывает только негативные колебания доходности (риск потерь).
# - Вычисляет Коэффициент Сортино, который показывает, насколько хорошо стратегия вознаграждает за принятый риск.
# - Результат расчета автоматически включается в итоговый отчет по бэктесту.
#
# Автор: Михаил Шардин https://shardin.name/
# Дата создания: 10.08.2025
# Версия: 1.0
# Новая версия всегда здесь: https://github.com/empenoso/backtrader-quickstart-template/
#
# Этот файл не требует изменений и используется автоматически при генерации отчетов.
#

import math
import backtrader as bt
import numpy as np

class SortinoRatio(bt.Analyzer):
    """
    Analyzer для коэффициента Сортино.
    Параметры (через cerebro.addanalyzer):
      - riskfreerate: годовая безрисковая ставка (в долях, например 0.01 = 1%)
      - periods_per_year: число периодов в году (252 для дневных баров)
      - mar: минимально приемлемая годовая доходность (annual), по умолчанию 0.0
    Возвращает dict с ключами:
      - sortino, annual_return, downside_deviation, n_periods
    """
    params = dict(
        riskfreerate=0.0,
        periods_per_year=252,
        mar=0.0
    )

    def __init__(self):
        self.equity = []
        self.prev_val = None

    def start(self):
        # инициализация, если хотим что-то в будущем
        pass

    def next(self):
        # собираем значение портфеля в каждом баре
        cur = self.strategy.broker.getvalue()
        if self.prev_val is None:
            self.prev_val = cur
            return
        # считаем периодный (например, дневной) доход
        r = (cur / self.prev_val) - 1.0
        self.equity.append(r)
        self.prev_val = cur

    def stop(self):
        res = {'sortino': None, 'annual_return': None, 'downside_deviation': None, 'n_periods': len(self.equity)}
        if not self.equity:
            self.rets = res
            return

        returns = np.array(self.equity, dtype=float)
        n = len(returns)
        # годовая геометрическая доходность
        total_growth = (1.0 + returns).prod()
        if total_growth <= 0:
            annual_return = -1.0
        else:
            annual_return = total_growth ** (self.p.periods_per_year / n) - 1.0

        # переводим годовой MAR / riskfree в периодную величину
        mar_period = (1.0 + self.p.mar) ** (1.0 / self.p.periods_per_year) - 1.0
        rf_annual = float(self.p.riskfreerate)

        # downside deviations: отклонения ниже MAR (period)
        downside = np.minimum(0.0, returns - mar_period)
        # среднее квадратичное берём по всем периодам (N) -> более стандартный вариант
        mean_sq = np.mean(downside ** 2)
        downside_dev = math.sqrt(mean_sq) * math.sqrt(self.p.periods_per_year)

        numerator = annual_return - rf_annual
        sortino = None
        if downside_dev > 0:
            sortino = numerator / downside_dev
        else:
            # нет даунсайд-волатильности
            sortino = float('inf') if numerator > 0 else None

        res.update({
            'sortino': None if sortino is None else float(sortino),
            'annual_return': float(annual_return),
            'downside_deviation': float(downside_dev),
            'n_periods': n
        })
        self.rets = res

    def get_analysis(self):
        return self.rets
