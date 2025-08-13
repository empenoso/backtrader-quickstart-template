# utils/report_generator.py

# 📊 Генератор отчетов и графиков 📊
#
# Этот модуль отвечает за создание подробных и наглядных отчетов по итогам тестирования стратегий.
# Он преобразует сухие цифры из симуляции в понятные человеку текстовые отчеты, а для режима
# оптимизации дополнительно строит "тепловую карту" — график, который помогает визуально определить
# самые прибыльные параметры для стратегии.
#
# Функционал:
# - Для одиночного теста (бэктеста):
#   - Расчет ключевых показателей: итоговая прибыль, годовая доходность, максимальная просадка, процент прибыльных сделок, фактор прибыли и коэффициент Сортино.
#   - Сравнение результата стратегии с подходом "купил и держи".
#   - Сохранение итогового отчета в текстовый файл в папку 'reports'.
# - Для оптимизации:
#   - Создание таблицы с результатами для каждой комбинации параметров.
#   - Построение и сохранение "тепловой карты" (.png), где цветом выделены наиболее удачные параметры.
#   - Сохранение отчета и графика в папку 'reports'.
#
# Автор: Михаил Шардин https://shardin.name/
# Дата создания: 10.08.2025
# Версия: 1.0
# Новая версия всегда здесь: https://github.com/empenoso/backtrader-quickstart-template/
#
# Этот файл работает автоматически после завершения тестирования в main.py.
#

import os
import datetime
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

