from flask import Flask, request, jsonify, render_template, abort, url_for, g
from flask_cors import CORS,cross_origin
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_httpauth import HTTPBasicAuth
import os
import time
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate


import config
# exchange = config.
from config import exchange
# exchange.set_sandbox_mode(True)
## Init app

app = Flask(__name__)
app.config['SECRET_KEY'] = config.PASSPHRASE


##################################################### DB CONFIG #####################################################


basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = config.DatabaseURL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True

db = SQLAlchemy(app)
auth = HTTPBasicAuth()
ma = Marshmallow(app)
migrate = Migrate(app,db)

CORS(app,resources={r"/api": {"origins": "*"}})
app.config['CORS_HEADERS'] = 'Content-Type'


#######################
#       SCHEMA        #
#######################

########### USER CLASS and Auth ##############

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), index=True)
    password_hash = db.Column(db.String(128))

    def hash_password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_auth_token(self, expires_in=600):
        return jwt.encode(
            {'id': self.id, 'exp': time.time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_auth_token(token):
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'],
                              algorithms=['HS256'])
        except:
            return
        return User.query.get(data['id'])



@auth.verify_password
def verify_password(username_or_token, password):
    # first try to authenticate by token
    user = User.verify_auth_token(username_or_token)
    if not user:
        # try to authenticate with username/password
        user = User.query.filter_by(username=username_or_token).first()
        if not user or not user.verify_password(password):
            return False
    g.user = user
    return True

# @app.route('/api/users', methods=['GET'])
# def register_user():
#     return render_template('register.html')


# @app.route('/api/users', methods=['POST'])
# def new_user():
#     username = request.json.get('username')
#     password = request.json.get('password')
#     if username is None or password is None:
#         abort(400)    # missing arguments
#     if User.query.filter_by(username=username).first() is not None:
#         abort(400)    # existing user
#     user = User(username=username)
#     user.hash_password(password)
#     db.session.add(user)
#     db.session.commit()
#     return (jsonify({'username': user.username}), 201,
#             {'Location': url_for('get_user', id=user.id, _external=True)})


# @app.route('/api/users/<int:id>')
# def get_user(id):
#     user = User.query.get(id)
#     if not user:
#         abort(400)
#     return jsonify({'username': user.username})


# @app.route('/api/token')
# @auth.login_required
# def get_auth_token():
#     token = g.user.generate_auth_token(600)
#     return jsonify({'token': token.decode('ascii'), 'duration': 600})


@app.route('/api/resource')
@auth.login_required
def get_resource():
    return jsonify({'data': 'Hello, %s!' % g.user.username})



################################## APP ######################################



class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    buy_order_id = db.Column(db.String, default="0", nullable=False)
    sell_order_id = db.Column(db.String, default="0", nullable=False)
    stop_order_id = db.Column(db.String, default="0", nullable=False)
    base = db.Column(db.String(50), nullable=False)
    quote = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float(), nullable=False)
    buy_price = db.Column(db.Float(), nullable=False)
    sell_price = db.Column(db.Float(), nullable=False)
    stop_loss = db.Column(db.Float(), nullable=False)
    buy_filled = db.Column(db.Boolean, default=False, nullable=False)
    sell_filled = db.Column(db.Boolean, default=False, nullable=False)
    stop_filled = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(self,base,quote,amount,buy_price,sell_price,stop_loss,buy_order_id,):
        # Add the data to the instance
        self.base = base
        self.quote = quote
        self.buy_order_id = buy_order_id
        self.amount = amount
        self.buy_price= buy_price
        self.sell_price = sell_price
        self.stop_loss = stop_loss

class TradeSchema(ma.Schema):
    class Meta:
        fields = ('id','base','quote', 'amount', 'buy_price', 'sell_price', 'stop_loss', 'buy_filled', 'sell_filled', 'stop_filled','buy_order_id','sell_order_id','stop_order_id')

trade_schema = TradeSchema()
trades_schema = TradeSchema(many=True)

##################################################### pause module #################################################


class Pause(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(50), nullable=False)
    side = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float(), nullable=False)
    price = db.Column(db.Float(), nullable=False)
    stopPrice = db.Column(db.Float(), default=0, nullable=False)
    old_id = db.Column(db.String, default="0", nullable=False)

    def __init__(self,symbol,side,type,amount,price,stopPrice,old_id):
        # Add the data to the instance
        self.symbol = symbol
        self.side = side
        self.type= type
        self.amount = amount
        self.price = price
        self.stopPrice =stopPrice
        self.old_id = old_id

class PauseSchema(ma.Schema):
    class Meta:
        fields = ('id','symbol', 'side','type','amount','price','stopPrice','old_id')

pause_schema = PauseSchema()
pauses_schema = PauseSchema(many=True)


