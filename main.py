# main.py

# 🚀 Запуск бэктестинга и оптимизации торговых стратегий 🚀
#
# Этот Python скрипт является главным центром управления для тестирования и анализа торговых стратегий.
# Он позволяет пользователю выбрать режим работы (тестирование одной стратегии или поиск лучших параметров),
# указать торговую стратегию и временной период. Скрипт автоматически загружает исторические данные,
# проводит симуляцию торгов и генерирует подробные отчеты о результатах, сохраняя их в папку 'reports'.
#
# Функционал:
# - Главная "панель управления" для настройки параметров тестирования в одном месте.
# - Выбор режима: 'BACKTEST' (одиночный тест) или 'OPTIMIZATION' (поиск лучших параметров).
# - Выбор торговой стратегии из автоматически загруженного списка.
# - Настройка временного периода для тестирования и начального капитала.
# - Загрузка исторических данных для выбранных акций из папки 'data-connector/Data/Tinkoff/'.
# - Запуск симуляции торгов в движке Backtrader.
# - Генерация и сохранение отчетов: текстовый отчет для бэктеста, текстовый отчет и тепловая карта для оптимизации.
# - Подготовлена (но отключена) возможность подключения к реальному торговому счету в Тинькофф.
#
# Автор: Михаил Шардин https://shardin.name/
# Дата создания: 22.08.2025
# Версия: 1.3
# Новая версия всегда здесь: https://github.com/empenoso/backtrader-quickstart-template/
#
# Для запуска необходимо настроить параметры в секции "ГЛАВНАЯ ПАНЕЛЬ УПРАВЛЕНИЯ".
#

# --- Системные и стандартные библиотеки ---
import os
import sys
import datetime

# Это должно быть сделано ДО импорта backtrader или любого другого модуля,
import matplotlib as mpl
mpl.use('Agg')  # Говорим matplotlib, что мы будем только сохранять в файлы.
import matplotlib.pyplot as plt
# Принудительно устанавливаем backend для всех последующих импортов
plt.switch_backend('Agg')
from matplotlib.figure import Figure

# Теперь импортируем "тяжелые" библиотеки, которые зависят от matplotlib 
import backtrader as bt

# --- Настройка кодировки ---
sys.stdout.reconfigure(encoding='utf-8')

# --- Импорты из нашего проекта ---
import strategies
from utils.custom_csv import CustomCSVData
from utils.sortino_analyzer import SortinoRatio
from utils.report_generator import generate_backtest_report, generate_optimization_report

# --- Импорты для Live Trading (Tinkoff) ---
# Раскомментируйте, если будете использовать Live Trading
# from BackTraderTinkoff import TKStore
# import logging

# ======================================================================================
# --- ГЛАВНАЯ ПАНЕЛЬ УПРАВЛЕНИЯ ---
# ======================================================================================

# 1. ВЫБЕРИТЕ РЕЖИМ: 'BACKTEST' или 'OPTIMIZATION'
MODE = 'BACKTEST'

# 2. ВЫБЕРИТЕ СТРАТЕГИЮ из загруженных (см. вывод в консоли при запуске)
#    Имя должно точно совпадать с именем класса стратегии.
STRATEGY_TO_RUN = 'SmaCrossStrategy' 

# 3. НАСТРОЙКИ ПЕРИОДА ТЕСТИРОВАНИЯ
FROM_DATE = datetime.datetime(2018, 1, 1)
TO_DATE = datetime.datetime(2025, 8, 12)

# 4. НАСТРОЙКИ LIVE TRADING (ЕСЛИ НУЖНО)
#    Для активации установите LIVE_TRADING = True
LIVE_TRADING = False
TINKOFF_TOKEN = "your_tinkoff_invest_api_token_here" # ВАШ ТОКЕН

# 5. ПУТИ К ПАПКАМ
DATA_DIR = 'data-connector/Data/Tinkoff/'
REPORTS_DIR = 'reports'

# ======================================================================================
# --- КОНЕЦ ПАНЕЛИ УПРАВЛЕНИЯ ---
# ======================================================================================

