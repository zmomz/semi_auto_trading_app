from flask import Flask, request, jsonify, render_template, abort, url_for, g
from flask_cors import CORS,cross_origin
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_httpauth import HTTPBasicAuth
import os
import time
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
import config

## Init app

app = Flask(__name__)
app.config['SECRET_KEY'] = config.PASSPHRASE


##################################################### DB CONFIG #####################################################


basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = config.DatabaseURL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True

db = SQLAlchemy(app)
# engine = db.create_engine('postgresql://me@localhost/mydb',pool_size=20, max_overflow=0)
auth = HTTPBasicAuth()
ma = Marshmallow(app)

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

@app.route('/api/users', methods=['GET'])
def register_user():
    return render_template('register.html')


@app.route('/api/users', methods=['POST'])
def new_user():
    username = request.json.get('username')
    password = request.json.get('password')
    if username is None or password is None:
        abort(400)    # missing arguments
    if User.query.filter_by(username=username).first() is not None:
        abort(400)    # existing user
    user = User(username=username)
    user.hash_password(password)
    db.session.add(user)
    db.session.commit()
    return (jsonify({'username': user.username}), 201,
            {'Location': url_for('get_user', id=user.id, _external=True)})


@app.route('/api/users/<int:id>')
def get_user(id):
    user = User.query.get(id)
    if not user:
        abort(400)
    return jsonify({'username': user.username})


@app.route('/api/token')
@auth.login_required
def get_auth_token():
    token = g.user.generate_auth_token(600)
    return jsonify({'token': token.decode('ascii'), 'duration': 600})


@app.route('/api/resource')
@auth.login_required
def get_resource():
    return jsonify({'data': 'Hello, %s!' % g.user.username})



################################## APP ######################################



class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    base = db.Column(db.String(50), nullable=False)
    quote = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float(), nullable=False)
    buy_price = db.Column(db.Float(), nullable=False)
    buy_order_id = db.Column(db.String, default="0", nullable=False)
    sell_price = db.Column(db.Float(), nullable=False)
    sell_order_id = db.Column(db.String, default="0", nullable=False)
    stop_loss = db.Column(db.Float(), nullable=False)
    stop_order_id = db.Column(db.String, default="0", nullable=False)
    buy_filled = db.Column(db.Boolean, default=False, nullable=False)
    sell_filled = db.Column(db.Boolean, default=False, nullable=False)
    stop_filled = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(self,base,quote,amount,buy_price,sell_price,stop_loss,buy_order_id,):
        # Add the data to the instance
        self.base = base
        self.quote = quote
        self.amount = amount
        self.buy_price= buy_price
        self.sell_price = sell_price
        self.stop_loss = stop_loss
        self.buy_order_id = buy_order_id

class TradeSchema(ma.Schema):
    class Meta:
        fields = ('id','base','quote', 'amount', 'buy_price', 'sell_price', 'stop_loss', 'buy_filled', 'sell_filled', 'stop_filled','buy_order_id','sell_order_id','stop_order_id')

trade_schema = TradeSchema()
trades_schema = TradeSchema(many=True)

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

########################
# update limit-sell id #
########################

def update_sell_id(trade_id, sell_id):
    trade = Trade.query.get(trade_id)
    trade.sell_order_id = sell_id
    # commit to the database
    db.session.commit()

    # return the new trade as per the schema
    return trade

######################
# update stoploss id #
######################


def update_stop_id(trade_id, stop_id):
    trade = Trade.query.get(trade_id)
    trade.stop_order_id = stop_id
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

from config import exchange

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
            if order['status'] == 'closed' or order['status'] == 'canceled':
                print('status is closed')
                return True
        except Exception as e:
            print("request failed, retrying",e)
            pass
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
        base = requested_orders['base']
        quote = requested_orders['quote']
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
    results = fetch_trades_from_db()
    data=[]
    for result in results:
        buy ={}
        sell ={}
        stop={}
        if result['buy_filled'] :
            if result['sell_filled'] or result['stop_filled']:
                continue
            else:
                sell['id']= result['sell_order_id']
                stop['id']= result['stop_order_id']

                sell['symbol']= result['base'] + result['quote']
                stop['symbol']= result['base'] + result['quote']

                sell['type']='limit sell'
                stop['type']='stop loss'

                sell['price']= result['sell_price']
                stop['price']= result['stop_loss']

                sell['status']= f"{result['sell_filled']}"
                stop['status']= f"{result['stop_filled']}" 
                data.append(sell)
                data.append(stop)
        else:                   
            buy['id']= result['buy_order_id']
            sell['id']= result['sell_order_id']
            stop['id']= result['stop_order_id']

            buy['symbol']= result['base'] + result['quote']
            sell['symbol']= result['base'] + result['quote']
            stop['symbol']= result['base'] + result['quote']

            buy['type']='limit buy'
            sell['type']='limit sell'
            stop['type']='stop loss'

            buy['price']= result['buy_price']
            sell['price']= result['sell_price']
            stop['price']= result['stop_loss']

            buy['status'] = f"{result['buy_filled']}"
            sell['status']= f"{result['sell_filled']}"
            stop['status']= f"{result['stop_filled']}"
            data.append(buy)
            data.append(sell)
            data.append(stop)
            
    return {'orders':data}


###################
# cancel an order #
###################

@app.route('/trades/cancel', methods=['POST'])
@auth.login_required
@cross_origin(origin='*',headers=['Content-Type'])
def cancel_order_request():
    order_to_cancel =request.get_json(silent=True)
    print(order_to_cancel)
    cancel_pending_order(id=order_to_cancel['id'], symbol=order_to_cancel['symbol'], type=order_to_cancel['type'])
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



# Start the app
if __name__ == '__main__':
    db.create_all()
    app.run(port=5000)