##################################################### DB Calls #####################################################

#################
# new buy trade #
#################


def add_buy_trade_to_db(base,quote,amount,buy_price,sell_price,stop_loss,buy_order_id):  
    # Create an instance
    new_trade = Trade(base,quote,amount,buy_price,sell_price,stop_loss,buy_order_id)
    # Save the trade in the db
    db.session.add(new_trade)
    db.session.commit()


#################
# Get all trades#
#################

def fetch_trades_from_db():
    # get the trade from db
    all_trades = Trade.query.all()
    # get the trade as per the schema
    result = trades_schema.dump(all_trades)
    # return the trade
    return result

#################
# Get all pauses#
#################

def fetch_pauses_from_db():
    # get the trade from db
    all_pauses = Pause.query.all()
    # get the trade as per the schema
    result = pauses_schema.dump(all_pauses)
    # return the trade
    return result


#################
# new buy Pause #
#################

def add_pause_to_db(symbol, side, type, amount, price, stopPrice, old_id):  
    # Create an instance
    new_pause = Pause(symbol=symbol, side=side, type=type, amount=amount, price=price, stopPrice=stopPrice, old_id=old_id)
    # Save the pause in the db
    db.session.add(new_pause)
    db.session.commit()


########################
# getting unfilled ids #
########################

def fetch_unfilled_ids(side):
    all_trades = fetch_trades_from_db()
    if side == 'buy':
        unfilled_orders_ids = [((order['base']+"/"+order['quote']),order['buy_order_id']) for order in all_trades if order['buy_filled'] == False]
    elif side == 'sell':
        unfilled_orders_ids = list(filter(lambda prices: prices[-2:] != ('0','0'),[((order['base']+"/"+order['quote']),order['sell_order_id'],order['stop_order_id']) for order in all_trades if order['sell_filled'] == False and order['stop_filled'] == False]))

    return unfilled_orders_ids


#########################
# update after ids pause#
#########################

def update_buy_id_after_pause(old_id, new_id):
    trade = Trade.query.filter(Trade.buy_order_id == old_id).first()
    trade.buy_order_id = new_id
    # commit to the database
    db.session.commit()

    # return the new trade as per the schema
    return trade

def update_sell_id_after_pause(old_id, new_id):
    trade = Trade.query.filter(Trade.sell_order_id == old_id).first()
    trade.sell_order_id = new_id
    # commit to the database
    db.session.commit()

    # return the new trade as per the schema
    return trade

def update_stop_id_after_pause(old_id, new_id):
    trade = Trade.query.filter(Trade.stop_order_id == old_id).first()
    trade.stop_order_id = new_id
    # commit to the database
    db.session.commit()

    # return the new trade as per the schema
    return trade


########################
# update limit-sell id #
########################

def update_sell_id(trade_id, new_id):
    trade = Trade.query.get(trade_id)
    trade.sell_order_id = new_id
    # commit to the database
    db.session.commit()

    # return the new trade as per the schema
    return trade

######################
# update stoploss id #
######################


def update_stop_id(trade_id, new_id):
    trade = Trade.query.get(trade_id)
    trade.stop_order_id = new_id
    # commit to the database
    db.session.commit()

    # return the new trade as per the schema
    return trade


############
# fill buy #
############

def fill_buy(buy_id):
    # get the trade first
    trade = Trade.query.filter(Trade.buy_order_id == buy_id).first()

    # set filled True
    trade.buy_filled = True
    next_trade={}
    next_trade['id'] = trade.id
    next_trade['base_amount'] = trade.amount/trade.buy_price
    next_trade['sell_price'] = trade.sell_price
    next_trade['stop_loss'] = trade.stop_loss
    next_trade['base'] = trade.base
    next_trade['quote'] = trade.quote
    # commit to the database
    db.session.commit()

    # return the new trade as per the schema
    return next_trade


#############
# fill sell #
#############

def fill_sell(sell_id):
    # get the trade first
    trade = Trade.query.filter(Trade.sell_order_id==sell_id).first()

    # set filled True
    trade.sell_filled = True

    # commit to the database
    db.session.commit()

    # return the new trade as per the schema
    return trade


##################
# fill stop lose #
##################

def fill_stop(stop_id):
    # get the trade first
    trade = Trade.query.filter(Trade.stop_order_id==stop_id).first()

    # set filled True
    trade.stop_filled = True

    # commit to the database
    db.session.commit()

    # return the new trade as per the schema
    return trade




##################################################### API CALLS #####################################################


