from flask import Flask, request, abort, render_template
import json
from flask.json import jsonify
import ZHA_stock_exchange as zse
import threading
import rw
import sudo

app = Flask(__name__)

@app.route('/')
def hellowWorld():
    return "Hello World"


@app.route('/zha')
def username():
    open_stock_exchange()
    return zse.user_login("zha", "zha")

# 登入帳號
@app.route('/login', methods=['post','get'])
def login():
    open_stock_exchange()
    user = request.args.get('user')
    password = request.args.get('password')

    return zse.user_login(user, password)

# 註冊帳號
@app.route('/signup', methods=['post','get'])
def signup():
    user = request.args.get('user')
    password = request.args.get('password')
    print ("signup", user, password)

    jdata = rw.r_gamer()
    if user in jdata:
        return "帳號已存在!"
    else:
        jdata[user] = jdata["Gamer"]
        jdata[user]["Password"]=password
        rw.w_gamer(jdata)

        print("Create Finish", user, password)
        return "Create Finish"


# 取得 HomePage 資料
@app.route('/get_HomePage_Data', methods=['post','get'])
def get_HomePage_Data():
    user = request.args.get('user')
    password = request.args.get('password')
    if zse.user_login(user, password) == "Ok!":
        return zse.get_HomePage_Data(user, password)
    return {"state":"false"}

# 受使用者委託交易 建立委託單
@app.route('/entrust', methods=['post','get'])
def entrusted():
    open_stock_exchange()
    user = request.args.get('user')
    type = request.args.get('type')
    ticker = request.args.get('ticker')
    price = request.args.get('price')
    lot = request.args.get('lot')
    reqtime = request.args.get('time')
    extra = request.args.get('extra')
    name = request.args.get('name')
    market = request.args.get('market')

    return zse.user_entrust_order(user, market, type, ticker, name, price, lot, reqtime, extra )

# 查詢委託單
@app.route('/getOrder', methods=['post','get'])
def getOrder():
    open_stock_exchange()
    user = request.args.get('user')
    return zse.get_user_order(user)

# 刪除委託單
@app.route('/delOrder', methods=['post','get'])
def delOrder():
    open_stock_exchange()
    user = request.args.get('user')
    orderId = request.args.get('orderId')
    return zse.del_user_order(user, orderId)


# 取得使用者證卷帳戶
@app.route('/get_securityAccount', methods=['post','get'])
def get_SA():
    user = request.args.get('user')
    password = request.args.get('password')
    return zse.get_user_securityAccount(user, password)

# 取的保證金
@app.route('/getMargin', methods=['post','get'])
def get_tw_margin():
    futures = request.args.get('futures')
    margin  = zse.get_twFutures_initial_margin(futures)
    print ("return:", margin)
    return str(margin)

# 運行
@app.route('/stock_exchange', methods=['post','get'])
def open_stock_exchange():
    open_stock_exchange_thread = threading.Thread(target = zse.stock_exchange)
    open_stock_exchange_thread.start()
    return "stock_exchange"

# 取得使用者明細
@app.route('/getDetails', methods=['post','get'])
def getDetails():
    user = request.args.get('user')
    password = request.args.get('password')
    return zse.get_user_details(user, password)

# 取得使用者庫存
@app.route('/getInStocks', methods=['post','get'])
def getInStocks():
    open_stock_exchange()
    user = request.args.get('user')
    password = request.args.get('password')
    return zse.get_user_instock(user, password)


@app.route('/get_account_detail', methods=['post','get'])
def get_account_detail():
    user = request.args.get('user')
    password = request.args.get('password')
    return zse.get_user_account_details(user, password)

# 更改使用者名稱
@app.route('/renameName', methods=['post','get'])
def rename_account_name():
    user = request.args.get('user')
    password = request.args.get('password')
    name = request.args.get('name')
    return zse.rename_user_name(user, password, name)

# 取得公告
@app.route('/announcement', methods=['post','get'])
def get_announcement():
    
    return rw.r_announcement()

# speak in talk
@app.route('/spead_in_talk', methods=['post','get'])
def speak_in_talk():
    user = request.args.get('user')
    msg = request.args.get('msg')
    rw.w_str_to_talk(user, msg)
    return "spead_in_talk"

# get talk
@app.route('/get_talk', methods=['post','get'])
def get_talk():
    return rw.r_talk()

# get twHotStocksList
@app.route('/get_twHotStocksList', methods=['post','get'])
def get_twHotStocksList():
    return zse.get_twHotStocksRank_list()

# ==== add something in json ====
@app.route('/sudo_add', methods=['post','get'])
def sudo_add_something_json():
    gjson = rw.r_gamer()
    for g in gjson:
        if "Name" in gjson[g]:
            gjson[g]["Title"].append("s封a弊o者s")
    rw.w_gamer(gjson)
    return "ok!"

# ==== backup json ====
@app.route('/sudo_backup_json', methods=['post','get'])
def sudo_backup_json():
    rw.backup_jsonData()
    
    return "finish!"

# ==== sudo_zeroing_all_accounts , https://tradingAppServer.masterrongwu.repl.co/sudo_zeroing_all_accounts ====
@app.route('/sudo_zeroing_all_accounts', methods=['post','get'])
def sudo_zeroing_all_accounts():
    sudo.zeroing_all_accounts()
    return "finish!"

# ==== sudo_zeroing_accounts , https://tradingAppServer.masterrongwu.repl.co/sudo_zeroing_accounts?user= ====
@app.route('/sudo_zeroing_accounts', methods=['post','get'])
def sudo_zeroing_accounts():
    user = request.args.get('user')
    sudo.zeroing_account(user)
    return "finish!"

# ==== test , https://tradingAppServer.masterrongwu.repl.co/test ====
@app.route('/test', methods=['post','get'])
def test():
    data = {
        "msgArray":
        [
            {
                "tv":"-",
                "z":"-",
                "ps":"9406",
                "pz":"128.5000",
                "bp":"0",
                "fv":"1909",
                "oa":"129.0000",
                "ob":"128.5000",
                "a":"129.0000_",
                "f":"570_",
                "b":"128.5000_128.0000_127.5000_127.0000_126.5000_",
                "g":"2698_7660_4287_5705_3973_",
                "c":"2603",
                "ip":"0",
                "d":"20210901",
                "ch":"2603.tw",
                "ot":"14:30:00",
                "tlong":"1630477800000",
                "mt":"000000",
                "ov":"76946",
                "h":"137.5000",
                "i":"15",
                "it":"12",
                "oz":"129.0000",
                "l":"126.5000",
                "n":"長榮",
                "o":"136.5000",
                "p":"0",
                "ex":"tse",
                "s":"9505",
                "t":"13:30:00",
                "u":"149.5000",
                "v":"277363",
                "w":"122.5000",
                "nf":"長榮海運股份有限公司",
                "y":"136.0000",
                "ts":"0"
            }
        ]
    }
    
    return data


if __name__ == "__main__":
    zse.initial_stock_exchange()
    open_stock_exchange()
    app.run(host="0.0.0.0", port=8080)
    