if __name__ == '__main__':
    # --- 1. Проверка и подготовка окружения ---
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    if STRATEGY_TO_RUN not in strategies.available_strategies:
        raise ValueError(f"Стратегия '{STRATEGY_TO_RUN}' не найдена. "
                         f"Доступные стратегии: {list(strategies.available_strategies.keys())}")
    
    StrategyClass = strategies.available_strategies[STRATEGY_TO_RUN]

    # --- 2. Инициализация Cerebro для асинхронного режима ---
    cerebro = bt.Cerebro(
        stdstats=False, 
        optreturn=False if MODE == 'OPTIMIZATION' else True,
        runonce=False,  # КЛЮЧЕВОЙ ПАРАМЕТР: отключаем синхронизацию данных
        preload=False,  # НЕ предзагружаем все данные в память
        oldsync=False,   # НЕ используем старый механизм синхронизации
        exactbars=-1    # ДОБАВИТЬ: позволяет разную длину данных
    )

    # --- Наблюдатели ---
    # Включаем стандартные наблюдатели (при желании можно оставить stdstats=False и добавить только нужные)
    # Показываем Buy/Sell как маркеры над/под свечой (barplot=True) и дистанцию от свечи (bardist)
    # cerebro.addobserver(bt.observers.BuySell, barplot=True, bardist=0.015)

    # Показываем значение портфеля / кэша — удобный верхний график
    cerebro.addobserver(bt.observers.Value, plotname='Стоимость портфеля')    # портфель value (включая cash)
    cerebro.addobserver(bt.observers.Cash, plotname='Свободные средства')     # cash отдельно
    cerebro.addobserver(bt.observers.DrawDown, plotname='Просадка (%)')       # просадка
    
    # Показываем полную информацию по сделкам (PnL на закрытие и т.д.)
    cerebro.addobserver(bt.observers.Trades, pnlcomm=True, plotname='P&L по сделкам')

    # --- 3. Конфигурация в зависимости от режима (Live vs Backtest) ---
    if LIVE_TRADING:
        print("РЕЖИM: РЕАЛЬНАЯ ТОРГОВЛЯ (TINKOFF)")
        # Здесь логика для подключения к Tinkoff, взятая из примера Игоря Чечета
        # store = TKStore(token=TINKOFF_TOKEN)
        # broker = store.getbroker()
        # cerebro.setbroker(broker)
        
        # for ticker in StrategyClass.tickers:
        #     # формат тикера для Tinkoff может отличаться от имени файла
        #     dataname = ticker.split('_')[0] 
        #     data = store.getdata(dataname=dataname, fromdate=FROM_DATE)
        #     cerebro.adddata(data)
        
        # cerebro.addsizer(bt.sizers.FixedSize, stake=10) # Пример сайзера
        print("ВНИМАНИЕ: Логика Live Trading закомментирована. "
              "Раскомментируйте и настройте ее при необходимости.")

    else: # Режим бэктеста или оптимизации
        print(f"РЕЖИМ: {MODE}")
        
        # --- 4. Загрузка данных ---

        # НАСТРОЙКИ МАРКЕТА И ФОРМАТА ФАЙЛОВ
        MARKET_PREFIX = "TQBR"
        TIMEFRAME_SUFFIX = "_D1.txt"

        for ticker in StrategyClass.tickers:
            filename = f"{MARKET_PREFIX}.{ticker}{TIMEFRAME_SUFFIX}"
            datapath = os.path.join(DATA_DIR, filename)
            if not os.path.exists(datapath):
                print(f"Внимание: Файл данных не найден: {datapath}")
                continue
            
            data_feed = CustomCSVData(
                dataname=datapath,
                fromdate=FROM_DATE,  
                todate=TO_DATE
            )
            cerebro.adddata(data_feed, name=ticker)

            # привязываем observer к этой конкретной серии, чтобы стрелки рисовались на её графике
            cerebro.addobserver(bt.observers.BuySell, barplot=True, bardist=0.015, plotmaster=data_feed)
        
        # --- 5. Настройка брокера ---
        cerebro.broker.setcash(StrategyClass.start_cash)
        cerebro.broker.setcommission(commission=StrategyClass.commission)
        
        # --- 6. Добавление размера позиции (можно вынести в стратегию) ---
        # cerebro.addsizer(bt.sizers.PercentSizer, percents=95)
        
        # --- 7. Добавление анализаторов ---
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        # Кастомный анализатор из файла
        cerebro.addanalyzer(SortinoRatio, _name='sortino', riskfreerate=0.0, periods_per_year=252, mar=0.0)


    # --- 8. Добавление стратегии в Cerebro ---
    if MODE == 'OPTIMIZATION':
        opt_params = StrategyClass.opt_params
        if not opt_params or len(opt_params) != 2:
             raise ValueError("Для оптимизации с построением тепловой карты "
                              "в стратегии должно быть определено ровно 2 параметра в 'opt_params'")
        
        opt_param_names = list(opt_params.keys())
        cerebro.optstrategy(StrategyClass, **opt_params)
        print(f"Запуск оптимизации для {STRATEGY_TO_RUN} по параметрам: {opt_param_names}")

    else: # 'BACKTEST'
        cerebro.addstrategy(StrategyClass)
        print(f"Запуск бэктеста для {STRATEGY_TO_RUN}")


    # --- 9. Запуск процесса ---
    results = cerebro.run() 

    # --- 10. Генерация отчетов ---
    if not LIVE_TRADING:
        if MODE == 'OPTIMIZATION':
            print("--- Генерация отчета по оптимизации ---")
            generate_optimization_report(
                results,
                strategy_name=STRATEGY_TO_RUN,
                opt_param_names=opt_param_names,
                from_date=FROM_DATE,
                to_date=TO_DATE,
                reports_dir=REPORTS_DIR
            )
        else: # 'BACKTEST'
            print("\n--- Генерация отчета по бэктесту ---")
            generate_backtest_report(
                results[0],
                strategy_name=STRATEGY_TO_RUN,
                from_date=FROM_DATE,
                to_date=TO_DATE,
                reports_dir=REPORTS_DIR
            )
            
            # --- Сохранение графиков в файлы (индивидуально для каждого актива) ---
            try:
                # 1. Получаем список тикеров, которые были в бэктесте.
                #    Это нужно для осмысленных имен файлов.
                strategy_instance = results[0]
                tickers_in_test = [d._name for d in strategy_instance.datas]
                num_figs = max(1, len(tickers_in_test))

                # 2. Вызываем plot() с параметром plotind=True.
                #    Backtrader вернет список фигур, по одной на каждый актив.
                figures = cerebro.plot(
                    style='candlestick',
                    barup='green',
                    bardown='red',
                    vol=True,
                    plotind=True,
                    # Можно также задать размер для каждой индивидуальной фигуры
                    fig_w=16, # Ширина каждой фигуры в дюймах
                    fig_h=9,   # Высота каждой фигуры в дюймах
                    # numfigs=num_figs  # <- добавлено: по одной фигуре на тикер
                )

                # 3. Проходим по списку фигур и сохраняем каждую в свой файл.
                timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
                period_str = f"{FROM_DATE.strftime('%Y%m%d')}-{TO_DATE.strftime('%Y%m%d')}"

                # figures - это список списков, [[fig1], [fig2], ...]. Проходим по нему.
                for i, fig_group in enumerate(figures):
                    if i >= len(tickers_in_test):
                        # На случай, если фигур больше, чем тикеров (маловероятно)
                        ticker_name = f"data_{i}"
                    else:
                        ticker_name = tickers_in_test[i]
                    
                    # Имя файла теперь включает тикер
                    plot_filename = f"{STRATEGY_TO_RUN}_{ticker_name}_plot_{timestamp}_{period_str}.png"
                    plot_filepath = os.path.join(REPORTS_DIR, plot_filename)
                    
                    # Сохраняем фигуру (первый и единственный элемент в fig_group)
                    fig_group[0].savefig(plot_filepath, dpi=200) # dpi=200-300 для хорошего качества
                    
                    print(f"График для '{ticker_name}' сохранен в: {plot_filepath}")

            except Exception as e:
                print(f"Не удалось сохранить графики: {e}")