def create_limit_buy_order(quote_amount, buy_price, base, quote, sell_price,stop_loss):
    base_amount = quote_amount / buy_price
    symbol = base + "/" + quote
    print('creating limit buy order')
    try:
        order = exchange.create_limit_buy_order(symbol=symbol, amount= base_amount, price=buy_price)
        if order :
            buy_order_id = order['id']
            print(buy_order_id)
            add_buy_trade_to_db(base=base, quote=quote, amount=quote_amount, buy_price=buy_price, sell_price=sell_price, stop_loss=stop_loss, buy_order_id=buy_order_id)

    except Exception as e:
        print(f"an exception occured - {e}")
        order = None

    return order

def check_filled_order(id,symbol):
    if id != "0":
        try:
            order = exchange.fetch_order(id,symbol)
            if order['status'] == 'closed' :
                print('status is closed')
                return True
        except Exception as e:
            print("request failed, retrying",e)
            return False
    return False

def cancel_pending_order(id,symbol):
    if id != "0":
        try:
            order = exchange.cancel_order(id=id, symbol=symbol)
            return True
        except Exception as e:
            print("request failed, retrying",e)
            pass
    return False

def cancel_pending_order_and_sell_market(id, symbol):
    if id !="0":
        try:
            order = exchange.fetch_order(id, symbol)
            amount = order['amount']
            canceled = cancel_pending_order(id=id,symbol=symbol)
            if canceled:
                neworder = exchange.create_market_sell_order(symbol=symbol, amount=amount)
            return neworder
        except Exception as e:
            print("request failed, retrying",e)
            pass
    return False


def create_limit_sell_order(base_amount, sell_price, base, quote):
    symbol = base + "/" + quote
    try:
        order = exchange.create_limit_sell_order(symbol=symbol, amount= base_amount, price=sell_price)
        print("sell order created")
    except Exception as e:
        print(f"an exception occured - {e}")
        order = None

    return order

def create_stop_order(base_amount, stop_loss, base, quote):
    symbol = base + "/" + quote
    price = stop_loss * 0.995
    try:
        order = exchange.create_stop_limit_order(symbol=symbol, amount= base_amount, price=price, stopPrice=stop_loss, side= 'sell')
        print("stoploss order created")
    except Exception as e:
        print(f"an exception occured - {e}")
        order = None

    return order

def filter_trades():
        results = fetch_trades_from_db()
        data=[]
        for result in results:
            buy ={}
            sell ={}
            stop={}
            symbol = result['base'] + result['quote']
            if result['buy_filled'] :
                if result['sell_filled'] or result['stop_filled']:
                    continue
                else:
                    if result['sell_order_id'] != '0':
                        recored = exchange.fetch_order(id=result['sell_order_id'],symbol=symbol)
                        if recored['status'] == 'open':
                            sell['id']= result['sell_order_id']
                            sell['symbol']= symbol
                            sell['type']='limit sell'
                            sell['price']= result['sell_price']
                            sell['status']= f"{result['sell_filled']}"
                            data.append(sell)
                    
                    if result['stop_order_id'] != '0':
                        recored = exchange.fetch_order(id=result['stop_order_id'],symbol=symbol)
                        if recored['status'] == 'open':
                            stop['id']= result['stop_order_id']
                            stop['symbol']= symbol
                            stop['type']='stop loss'
                            stop['price']= result['stop_loss']
                            stop['status']= f"{result['stop_filled']}" 
                            data.append(stop)
            else:
                recored = exchange.fetch_order(id=result['buy_order_id'],symbol=symbol)
                if recored['status'] == 'open':                   
                    buy['id']= result['buy_order_id']
                    buy['symbol']= symbol
                    buy['type']='limit buy'
                    buy['price']= result['buy_price']
                    buy['status'] = f"{result['buy_filled']}"
                    data.append(buy)
                
        return {'orders':data}

def pause(orders):
    for order in orders:
        order_data = exchange.fetch_order(order['id'],order['symbol'])
        if order_data['status'] != 'closed':
            id = order_data['id']
            type = order_data['type']
            side = order_data['side']
            symbol = order_data['symbol']
            price = order_data['price']
            amount = order_data['amount']
            stopPrice = order_data['stopPrice']
            if id !=0:
                exchange.cancel_order(id=id,symbol =symbol)
            if stopPrice == None:
                stopPrice = 0
            add_pause_to_db(symbol=symbol, side=side, type=type, amount=amount, price=price, stopPrice=stopPrice, old_id = id)
    return 'done'