def generate_backtest_report(strategy_result, strategy_name, from_date, to_date, reports_dir):
    """Генерирует и сохраняет текстовый отчет по результатам бэктеста."""
    p = getattr(strategy_result, 'params', None)
    
    # Анализаторы (безопасно)
    try:
        analyzer = strategy_result.analyzers.trade_analyzer.get_analysis()
    except Exception:
        analyzer = None
    try:
        drawdown = strategy_result.analyzers.drawdown.get_analysis()
    except Exception:
        drawdown = None
    try:
        returns = strategy_result.analyzers.returns.get_analysis()
    except Exception:
        returns = {}
    try:
        sortino_data = strategy_result.analyzers.sortino.get_analysis() or {}
    except Exception:
        sortino_data = {}

    sortino_value = sortino_data.get('sortino', None)

    # Сделки
    total_closed_trades = getattr(analyzer, 'total', None)
    total_closed_trades = (total_closed_trades.closed if total_closed_trades is not None else 0) if analyzer else 0
    won_trades = (analyzer.won.total if analyzer and getattr(analyzer, 'won', None) else 0)
    lost_trades = (analyzer.lost.total if analyzer and getattr(analyzer, 'lost', None) else 0)

    # Начальный и конечный капитал
    initial_value = getattr(strategy_result.broker, 'startingcash', None)
    final_value = strategy_result.broker.getvalue()
    pnl = (final_value - initial_value) if initial_value is not None else None
    
    # Расчет процента от начального капитала
    pnl_percent = (pnl / initial_value * 100) if (pnl is not None and initial_value is not None and initial_value != 0) else 0.0

    # Расчет Buy and Hold: корректно извлекаем первый и последний close из первого датасета
    buy_and_hold_return = None
    buy_and_hold_absolute = None
    try:
        data = strategy_result.datas[0]
        n_bars = len(data)
        if n_bars >= 1:
            # Первый close: индекс - (n_bars-1)
            first_idx = -(n_bars - 1)
            first_close = data.close[first_idx]
            last_close = data.close[0]
            if first_close != 0:
                buy_and_hold_return = (last_close - first_close) / first_close
                # Абсолютное значение buy and hold в денежном эквиваленте
                buy_and_hold_absolute = initial_value * buy_and_hold_return if initial_value else 0
    except Exception:
        buy_and_hold_return = None
        buy_and_hold_absolute = None

    # Расчет Profit Factor
    gross_profit = (analyzer.won.pnl.total if analyzer and getattr(analyzer, 'won', None) else 0)
    gross_loss = abs((analyzer.lost.pnl.total if analyzer and getattr(analyzer, 'lost', None) else 0))
    profit_factor = gross_profit / gross_loss if gross_loss != 0 else (float('inf') if gross_profit > 0 else 0.0)

    # Win rate
    win_rate = (won_trades / total_closed_trades * 100) if total_closed_trades else 0.0

    # Максимальная просадка в абсолютных значениях
    max_drawdown_percent = (drawdown.max.drawdown if drawdown and getattr(drawdown, 'max', None) else 0.0)
    max_drawdown_absolute = initial_value * (max_drawdown_percent / 100) if initial_value else 0.0

    # Форматирование Sortino безопасно
    def fmt_sortino(v):
        if v is None:
            return "N/A"
        if v == float('inf'):
            return "inf"
        return f"{v:.2f}"
    
    # Функция для форматирования денежных сумм с разделителем тысяч
    def fmt_money(value):
        if value is None:
            return "N/A"
        # Форматируем с пробелами как разделителями тысяч
        return f"{value:,.2f}".replace(',', ' ')
    
    # Функция для форматирования buy and hold
    def fmt_buy_hold():
        if buy_and_hold_return is None or buy_and_hold_absolute is None:
            return "Результат 'Купил и держал': N/A"
        return f"Результат 'Купил и держал': {fmt_money(buy_and_hold_absolute)} [{buy_and_hold_return * 100:.2f}%]"

    report_lines = [
        f"--- ОТЧЕТ ПО БЭКТЕСТУ СТРАТЕГИИ: {strategy_name} ---",
        f"Параметры: {p}",
        f"Период тестирования: с {from_date.strftime('%d.%m.%Y')} по {to_date.strftime('%d.%m.%Y')}",
        "--- РЕЗУЛЬТАТЫ ---",
        f"Итоговая прибыль/убыток: {fmt_money(pnl)} [{pnl_percent:.2f}%]" if pnl is not None else "Итоговая прибыль/убыток: N/A",
        f"Доходность (годовых): {returns.get('rnorm100', 0.0):.2f}%",
        fmt_buy_hold(),
        f"Максимальная просадка: {fmt_money(max_drawdown_absolute)} [{max_drawdown_percent:.2f}%]",
        f"Всего сделок: {total_closed_trades}",
        f"Процент прибыльных сделок: {win_rate:.2f}% ({won_trades} из {total_closed_trades})",
        f"Фактор прибыли: {profit_factor:.2f}" if profit_factor not in (float('inf'), None) else f"Фактор прибыли: {'inf' if profit_factor==float('inf') else 'N/A'}",
        f"Коэффициент Сортино: {fmt_sortino(sortino_value)}",
        "--------------------------------------------------"
    ]
    
    # Убираем None-строки
    report_lines = [r for r in report_lines if r is not None]

    report_content = "\n".join(report_lines)
    print(report_content)

    # Сохранение отчета
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
    period_str = f"{from_date.strftime('%Y%m%d')}-{to_date.strftime('%Y%m%d')}"
    filename = f"{strategy_name}_test_{timestamp}_{period_str}.txt"
    filepath = os.path.join(reports_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(report_content)
    print(f"\nОтчет сохранен в: {filepath}")


def generate_optimization_report(results, strategy_name, opt_param_names, from_date, to_date, reports_dir):
    """Генерирует и сохраняет отчет по оптимизации и тепловую карту."""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
    period_str = f"{from_date.strftime('%Y%m%d')}-{to_date.strftime('%Y%m%d')}"
    
    # --- 1. Текстовый отчет ---
    txt_filename = f"{strategy_name}_opt_{timestamp}_{period_str}.txt"
    txt_filepath = os.path.join(reports_dir, txt_filename)

    with open(txt_filepath, 'w', encoding='utf-8') as f:
        f.write(f"--- РЕЗУЛЬТАТЫ ОПТИМИЗАЦИИ СТРАТЕГИИ: {strategy_name} ---\n")
        f.write(f"Параметры для оптимизации: {', '.join(opt_param_names)}\n\n")
        
        # Заголовок таблицы
        header = f"{opt_param_names[0]:<10} | {opt_param_names[1]:<10} | {'ProfitFactor':<15} | {'TotalTrades':<12}\n"
        f.write(header)
        f.write("-" * len(header) + "\n")
        
        opt_data = []
        for run in results:
            strategy = run[0]  # Берем одну стратегию из каждого прогона
            params = strategy.p
            analyzer = strategy.analyzers.trade_analyzer.get_analysis()
            
            gross_profit = analyzer.won.pnl.total or 0
            gross_loss = abs(analyzer.lost.pnl.total or 0)
            profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
            total_trades = analyzer.total.closed or 0
            
            p1_val = getattr(params, opt_param_names[0])
            p2_val = getattr(params, opt_param_names[1])
            
            f.write(f"{p1_val:<10} | {p2_val:<10} | {profit_factor:<15.2f} | {total_trades:<12}\n")
            
            opt_data.append({
                opt_param_names[0]: p1_val,
                opt_param_names[1]: p2_val,
                'profit_factor': profit_factor
            })

    print(f"Отчет по оптимизации сохранен в: {txt_filepath}")

    # --- 2. Тепловая карта ---
    if not opt_data:
        print("Нет данных для построения тепловой карты.")
        return
        
    df = pd.DataFrame(opt_data)
    
    # Если фактор прибыли бесконечный, заменяем его на большое число для визуализации
    df['profit_factor'] = df['profit_factor'].replace([float('inf'), -float('inf')], 10)
    
    try:
        heatmap_data = df.pivot(index=opt_param_names[0], columns=opt_param_names[1], values='profit_factor')
        
        plt.figure(figsize=(12, 8))
        sns.heatmap(heatmap_data, annot=True, fmt=".2f", cmap="viridis")
        plt.title(f'Тепловая карта оптимизации для {strategy_name}\n(Фактор прибыли)')
        plt.xlabel(opt_param_names[1])
        plt.ylabel(opt_param_names[0])
        
        # Получаем имена тикеров из класса стратегии
        ticker_names = [os.path.splitext(ticker)[0] for ticker in strategy.__class__.tickers]
        tickers_str = "_".join(ticker_names)
        png_filename = f"{strategy_name}_opt_heatmap_{tickers_str}_{timestamp}_{period_str}.png"
        png_filepath = os.path.join(reports_dir, png_filename)
        
        plt.savefig(png_filepath)
        plt.close()  # Важно закрыть фигуру, чтобы не отображать ее в jupyter/etc.
        
        print(f"Тепловая карта сохранена в: {png_filepath}")

    except Exception as e:
        print(f"Не удалось построить тепловую карту: {e}")
        print("Возможно, у вас только один параметр для оптимизации или данные не подходят для сводной таблицы.")