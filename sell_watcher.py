from app import fetch_unfilled_ids, fill_buy, update_sell_id, fill_sell, update_stop_id, fill_stop, check_filled_order, create_limit_sell_order, create_stop_order, cancel_pending_order
import time


while True:
    print('watching api ...')
    buy_orders = fetch_unfilled_ids('buy')
    if len(buy_orders)>0:
        print('found buy order ids: ...',buy_orders)
        for buy_order in buy_orders:
            print('checking: ..', buy_order)
            if check_filled_order(id=buy_order[1], symbol=buy_order[0]):
                trade = fill_buy(buy_id=buy_order[1])
                print(f"buy order {trade['id']} filled" )
                
                sell_order = create_limit_sell_order(base_amount= trade['base_amount'], sell_price= trade['sell_price'], base= trade['base'], quote= trade['quote'])
                stop_order = create_stop_order(base_amount= trade['base_amount'], stop_loss= trade['stop_loss'], base= trade['base'], quote= trade['quote'])
                if sell_order :
                    sell_order_id = sell_order['id']
                    update_sell_id(trade['id'], sell_order_id)
                if stop_order:
                    stop_order_id = stop_order['id']
                    update_stop_id(trade['id'], stop_order_id)
            else:
                print('not filled')

    sell_orders = fetch_unfilled_ids('sell')
    if len(sell_orders)>0:
        print('found sell order ids: ...',sell_orders)

        for sell_order in sell_orders:
            if check_filled_order(id=sell_order[1], symbol=sell_order[0]):
                canceled=cancel_pending_order(id=sell_order[2], symbol=sell_order[0])
                if canceled:
                    print('stoploss is canceled')
                trade = fill_sell(sell_order[1])
            elif check_filled_order(id=sell_order[2], symbol=sell_order[0]):
                canceled=cancel_pending_order(id=sell_order[1], symbol=sell_order[0])
                if canceled:
                    print('limit sell is canceled')
                trade = fill_stop(sell_order[2])
            else:
                print('not filled')
    time.sleep(10)