def resume():
    orders = fetch_pauses_from_db()
    for order in orders:
        old_id = order['old_id']
        try:
            if order['type'] == 'stop_loss_limit':
                order= exchange.create_stop_limit_order(symbol=order['symbol'],side=order['side'],amount=order['amount'], price=order['price'], stopPrice=order['stopPrice'])
                new_id = order['id']
                update_stop_id_after_pause(old_id=old_id, new_id=new_id)
            elif order['type'] == 'limit' and order['side'] == 'buy' :
                order = exchange.create_limit_order(symbol=order['symbol'], side=order['side'], amount=order['amount'], price=order['price'])
                new_id = order['id']
                update_buy_id_after_pause(old_id=old_id, new_id=new_id)
            elif order['type'] == 'limit' and order['side'] == 'sell':
                order = exchange.create_limit_order(symbol=order['symbol'], side=order['side'], amount=order['amount'], price=order['price'])
                new_id = order['id']
                update_sell_id_after_pause(old_id=old_id, new_id=new_id)
        except Exception as e:
            print(e)
            
    return 'done'





##################################################### ROUTER #####################################################

####################
# render home page #
####################


@app.route('/', methods=['GET'])
@auth.login_required
@cross_origin(origin='*',headers=['content-type'])
def render_home_page():
    return render_template("index.html")


#################
# create trades #
#################


@app.route('/', methods=['POST'])
@auth.login_required
@cross_origin(origin='*',headers=['content-type'])
def send_buy_orders():
    requested_orders =request.get_json(silent=True)
    for order in requested_orders['orders']:
        quote = requested_orders['quote']
        base = order['base']
        amount = float(order['amount'])
        buy_price= float(order['buy_price'])
        sell_price = float(order['sell_price'])
        stop_loss = float(order['stop_loss'])

        create_limit_buy_order(quote_amount=amount, buy_price=buy_price, base=base, quote=quote, sell_price=sell_price,stop_loss=stop_loss)
    return jsonify(requested_orders)


#################
# Get all trades#
#################
@app.route('/trades', methods=['GET'])
@auth.login_required
@cross_origin(origin='*',headers=['Content-Type'])
def get_all_trades():
    return render_template("dashboard.html")


@app.route('/trades/data/vue', methods=['GET'])
@auth.login_required
@cross_origin(origin='*',headers=['Content-Type'])
def vue_all_trades():
    return filter_trades()


###################
# cancel an order #
###################

@app.route('/trades/cancel', methods=['POST'])
@auth.login_required
@cross_origin(origin='*',headers=['Content-Type'])
def cancel_order_request():
    order_to_cancel =request.get_json(silent=True)
    print(order_to_cancel)
    cancel_pending_order(id=order_to_cancel['id'], symbol=order_to_cancel['symbol'])
    return order_to_cancel



##########################
# cancel and sell market #
##########################

@app.route('/trades/cancelandsellmarket', methods=['POST'])
@auth.login_required
@cross_origin(origin='*',headers=['Content-Type'])
def cancel_order_request_and_sell_market():
    order_to_cancel =request.get_json(silent=True)
    print(order_to_cancel)
    neworder =cancel_pending_order_and_sell_market(id=order_to_cancel['id'], symbol=order_to_cancel['symbol'])
    return neworder

##########################
# Pause all trades       #
##########################

@app.route('/trades/pause', methods=['POST'])
@auth.login_required
@cross_origin(origin='*',headers=['Content-Type'])
def pause_all_trades():
    orders_to_pause =request.get_json(silent=True)
    print(orders_to_pause)
    neworder =pause(orders=orders_to_pause)
    return neworder

##################
# Get all paused #
##################

@app.route('/paused', methods=['GET'])
@auth.login_required
@cross_origin(origin='*',headers=['Content-Type'])
def get_paused_trades():
    return render_template("paused.html")

@app.route('/paused/data/vue', methods=['GET'])
@auth.login_required
@cross_origin(origin='*',headers=['Content-Type'])
def vue_all_paused():
    orders = fetch_pauses_from_db()
    data = []
    for order in orders:
        neworder={}
        if order['type'] == 'stop_loss_limit':
            neworder['type']= 'stop loss'
            neworder['id'] = order['old_id']
            neworder['symbol']=order['symbol']
            neworder['price']=order['stopPrice']
        elif order['type'] == 'limit' and order['side'] == 'buy' :
            neworder['type'] = 'limit buy'
            neworder['id'] = order['old_id']
            neworder['symbol']=order['symbol']
            neworder['price']=order['price']
        elif order['type'] == 'limit' and order['side'] == 'sell':
            neworder['type'] = 'limit sell'
            neworder['id'] = order['old_id']
            neworder['symbol']=order['symbol']
            neworder['price']=order['price']
        data.append(neworder)

    return {'orders':data}

@app.route('/paused/activate', methods=['POST'])
@auth.login_required
@cross_origin(origin='*',headers=['Content-Type'])
def activate_paused_orders():
    status = resume()
    if status:
        db.session.query(Pause).delete()
        db.session.commit()
    return 'status' 


# Start the app
if __name__ == '__main__':
    db.create_all()
    app.run(threaded=True, port=5000)