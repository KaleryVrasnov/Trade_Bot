import uuid
from tinkoff.invest import CandleInterval, MoneyValue, Client, OrderType, PostOrderResponse, OperationType
from tinkoff.invest.sandbox.client import SandboxClient
from tinkoff.invest.services import OrderDirection
from tinkoff.invest.utils import now
from tinkoff.invest.constants import INVEST_GRPC_API_SANDBOX
from datetime import date, datetime, timedelta
import time
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import ta.trend
import plotly.graph_objects as go
import schedule


def get_candles_as_dataframe(token, figi):
    with SandboxClient(token, target=INVEST_GRPC_API_SANDBOX) as client:
        class_candle = client.get_all_candles(  # получение свечей за период времени
            figi=figi,
            from_=now() - timedelta(7),
            to=now(),
            interval=CandleInterval.CANDLE_INTERVAL_5_MIN,
        )
        df = create_dataframe(class_candle)
    return df


def create_dataframe(class_candle):
    df = pd.DataFrame([{
        'time': candle.time,
        'volume': candle.volume,
        'open': money_to_float(candle.open),
        'close': money_to_float(candle.close),
        'high': money_to_float(candle.high),
        'low': money_to_float(candle.low)
    } for candle in class_candle])
    return df


def add_two_moving_averages(df, small_window, big_window):
    df['SMA' + str(big_window)] = ta.trend.ema_indicator(close=df['close'], window=big_window, fillna=True)
    df['SMA' + str(small_window)] = ta.trend.ema_indicator(close=df['close'], window=small_window, fillna=True)
    return df


def money_to_float(Money):
    return Money.units + Money.nano / 1e9


def print_accounts(token):
    print("Список счетов:")
    with SandboxClient(token, target=INVEST_GRPC_API_SANDBOX) as client:
        accounts = client.users.get_accounts().accounts  # список песочных счетов
        for i in range(len(accounts)):
            print("[Счёт " + str(i) + "]", accounts[i].id)
    print("\n")


def get_token(file_txt):
    file = open(file_txt)
    token = file.readline()
    file.close()
    return token


def show_candles(df):
    fig = go.Figure(
        data=[go.Candlestick(x=df['time'],
                             open=df['open'],
                             high=df['high'],
                             low=df['low'],
                             close=df['close'],
                             )])
    fig.show()


def show_plot(df, small_window, big_window):
    y1 = df.plot(x='time', y='close')
    y2 = df.plot(ax=y1, x='time', y='SMA' + str(small_window))
    df.plot(ax=y2, x='time', y='SMA' + str(big_window))
    plt.show()


def buy_order(token, quantity, figi, account_id):
    with SandboxClient(token, target=INVEST_GRPC_API_SANDBOX) as client:
        order_id = str(uuid.uuid4())
        client.orders.post_order(
            quantity=quantity,  # Количество лотов для покупки
            direction=OrderDirection.ORDER_DIRECTION_BUY,  # Направление операции (покупка или продажа)
            figi=figi,  # FIGI акции
            order_type=OrderType.ORDER_TYPE_MARKET,  # Тип ордера (рыночный или лимитный)
            account_id=account_id,  # Идентификатор брокерского счета
            order_id=order_id,  # Идентификатор брокерского счета
        )


def sell_order(token, quantity, figi, account_id):
    with SandboxClient(token, target=INVEST_GRPC_API_SANDBOX) as client:
        order_id = str(uuid.uuid4())
        client.orders.post_order(
            quantity=quantity,  # Количество лотов для покупки
            direction=OrderDirection.ORDER_DIRECTION_SELL,  # Направление операции (покупка или продажа)
            figi=figi,  # FIGI акции
            order_type=OrderType.ORDER_TYPE_MARKET,  # Тип ордера (рыночный или лимитный)
            account_id=account_id,  # Идентификатор брокерского счета
            order_id=order_id,  # Идентификатор брокерского счета
        )


flag = bool
last_buy_price = float
commission = 0.004
profit = float


def my_strategy(df, token, quantity, figi, account_id, small_window, big_window):
    current_row = df.iloc[-1]
    previous_row = df.iloc[-2]
    global flag
    global last_buy_price
    global profit
    if flag:
        if current_row['SMA' + str(small_window)] < previous_row['SMA' + str(big_window)]:
            sell_order(token=token, quantity=quantity, figi=figi, account_id=account_id)
            print('Тенденция на уменьшение цены. Акции проданы!')
            profit = current_row['close'] * (1 - commission) - last_buy_price
            flag = False

        else:
            print('Тенденции на уменьшение цены нет. Акции сохранены')
            pass
    else:
        if current_row['SMA' + str(small_window)] > previous_row['SMA' + str(big_window)]:
            buy_order(token=token, quantity=quantity, figi=figi, account_id=account_id)
            print('Тенденция на увелечение цены. Акции куплены!')
            last_buy_price = current_row['close']
            flag = True
        else:
            print('Тенденции на повышение цены нет. Акции не куплены')
            pass


# print(client.operations.get_portfolio(account_id=account_id))
# print(client.users.get_info())


def main():
    token = get_token("secret.txt")
    # открытие песочного счёта
    # client.sandbox.open_sandbox_account()

    # print_accounts(token)
    account_id = "385597e1-52e1-4a5a-91db-69c15208b9c3"

    # пополнение счёта
    # client.sandbox.sandbox_pay_in(account_id=account_id, amount=MoneyValue(units=100000, nano=0, currency='rub'))

    figi = 'BBG004S682Z6'  # Ростелеком

    df = get_candles_as_dataframe(token=token, figi=figi)

    small_window = 10
    big_window = 200
    add_two_moving_averages(df, small_window=small_window, big_window=big_window)

    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    print(df)

    show_candles(df)
    show_plot(df, small_window=small_window, big_window=big_window)

    my_strategy(df=df,
                token=token,
                quantity=1,
                figi=figi,
                account_id=account_id,
                small_window=small_window,
                big_window=big_window
                )
    print(flag)

if __name__ == "__main__":
    main()

schedule.every(5).seconds.do(main)

while True:
    schedule.run_pending()
    time.sleep(1)


