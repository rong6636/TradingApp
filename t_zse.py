import json
import os
import io
import random
import time
from datetime import date, datetime, timedelta, timezone
import threading
from flask.helpers import safe_join

import rw
import pandas as pd
import requests
from bs4 import BeautifulSoup
import math

# initialization
def initial_stock_exchange():
    signal=rw.r_signal()

    signal["stockExchangeOpen"] = 0
    signal["roundCD"] = 2

    rw.w_signal(signal)

# 運作交易所
def stock_exchange():
    signal = rw.r_signal()
    r_id = random.randint(100, 1000)
    trading_num = -1
    # 碰撞避免保護
    if signal["stockExchangeOpen"] != 0:
        print ("碰撞避免保護 1")
        return
    else:
        signal["stockExchangeOpen"] = r_id
        rw.w_signal(signal)
        time.sleep((r_id/1000)*5)
        signal = rw.r_signal()
        if signal["stockExchangeOpen"] != r_id:
            print ("碰撞避免保護 2")
            return
    rw.check_backup()

    while trading_num != 0 :
        signal=rw.r_signal()
        dayparts, sleepTime = get_currentTWSEDaysPart()
        sleepTime = max(3, sleepTime*pow(0.5, trading_num))
        if signal["roundCD"] > 0:
            print("=== CD ===", dayparts, sleepTime)
            # 冷卻
            time.sleep(sleepTime)
            signal["roundCD"] -= 1
            rw.w_signal(signal)
            rw.renew_Gs_Log()
        else:
            print("=== working ===", dayparts, sleepTime)
            debug_check()
            
            trading_num = twStockService(dayparts)
            trading_num += twFuturesService(dayparts)
        
            signal["roundCD"] += 1
            time.sleep(0.5)
            rw.w_signal(signal)

    signal["stockExchangeOpen"] = 0
    signal["roundCD"] = 2
    rw.w_signal(signal)
    rw.backup_jsonData()
    print ("====== 交易所暫無工作!! ======")

# 交易所 日程
def get_currentTWSEDaysPart():
    _str = ""
    sleepTime = 600

    tw = timezone(timedelta(hours=+8))
    twdt = datetime.now(tw)
    yd = twdt-timedelta(days=1)
    holiday = get_twseHoliday()

    # 不是例假日 不是六日 在9點到13點半之間
    if twdt.strftime("%Y/%m/%d") not in holiday["Holiday"]:
        if int(twdt.strftime("%w"))>=1 and int(twdt.strftime("%w"))<=5:
            if int(twdt.strftime("%H%M"))>=830 and int(twdt.strftime("%H%M"))<900:
                _str += "股票開盤時段"
            elif int(twdt.strftime("%H%M"))>=900 and int(twdt.strftime("%H%M"))<1330:
                _str += "股票交易時段"
            elif int(twdt.strftime("%H%M"))>=1330 and int(twdt.strftime("%H%M"))<1450:
                _str += "股票結束時段"
    else:
        _str += "股票休息時段"

    # 不是例假日 不是六日 在845-1345之間 1500-2359
    if twdt.strftime("%Y/%m/%d") not in holiday["Holiday"] and int(twdt.strftime("%w"))>=1 and int(twdt.strftime("%w"))<=5:
        if (int(twdt.strftime("%H%M"))>=845 and int(twdt.strftime("%H%M"))<1345) or int(twdt.strftime("%H%M"))>=1450:
            _str += "期貨交易時段"

        elif int(twdt.strftime("%H%M"))>=1345 and int(twdt.strftime("%H%M"))<1450:
            _str += "期貨結束時段"

        elif int(twdt.strftime("%H%M"))>=500 and int(twdt.strftime("%H%M"))<845:
            _str += "期貨結束時段"
            
    # 昨天是禮拜一到禮拜五 並且 不是假日 對於 隔日的0~5點 "盤後交易時間"
    if int(yd.strftime("%w"))>=1 and int(yd.strftime("%w"))<=5 and yd.strftime("%Y/%m/%d") not in holiday["Holiday"]:
        if int(twdt.strftime("%H%M"))<500:
            _str += "期貨交易時段"
    # 近一商品結算時段
    if month_settlement_day() and int(twdt.strftime("%H%M"))>=1300 and int(twdt.strftime("%H%M"))<1500:
        _str += "===期貨近一結算時段==="
    if "期貨" not in _str:
        _str += "期貨休息時段"

    if twdt.strftime("%Y/%m/%d") not in holiday["Holiday"] and int(twdt.strftime("%w"))>=1 and int(twdt.strftime("%w"))<=6:
        if int(twdt.strftime("%H%M")) < 200:
        # 午夜時段
            sleepTime = 40
        elif int(twdt.strftime("%H%M")) < 500:
        # 凌晨時段
            sleepTime = 120
        elif int(twdt.strftime("%H%M")) < 830:
        # 晚盤休息時段
            sleepTime = 1200
        elif int(twdt.strftime("%H%M")) < 900:
        # 開盤準備
            sleepTime = 30
        elif int(twdt.strftime("%H%M")) < 1130:
        # 盤中 前段
            sleepTime = 5
        elif int(twdt.strftime("%H%M")) < 1345:
        # 盤中 後段
            sleepTime = 6
        elif int(twdt.strftime("%H%M")) < 1450:
        # 早盤休息時段
            sleepTime = 600
        elif int(twdt.strftime("%H%M")) < 1800:
        # 盤後 晚餐前時間
            sleepTime = 10
        # 盤後 晚餐後時間
        else:
            sleepTime = 10
    if "期貨休息" in _str:
        sleepTime = 1200

    return _str, sleepTime

# 當月結算日
def month_settlement_day():
    tz = timezone(timedelta(hours=+8))
    twdt = datetime.now(tz)

    # 取得今天 年, 月, 日
    y = int(twdt.strftime("%Y"))
    m = int(twdt.strftime("%m"))
    d = 15
    # 第三個禮拜三 會在15到21號之間
    while 3 != int(date(y, m, d).strftime("%w")):
        d+=1
    return date(y, m, d).strftime("%Y/%m/%d") == twdt.strftime("%Y/%m/%d")

# 交易所休息日
def get_twseHoliday():
    y = datetime.now(timezone(timedelta(hours=+8))).strftime("%Y")
    
    filepath = y+"holiday.json"
    if os.path.isfile(filepath) == False:
        url = "https://www.twse.com.tw/holidaySchedule/holidaySchedule?response=open_data"
        req = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'}).content
        data = pd.read_csv(io.StringIO(req.decode('utf-8')))
        holiday = {"Holiday":[]}
        holiday_str = ["放假1日", "無交易", "補假1日", "調整放假"]
        for i in range(len(data)):
            date = str(int(data["日期"].iloc[i])+19110000)
            for h in holiday_str:
                if h in data["說明"].iloc[i]:
                    holiday["Holiday"].append(date[:4]+"/"+date[4:6]+"/"+date[6:8])
                    break
        
        with open (filepath, 'w', encoding='utf8') as f: 
            json.dump(holiday, f, indent=4)
            f.close()
    with open (filepath, 'r', encoding='utf8') as jfile:
        jdata = json.load(jfile)
        jfile.close()
    return jdata

# 證卷服務
def twStockService(dayparts):
    trading_num = 0
    j_order = rw.r_order()

    if "股票開盤時段" in dayparts:
        print ("股票 opening...")
    elif "股票交易時段" in dayparts:
        # 取得所需股票
        print ("stocks_info")
        str_stocks = ""
        for id in j_order["twStocks"]:
            if j_order["twStocks"][id]["ticker"] not in str_stocks and j_order["twStocks"][id]["state"] == "委":
                str_stocks+=j_order["twStocks"][id]["ticker"]+".tw|"
        
        if str_stocks != "":
            stocks_info = get_stocks_info(str_stocks[:-1])

        # 委託單 交易處理
        for id in j_order["twStocks"]:
            order = j_order["twStocks"][id]
            if order["state"] == "委":
                trading_num += 1
                print("委託單 交易處理", id)
                user = id[:-5]
                j_gamer = rw.r_gamer()
                gamer = j_gamer[user]
                # 交易前比對 可動用金額是否足夠應付新倉量
                available_money = get_available_money(user)
                # 可動用金額不足 結束此單委託
                if available_money/order["price"] < order["new_lots"]:
                    print ("可動用金額不足")
                    order["state"] = "退"
                    order["extra"] += "帳戶可動用餘額不足_"
                    order["extra"] += "帳戶可動用餘額 : "+ str(available_money)+"_"
                else:
                    # "name" "time" "price" "tv" "best_ask_p" "best_bid_p" "best_ask_v" "best_bid_v"
                    s_info = stocks_info[order["ticker"]]
                    print (s_info)
                    info_p, info_v = s_info["price"], s_info["tv"]

                    # m 本次逐筆交易量, p_v 本次交易金額與量, o_lots 本次委託量
                    m = 0
                    p_v={}
                    o_lots = order["new_lots"]
                    if order["price"] == info_p:
                        print ("price", info_p)
                        # (當前成交價或最優一筆)與委託價相同 交易量等於 委託量與交易量取最小
                        if s_info["best_ask_p"][0] == info_p and order["type"] == "買":
                            info_v += s_info["best_ask_v"][0]
                        elif s_info["best_bid_p"][0] == info_p and order["type"] == "賣":
                            info_v += s_info["best_bid_v"][0]

                        m = min (o_lots, info_v)
                        o_lots -= m
                        p_v[info_p] = m
                    elif order["price"] > info_p and order["type"] == "買":
                        print ("買", info_p)
                        # 當前交易價格低於委託價時 交易量往上吃到大於委託價
                        m = min( o_lots, info_v)
                        o_lots-=m
                        p_v[info_v] = m
                        for i in range(len(s_info["best_ask_p"])):
                            if s_info["best_ask_p"][i] > order["price"] or o_lots<=0:
                                break
                            m = min(o_lots, s_info["best_ask_v"][i])
                            o_lots-=m
                            if s_info["best_ask_p"][i] in p_v:
                                p_v[s_info["best_ask_p"][i]] += m
                            else:
                                p_v[s_info["best_ask_p"][i]] = m
                    elif order["price"] < info_p and order["type"] == "賣":
                        print ("賣", info_p)
                        m = min(o_lots, info_p)
                        o_lots-=m
                        p_v[info_p] = m
                        for i in range(len(s_info["best_bid_v"])):
                            if s_info["best_bid_p"][i] < order["price"] or o_lots<=0:
                                break
                            m = min(o_lots, s_info["best_bid_v"][i])
                            o_lots-=m
                            if s_info["best_bid_p"][i] in p_v:
                                p_v[s_info["best_bid_p"][i]] += m
                            else:
                                p_v[s_info["best_bid_p"][i]] = m

                    for p in p_v:
                        tw = timezone(timedelta(hours=+8))
                        twdt = datetime.now(tw)
                        if p_v[p] > 0:
                            if str(p) in order["p_v"]:
                                order["p_v"][str(p)] += p_v[p]
                            else:
                                order["p_v"][str(p)] = p_v[p]
                            
                            if order["type"] == "賣":
                                # 如果委託單為賣單
                                m = min (order["new_lots"], p_v[p])
                                order["new_lots"] -= m
                                p_v[p] -= m
                                gamer["twStocks"][order["ticker"]]["Lots"] -= m
                                order["detail"][twdt.strftime("%H:%M:%S.%f")[:-2]] = "賣出 價："+str(p)+", 量："+str(m)
                                
                                a_p = gamer["twStocks"][order["ticker"]]["Average_Price"]
                                print (p , a_p, order["type"], m)
                                income = round((float(p)-a_p)*m*1000, 2)
                                gamer["Cash"] += float(p)*m*1000
                                gamer["realizedProfit"] += income
                                order["income"] += float(p)*m*1000

                            elif order["type"] == "買":
                                m = min (order["new_lots"], p_v[p])
                                order["new_lots"] -= m
                                p_v[p] -= m
                                order["detail"][twdt.strftime("%H:%M:%S.%f")[:-2]] = "買入 價："+str(p)+", 量："+str(m)

                                if order["ticker"] in gamer["twStocks"]:
                                    a_p = gamer["twStocks"][order["ticker"]]["Average_Price"]
                                    lot = gamer["twStocks"][order["ticker"]]["Lots"]
                                    # 更改持有均價 
                                    gamer["twStocks"][order["ticker"]]["Average_Price"] = round((a_p*lot + float(p)*m)/(lot + m), 2)
                                    # 更改 持有數量
                                    gamer["twStocks"][order["ticker"]]["Lots"] += m
                                else:
                                    gamer["twStocks"][order["ticker"]] = {}
                                    gamer["twStocks"][order["ticker"]]["Lots"] = m
                                    gamer["twStocks"][order["ticker"]]["Average_Price"] = float(p)
                                pay = round(float(p)*m*-1000, 2)
                                gamer["Cash"] += pay
                                order["income"] += pay
                    
                j_gamer[user] = gamer
                if order["new_lots"] == 0:
                    order["state"] = "成"
                    j_gamer = newTwStocksDetail(order, j_gamer, datetime.now(timezone(timedelta(hours=+8))).strftime("%Y-%m-%d"), id, user)
                    
                j_order["twStocks"][id] = order
                rw.w_gamer(j_gamer)
    elif "股票結束時段" in dayparts:
        # 取台灣時間
        tw = timezone(timedelta(hours=+8))
        twtoday = datetime.now(tw).strftime("%Y-%m-%d")
        j_gamer = rw.r_gamer()

        # 判斷單子所屬人是誰的做歸檔
        for orderId in j_order["twStocks"]:
            order = j_order["twStocks"][orderId]
            gamerId = orderId[:-5]
            if gamerId in j_gamer:
                print (gamerId, orderId)
                if twtoday not in j_gamer[gamerId]["detail"]:
                    j_gamer[gamerId]["detail"][twtoday] = {}
                if orderId not in j_gamer[gamerId]["detail"][twtoday]:
                    j_gamer = newTwStocksDetail(order, j_gamer, datetime.now(timezone(timedelta(hours=+8))).strftime("%Y-%m-%d"), orderId, gamerId)
        rw.w_gamer(j_gamer)
        j_order["twStocks"] = {}
    elif "股票休息時段" in dayparts:
        w=1

    time.sleep(0.5)
    rw.w_order(j_order)
    return trading_num

# 期貨服務
def twFuturesService(dayparts):
    trading_num = 0
    j_order = rw.r_order()

    if "期貨近一結算時段" in dayparts:
        # 取台灣時間
        tw = timezone(timedelta(hours=+8))
        twtoday = datetime.now(tw).strftime("%Y-%m-%d")
        j_gamer = rw.r_gamer()

        delList = []
        # 找出近一結算掉
        for orderId in j_order["twFutures"]:
            if "近一" in orderId:
                delList.append(orderId)
                gamerId = orderId[:-5]
                if twtoday not in j_gamer[gamerId]["detail"]:
                    j_gamer[gamerId]["detail"][twtoday] = {}
                if orderId not in j_gamer[gamerId]["detail"][twtoday]:
                    j_gamer = newTwFuturesDetail(j_order, twtoday, j_gamer, orderId, gamerId)
                
        # 刪掉 近一
        for d in delList:
            del j_order["twFutures"][d]
        rw.w_gamer(j_gamer)
    if "期貨交易時段" in dayparts:
        # 取得所需期貨
        futures_info = {}
        for id in j_order["twFutures"]:
            if j_order["twFutures"][id]["ticker"] not in futures_info and j_order["twFutures"][id]["state"] == "委":
                f_info = get_futures_info(j_order["twFutures"][id]["ticker"])
                futures_info[j_order["twFutures"][id]["ticker"]] = f_info
            time.sleep(0.4)
        print (futures_info.keys())

        # 委託單 交易處理
        for id in j_order["twFutures"]:
            order = j_order["twFutures"][id]
            if order["state"] == "委" or order["state"] == "抵":
                trading_num += 1
                user = id[:-5]
                j_gamer = rw.r_gamer()
                gamer = j_gamer[user]
                # 交易前比對 保證金是否足夠應付新倉量
                available_money = get_available_money(user)
                # 保證金不足 結束此單委託
                if available_money/order["margin"] < order["new_lots"]:
                    order["state"] = "退"
                    order["extra"] += "單一期貨商品所需保證金 : "+str(order["margin"])+"_"
                    order["extra"] += "帳戶可動用保證金餘額 : "+ str(available_money)+"_"
                else :
                    # p 2, v 3, bv 4(買方要價, 量), sv 5(賣方喊價, 量),
                    f_info = futures_info[order["ticker"]]
                    f_price = f_info[2]
                    f_volume = f_info[3]
                    bv = f_info[4]
                    sv = f_info[5]

                    # m 本次逐筆交易量, p_v 本次交易金額與量, o_lots 本次委託量
                    m = 0
                    p_v={}
                    o_lots = order["new_lots"]+order["cover_lots"]
                    if order["price"] == f_price:
                        print ("price", f_price)
                        # (當前成交價或最優一筆)與委託價相同 交易量等於 委託量與交易量取最小
                        if sv[0]-4 == f_price and order["type"] == "多":
                            f_volume += sv[1]
                        elif bv[0]+4 == f_price and order["type"] == "空":
                            f_volume += bv[5]
                        m = min (o_lots, f_volume)
                        o_lots -= m
                        p_v[f_price] = m
                    elif order["price"] >= f_price and order["type"] == "多":
                        print ("多", f_price)
                        # 當前交易價格低於委託價時 交易量往下吃到大於委託價
                        m = min(o_lots, f_volume)
                        o_lots-=m
                        p_v[f_price] = m
                        for i in range(5):
                            if sv[0]+i-4 > order["price"] or o_lots<=0:
                                break
                            m = min(o_lots, f_volume)
                            o_lots-=m
                            if sv[0]+i-4 in p_v:
                                p_v[sv[0]+i-4] += m
                            else:
                                p_v[sv[0]+i-4] = m
                    elif order["price"] <= f_price and order["type"] == "空":
                        print ("空", f_price)
                        m = min(o_lots, f_volume)
                        o_lots-=m
                        p_v[f_price] = m
                        for i in range(5):
                            if bv[0]-i+4 < order["price"] or o_lots<=0:
                                break
                            m = min(o_lots, bv[5-i])
                            o_lots-=m
                            if bv[0]-i+4 in p_v:
                                p_v[bv[0]-i+4] += m
                            else:
                                p_v[bv[0]-i+4] = m

                    for p in p_v:
                        tw = timezone(timedelta(hours=+8))
                        twdt = datetime.now(tw)
                        if p_v[p] > 0:
                            if str(p) in order["p_v"]:
                                order["p_v"][str(p)] += p_v[p]
                            else:
                                order["p_v"][str(p)] = p_v[p]
                            
                            if order["cover_lots"] > 0:
                                # 如果委託單中的平倉量還有
                                m = min (order["cover_lots"], p_v[p])
                                order["cover_lots"] -= m
                                order["detail"][twdt.strftime("%H:%M:%S.%f")[:-2]] = "平倉 價："+str(p)+", 量："+str(m)
                                p_v[p] -= m
                                gamer["twFutures"][order["ticker"]]["Lots"] += m*order_type_n(order["type"])
                                a_p = gamer["twFutures"][order["ticker"]]["Average_Price"]
                                print (p_v , a_p, order["type"], m,f_info[6])
                                print ((float(p)-a_p))
                                print ((float(p)-a_p)*order_type_n(order["type"])*m*f_info[6]*(-1))
                                income = round((float(p)-a_p)*order_type_n(order["type"])*m*f_info[6]*(-1), 2)
                                gamer["Cash"] += income
                                gamer["realizedProfit"] += income
                                order["income"] += income
                            elif order["new_lots"] > 0:
                                m = min (order["new_lots"], p_v[p])
                                order["new_lots"] -= m
                                order["detail"][twdt.strftime("%H:%M:%S.%f")[:-2]] = "新倉 價："+str(p)+", 量："+str(m)
                                p_v[p] -= m

                                if order["ticker"] in gamer["twFutures"]:
                                    a_p = gamer["twFutures"][order["ticker"]]["Average_Price"]
                                    lot = gamer["twFutures"][order["ticker"]]["Lots"]
                                    # 更改持有平均價 
                                    gamer["twFutures"][order["ticker"]]["Average_Price"] = round((a_p*abs(lot) + float(p)*m)/(abs(lot) + m), 2)
                                    # 更改 持有數量
                                    gamer["twFutures"][order["ticker"]]["Lots"] += m*order_type_n(order["type"])
                                else:
                                    gamer["twFutures"][order["ticker"]] = {}
                                    gamer["twFutures"][order["ticker"]]["Lots"] = m*order_type_n(order["type"])
                                    gamer["twFutures"][order["ticker"]]["Average_Price"] = float(p)
                    
                j_gamer[user] = gamer
                if order["new_lots"]+order["cover_lots"] == 0:
                    order["state"] = "成"
                    j_gamer = newTwFuturesDetail(j_order, datetime.now(timezone(timedelta(hours=+8))).strftime("%Y-%m-%d"), j_gamer, id, user)
                    

                j_order["twFutures"][id] = order
                rw.w_gamer(j_gamer)
    elif "期貨結束時段" in dayparts:
        # 取台灣時間
        tw = timezone(timedelta(hours=+8))
        twtoday = datetime.now(tw).strftime("%Y-%m-%d")
        j_gamer = rw.r_gamer()

        # 判斷單子所屬人 委託單清零
        for orderId in j_order["twFutures"]:
            gamerId = orderId[:-5]
            if gamerId in j_gamer:
                if twtoday not in j_gamer[gamerId]["detail"]:
                    j_gamer[gamerId]["detail"][twtoday] = {}
                if orderId not in j_gamer[gamerId]["detail"][twtoday]:
                    j_gamer = newTwFuturesDetail(j_order, twtoday, j_gamer, orderId, gamerId)
                time.sleep(0.1)
        rw.w_gamer(j_gamer)
        j_order["twFutures"] = {}

        # 判斷使用者 是否需被強制平倉
        # ==========================
        # ========== 施工 ========== 
        # 先取得使用者 期貨 再判斷 可動用金額是否足夠 逐一賣出
        # ==========================
        for gamerId in j_gamer:
            if "Name" in j_gamer[gamerId]:
                maintenance = 0
                for twF in j_gamer[gamerId]["twFutures"]:
                    maintenance+=j_gamer[gamerId]["twFutures"][twF]*get_twFutures_maintenance_margin(twF)
                # === 需要強制平倉 ===
                if maintenance > j_gamer[gamerId]["Cash"]:
                    needBalance = maintenance - j_gamer[gamerId]["Cash"]
                    returnData = get_forced_liquidation_Num(needBalance, j_gamer[gamerId]["twFutures"])
                    print ("returnData", returnData)
                    for f in returnData:
                        type = "多"
                        if j_gamer[gamerId]["twFutures"][f]["Lots"] > 0:
                            type = "空"
                        user_entrust_order(gamerId, "twFutures", type, f, f, get_futures_info(f)[2], returnData[f], twtoday+"結束時間", {}, state="抵")

    time.sleep(0.5)
    rw.w_order(j_order)
    return trading_num


def get_forced_liquidation_Num(needBalance, twFutures):
    productName = []
    productMargin = []
    productNum = []
    for f in twFutures:
        productName.append(f)
        productMargin.append(get_twFutures_initial_margin(f))
        productNum.append(abs(twFutures[f]["Lots"]))
    print (productMargin, productNum)
    data = []
    needBalance = int(needBalance/100 + 0.5)

    for p in range(len(productMargin)):
        productMargin[p] =  int(productMargin[p]/100 + 0.5)
        data.append([])
        for i in range(needBalance+1):
            data[p].append([])
            for j in range(len(productMargin)+1):
                data[p][i].append(0)
            
    for i in range(len(productMargin)):
        price = productMargin[i]
        for j in range(needBalance+1):
            if i == 0:
                data[0][j][0] = min(productNum[0], math.ceil(j/price))
            else:
                if data[i-1][j][len(productMargin)] == 9:
                    v = min(productNum[i], math.ceil(j/price))
                    data[i][j] = data[i-1][max( 0, j-v*price)].copy()
                    data[i][j][i] = min(productNum[i], math.ceil(j/price))
                    data[i][j][len(productMargin)] = 0
                else:
                    v = min(productNum[i], int(j/price))
                    caseA = v + sum(data[i-1][max( 0, j-v*price)]) # use salf
                    caseB = sum(data[i-1][j])
                    data[i][j] = data[i-1][j].copy()

                    if caseA <= caseB:
                        data[i][j] = data[i-1][max( 0, j-v*price)].copy()
                        data[i][j][i] = v
                        data[i][j][len(productMargin)] = 0
            prove = 0
            for x in range(len(productMargin)):
                prove += data[i][j][x]*productMargin[x]
            if j > prove:
                data[i][j][len(productMargin)] = 9
    print (data[len(productMargin)-1][needBalance])
    returnData = {}
    for i in range(len(productName)):
        returnData[productName] = data[len(productMargin)-1][needBalance][i]
    return returnData

def newTwFuturesDetail(j_order, twtoday, j_gamer, orderId, gamerId):
    content = {
        "type": j_order["twFutures"][orderId]["type"],
        "ticker": j_order["twFutures"][orderId]["ticker"],
        "name": j_order["twFutures"][orderId]["ticker"],
        "totalLots": j_order["twFutures"][orderId]["lots"] - j_order["twFutures"][orderId]["new_lots"] - j_order["twFutures"][orderId]["cover_lots"],
        "lastState": j_order["twFutures"][orderId]["state"],
        "income": j_order["twFutures"][orderId]["income"],
        "detail": j_order["twFutures"][orderId]["detail"]
    }
    count_p = 0.0
    count_v = 0.0
    if content["totalLots"] > 0:
        for i in j_order["twFutures"][orderId]["p_v"]:
            count_p += float(i)*j_order["twFutures"][orderId]["p_v"][i]
            count_v += float(j_order["twFutures"][orderId]["p_v"][i])
        content["a_p"] = count_p/count_v
        if twtoday not in j_gamer[gamerId]["detail"]:
            j_gamer[gamerId]["detail"][twtoday] = {}
        j_gamer[gamerId]["detail"][twtoday][orderId] = content

    rw.w_str_to_log("newTwFuturesDetail() g_id:"+ gamerId+", o_id:"+orderId+", c:"+str(content))
    return j_gamer


def newTwStocksDetail(order, j_gamer, twtoday, orderId, gamerId):
    content = {
        "type": order["type"],
        "ticker": order["ticker"],
        "name": order["name"],
        "totalLots": order["lots"] - order["new_lots"],
        "lastState": order["state"],
        "income": order["income"],
        "detail": order["detail"]
    }
    count_p = 0
    count_v = 0
    if content["totalLots"] > 0:
        for i in order["p_v"]:
            count_p += float(i)*order["p_v"][i]
            count_v += order["p_v"][i]
        content["a_p"] = count_p/count_v
        print(twtoday)
        if twtoday not in j_gamer[gamerId]["detail"]:
            j_gamer[gamerId]["detail"][twtoday] = {}

        j_gamer[gamerId]["detail"][twtoday][orderId] = content
        
    rw.w_str_to_log("newTwStocksDetail() g_id:"+gamerId+", o_id"+orderId+", c:"+str(content))
    return j_gamer

# 取得期貨當前成交價格與量	return ....
def get_futures_info_i(futures, url):
    req = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'})
    data = req.text
    # 當前交易量
    fv = int(float(data[data.find(':',data.find('"413":'))+1 :data.find(',', data.find('"413":'))]))
    # 當前最大買價
    bp = float(data[data.find(':',data.find('"101":'))+1 :data.find(',', data.find('"101":'))])
    # 當前最小賣價
    sp = float(data[data.find(':',data.find('"102":'))+1 :data.find(',', data.find('"102":'))])
    # 當前成交價
    fp = float(data[data.find(':',data.find('"125":'))+1 :data.find(',', data.find('"125":'))])
    # 委買量 bid volume
    bvp = float(data[data.find(':',data.find('"109":'))+1 :data.find(',', data.find('"109":'))])
    bv1 = int (float(data[data.find(':',data.find('"113":'))+1 :data.find(',', data.find('"113":'))]))
    bv2 = int (float(data[data.find(':',data.find('"115":'))+1 :data.find(',', data.find('"115":'))]))
    bv3 = int (float(data[data.find(':',data.find('"117":'))+1 :data.find(',', data.find('"117":'))]))
    bv4 = int (float(data[data.find(':',data.find('"119":'))+1 :data.find(',', data.find('"119":'))]))
    bv5 = int (float(data[data.find(':',data.find('"121":'))+1 :data.find(',', data.find('"121":'))]))
    # 委賣量 ask volume
    svp = float(data[data.find(':',data.find('"110":'))+1 :data.find(',', data.find('"110":'))])
    sv1 = int (float(data[data.find(':',data.find('"114":'))+1 :data.find(',', data.find('"114":'))]))
    sv2 = int (float(data[data.find(':',data.find('"116":'))+1 :data.find(',', data.find('"116":'))]))
    sv3 = int (float(data[data.find(':',data.find('"118":'))+1 :data.find(',', data.find('"118":'))]))
    sv4 = int (float(data[data.find(':',data.find('"120":'))+1 :data.find(',', data.find('"120":'))]))
    sv5 = int (float(data[data.find(':',data.find('"122":'))+1 :data.find(',', data.find('"122":'))]))
    # point 單點價格
    point_list ={
        "大台指近一": 200,
        "大台指近二": 200,
        "小台指近一": 50,
        "小台指近二": 50,
        "金融期近一": 1000,
        "電子期近一": 200
    }
    
    return [bp, sp, fp, fv, [bvp, bv1 ,bv2, bv3, bv4, bv5], [svp, sv1, sv2, sv3, sv4, sv5], point_list[futures]]


def get_futures_info(futures):
    url_list = {"大台指近一": "https://tw.screener.finance.yahoo.net/future/q?type=tick&perd=1m&mkt=01&sym=WTX%26",
                "大台指近二": "https://tw.screener.finance.yahoo.net/future/q?type=tick&perd=1m&mkt=01&sym=WTX%40",
                "小台指近一": "https://tw.screener.finance.yahoo.net/future/q?type=tick&perd=1m&mkt=01&sym=WMT%26",
                "小台指近二": "https://tw.screener.finance.yahoo.net/future/q?type=tick&perd=1m&mkt=01&sym=WMT%40",
                "金融期近一": "https://tw.screener.finance.yahoo.net/future/q?type=tick&perd=1m&mkt=01&sym=WTF%26",
                "電子期近一": "https://tw.screener.finance.yahoo.net/future/q?type=tick&perd=1m&mkt=01&sym=WTE%26",
                }
    
    if futures not in url_list:
        print ("輸入錯誤 此期貨商品不存在。")
    url = url_list[futures]
    data = get_futures_info_i(futures, url)
    count = 0
    while True:
        time.sleep(random.random()*1+0.1)
        tdata = get_futures_info_i(futures, url)
        if tdata == data and count > 3:
            data = [data[0], data[1], data[2], data[3], [data[4][0], 0, 0, 0, 0, 0], [data[5][0], 0, 0, 0, 0, 0], data[6]]
            break
        elif tdata != data:
            data=tdata
            break
        count += 1

    return data

# 取得股票證卷當前成交價格與量	return ....
def get_stocks_info(str_stocks):
    url = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch="+ str_stocks +"&json=1&delay=0"
    print(url)
    req = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'})
    data = json.loads(req.text)
    # ['c', 'n', 'z', 'tv', 'v', 'o', 'h', 'l', 'y', 'a']
    # ['股票代號','公司簡稱','當盤成交價','當盤成交量','累積成交量','開盤價','最高價','最低價','昨收價', '前五筆賣方喊價']
    stocks_info = {}
    if "msgArray" in data:
        for info in data["msgArray"]:
            ticker = info["ex"]+"_"+info["c"]
            stocks_info[ticker] = {
                "name": info["n"],
                "time": info["t"]
            }
            # 預處理 "漲""跌"停
            if info["a"] == "-":
                stocks_info[ticker]["price"] = float(info["z"].replace("-", info["b"].split("_")[0]))
                stocks_info[ticker]["tv"] = int(info["tv"].replace("-", info["g"].split("_")[0]))
                stocks_info[ticker]["best_ask_p"] = []
                stocks_info[ticker]["best_bid_p"] = [float(i) for i in info["b"].replace("-", "_").split("_")[:-1]]
                stocks_info[ticker]["best_ask_v"] = []
                stocks_info[ticker]["best_bid_v"] = [float(i) for i in info["g"].replace("-", "_").split("_")[:-1]]
            elif info["b"] == "-":
                stocks_info[ticker]["price"] = float(info["z"].replace("-", info["a"].split("_")[0]))
                stocks_info[ticker]["tv"] = int(info["tv"].replace("-", info["f"].split("_")[0]))
                stocks_info[ticker]["best_ask_p"] = [float(i) for i in info["a"].replace("-", "_").split("_")[:-1]]
                stocks_info[ticker]["best_bid_p"] = []
                stocks_info[ticker]["best_ask_v"] = [float(i) for i in info["f"].replace("-", "_").split("_")[:-1]]
                stocks_info[ticker]["best_bid_v"] = []
            else:
                stocks_info[ticker]["price"] = float(info["z"].replace("-", info["b"].split("_")[0]))
                stocks_info[ticker]["tv"] = int(info["tv"].replace("-", info["g"].split("_")[0]))
                stocks_info[ticker]["best_ask_p"] = [float(i) for i in info["a"].replace("-", "_").split("_")[:-1]]
                stocks_info[ticker]["best_bid_p"] = [float(i) for i in info["b"].replace("-", "_").split("_")[:-1]]
                stocks_info[ticker]["best_ask_v"] = [float(i) for i in info["f"].replace("-", "_").split("_")[:-1]]
                stocks_info[ticker]["best_bid_v"] = [float(i) for i in info["g"].replace("-", "_").split("_")[:-1]]
            
    else:
        print ("data", data)
    
    return stocks_info

# 受使用者委託
def user_entrust_order(user, market, type, ticker, name, price, lots, reqtime, extra, state = "委"):
    lots = int(lots)
    price = float(price)
    # 判斷能委託之時間
    dpart = get_currentTWSEDaysPart()[0]
    order={}
    j_gamer = rw.r_gamer()
    orderid = user + datetime.now().strftime("%M")+str(random.randint(100, 1000))
    initial_margin = get_twFutures_initial_margin(ticker)
    available_money = get_available_money(user)

    if market == "twFutures":
        if "期貨結束時段" not in dpart and not("近一" in name and "期貨近一結算時段" in dpart):
            cover_lots = 0
            new_lots = lots
            # 計算新倉平倉 
            if ticker in j_gamer[user]["twFutures"] and j_gamer[user]["twFutures"][ticker]["Lots"]*order_type_n(type) < 0:
                print ("新舊不一樣")
                # 如果舊比新多 沒新倉, 如果新比舊多 新倉量為絕對值差
                if abs(j_gamer[user]["twFutures"][ticker]["Lots"]) >= abs(lots):
                    new_lots = 0
                else:
                    new_lots = abs(lots)-abs(j_gamer[user]["twFutures"][ticker]["Lots"])
                # 平倉量 就是 新舊取最小
                cover_lots = min(abs(j_gamer[user]["twFutures"][ticker]["Lots"]), abs(lots))
            print ("c n", cover_lots, new_lots)
            # 保證金不足 結束此單委託
            if available_money/initial_margin < new_lots:
                orderid = "保證金不足。 單一期貨商品所需保證金 : "+ str(initial_margin)+"\n"+"帳戶可動用保證金餘額 : "+ str(available_money)+"\n"
            else:
                order = {
                    "state": state,
                    "time": reqtime,
                    "type": type,
                    "name": name,
                    "ticker": ticker,
                    "price": price,
                    "lots": lots,
                    "new_lots": new_lots,
                    "cover_lots": cover_lots,
                    "margin": initial_margin,
                    "p_v": {},
                    "income": 0,
                    "detail":{},
                    "extra": extra if extra != None else ""
                }
        else:
            orderid = "不在委託時間"
    elif market == "twStocks":
        if "股票結束時段" in dpart:
            orderid = "不在委託時間"
        else:
            if available_money < price*lots*1000:
                orderid = "可動用資金不足， 剩餘： " + str(available_money)
            elif type == "賣" and  ticker not in j_gamer[user]["twStocks"] :
                orderid = "可賣出股數不足， 剩餘： 0"
            elif type == "賣" and lots > j_gamer[user]["twStocks"][ticker]["Lots"] :
                orderid = "可賣出股數不足， 剩餘： " + str(j_gamer[user]["twStocks"][ticker]["Lots"]*1000)
            else:
                order = {
                    "state": state,
                    "time": reqtime,
                    "type": type,
                    "name": name,
                    "ticker": ticker,
                    "price": price,
                    "lots": lots,
                    "new_lots": lots,
                    "cover_lots": 0,
                    "p_v": {},
                    "income": 0,
                    "detail":{},
                    "extra": extra if extra != None else ""
                }

    if "不" not in orderid :
        j_order = rw.r_order()
        count = 0
        while rw.r_signal()["roundCD"] == 0:
            time.sleep(0.5)
            j_order = rw.r_order()
            count+=1
            print(count)
            if count > 2:
                print("123")
                continue_order_thread = threading.Thread(target = thread_continue_order, args = (order, market, orderid, user, j_gamer, ))
                continue_order_thread.start()
                print("456")
                return "暫時的委託單號為："+orderid
        
        j_order[market][orderid] = order
        rw.w_order(j_order)
        rw.w_str_to_talk(user, j_gamer[user]["Name"]+" 委託 "+ order["type"]+order["name"] + " "+ str(order["lots"])  +"單位 "+ str(order["price"])+"元")
        print ("return "+orderid)
    
    rw.w_str_to_log("user_entrust_order() m:" + market + ", i:" + orderid + ", o:" + str(order))
    return orderid


def thread_continue_order(order, market, orderid, user, j_gamer):
    count = 0
    while rw.r_signal()["roundCD"] == 0:
        time.sleep(0.5)
        count+=1
        if count > 28:
            print ("count out 28")
            return
    j_order = rw.r_order()
    j_order[market][orderid] = order
    rw.w_order(j_order)
    rw.w_str_to_log("thread_continue_order() m:" + market + ", i:" + orderid + ", o:" + str(order))
    rw.w_str_to_talk(user, j_gamer[user]["Name"]+" 委託 "+ order["type"]+order["name"] + " "+ str(order["lots"])  +"單位 "+ str(order["price"])+"元")

# 刪除委託單
def del_user_order(user, id):
    j_order = rw.r_order()
    count = 0
    while rw.r_signal()["roundCD"] == 0:
        time.sleep(0.5)
        j_order = rw.r_order()
        count+=1
        if count > 2:
            print("count", count)
            continue_del_order_thread = threading.Thread(target = thread_continue_del_order, args = (id,))
            continue_del_order_thread.start()
            return "忙碌中...刪除："+id

    if id in j_order["twFutures"]:
        j_order["twFutures"][id]["state"] = "刪"
    elif id in j_order["twStocks"]:
        j_order["twStocks"][id]["state"] = "刪"

    rw.w_order(j_order)
    
    rw.w_str_to_log("del_user_order() i:"+ id)
    return id


def thread_continue_del_order(id):
    count = 0
    while rw.r_signal()["roundCD"] == 0:
        time.sleep(0.5)
        count+=1
        if count > 38:
            print ("count out 38")
            return

    j_order = rw.r_order()
    if id in j_order["twFutures"]:
        j_order["twFutures"][id]["state"] = "刪"
    elif id in j_order["twStocks"]:
        j_order["twStocks"][id]["state"] = "刪"
    rw.w_order(j_order)

# 取得保證金金額
def get_tw_futures_margin():
    
    ym = datetime.now(timezone(timedelta(hours=+8))).strftime("%Y%m")
    filepath = ym+"margin.json"
    
    if os.path.isfile(filepath) == False:
        url = "https://www.taifex.com.tw/cht/5/indexMargingDetail"
        req = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'})
        soup = BeautifulSoup(req.text,"html.parser")
        tr = soup.select('div.section > table > tr')
        margin = { }
        for t in tr:
            d = t.find_all('td')
            if len(d)==4:
                future = d[0].text
                margin[future] = {}
                margin[future]["Clearing"] = int(d[1].text.replace(',',''))
                margin[future]["Maintenance"] = int(d[2].text.replace(',',''))
                margin[future]["Initial"] = int(d[3].text.replace(',',''))
        with open (filepath, 'w', encoding='utf8') as f: 
            json.dump(margin, f, indent=4)
            f.close()
    with open (filepath, 'r', encoding='utf8') as jfile:
        jdata = json.load(jfile)
        jfile.close()
    
    return jdata


def get_twFutures_initial_margin(futures):
    # 造冊
    if "小台指" in futures:
        futures = "小型臺指"
    elif "台指50" in futures:
        futures = "臺灣50期貨"
    elif "台指" in futures:
        futures = "臺股期貨"
    elif "道瓊" in futures:
        futures = "美國道瓊期貨"
    elif "電子期" in futures:
        futures = "電子期貨"
    elif "金融期" in futures:
        futures = "金融期貨"

    margin = get_tw_futures_margin()
    if futures in margin:
        return margin[futures]["Initial"]
    return 999999999999


def get_twFutures_maintenance_margin(futures):
    # 造冊
    if "小台指" in futures:
        futures = "小型臺指"
    elif "台指50" in futures:
        futures = "臺灣50期貨"
    elif "台指" in futures:
        futures = "臺股期貨"
    elif "道瓊" in futures:
        futures = "美國道瓊期貨"
    elif "電子期" in futures:
        futures = "電子期貨"
    elif "金融期" in futures:
        futures = "金融期貨"

    margin = get_tw_futures_margin()
    if futures in margin:
        return margin[futures]["Maintenance"]
    return 999999999999


# 取得可動用金額
def get_available_money(gamerId):
    margin = get_tw_futures_margin()
    tatal_margin = 0
    j_gamer = rw.r_gamer()
    
    Cash = j_gamer[gamerId]["Cash"]
    futures = j_gamer[gamerId]["twFutures"]
    for i in futures:
        if i == "大台指近一" or i == "大台指近二":
            tatal_margin+=margin["臺股期貨"]["Initial"]*abs(j_gamer[str(gamerId)]["twFutures"][i]["Lots"])
        elif i == "小台指近一" or i == "小台指近二":
            tatal_margin+=margin["小型臺指"]["Initial"]*abs(j_gamer[str(gamerId)]["twFutures"][i]["Lots"])
    return int(Cash-tatal_margin)

# sort order json
def sort_Order(orderlist):
    new_orderlist = []
    while len(orderlist) > 0 :
        key = list(orderlist.keys())[0]
        for i in orderlist:
            if time.strptime(orderlist[i]["time"], "%m-%d %H:%M:%S") > time.strptime(orderlist[key]["time"], "%m-%d %H:%M:%S"):
                key = i
        orderlist[key]["key"] = key
        new_orderlist.append(orderlist[key])
        del orderlist[key]
    new_order = {"orderlist":new_orderlist}
    return new_order

#  sort detial json
def sort_detial(detailList):
    new_detailList = []
    return 0


def order_type_n(type):
    if type == "多":
        return 1
    return -1

# 取得使用者的委託單
def get_user_order(user):
    jdata = rw.r_order()
    orderlist = {}
    for j in jdata["twStocks"]:
        if user in j:
            orderlist[j]=jdata["twStocks"][j].copy()
    for j in jdata["twFutures"]:
        if user in j:
            orderlist[j]=jdata["twFutures"][j].copy()

    return sort_Order(orderlist)

# 取得使用者帳戶明細
def get_user_details(user, password):
    j_gamer = rw.r_gamer()
    if check_user_password(user, password, j_gamer):
        detailList = {}
        if user in j_gamer:
            for day in j_gamer[user]["detail"]:
                detailList[day]=j_gamer[user]["detail"][day].copy()
        return detailList
    else:
        return "帳密錯誤"

# 取得使用者帳戶細項資料
def get_user_account_details(user, password):
    j_gamer = rw.r_gamer()
    if check_user_password(user, password, j_gamer):
        detaiL={
            "Name": j_gamer[user]["Name"],
            "Title": j_gamer[user]["Title"],
            "Avatar": j_gamer[user]["Avatar"],
            "nowTitle": j_gamer[user]["nowTitle"],
            "nowAvatar": j_gamer[user]["nowAvatar"],
            "SigninTimes": j_gamer[user]["SigninTimes"],
            "lastSinginTime": j_gamer[user]["lastSinginTime"],
        }
        return detaiL
    else:
        return "帳密錯誤"

# 取得使用者帳戶庫存
def get_user_instock(user, password):
    j_gamer = rw.r_gamer()
    if check_user_password(user, password, j_gamer):    
        inStocks={
            "twStocks": j_gamer[user]["twStocks"],
            "twFutures": j_gamer[user]["twFutures"]
        }
        return inStocks
    else:
        return "帳密錯誤"

# 更改使用者帳戶名稱
def rename_user_name(user, password, name):
    j_gamer = rw.r_gamer()
    if check_user_password(user, password, j_gamer):
        j_gamer[user]["Name"] = name
        rw.w_gamer(j_gamer)
        return "成功改名："+name
    else:
        return "帳密錯誤!"


# 取得使用者證卷帳戶
def get_user_securityAccount(user, password):
    j_gamer = rw.r_gamer()
    if check_user_password(user, password, j_gamer):
        sa_json = {
            "funds": j_gamer[user]["Cash"],
            "availableMoney": get_available_money(user),
            "realizedProfit": j_gamer[user]["realizedProfit"],
            "unrealizedProfit": get_current_futures_income(user)+get_current_stocks_income(user)
        }
        return sa_json
    else:
        return "帳密錯誤!"
            
        
# 取的使用者當前的"證卷"獲利
def get_current_stocks_income(user):
    j_gamer = rw.r_gamer()
    income = 0
    if user in j_gamer:
        for s in j_gamer[user]["twStocks"]:
            s_info = get_stocks_info(s+".tw")[s]
            income += 1000 * (j_gamer[user]["twStocks"][s]["Lots"]*(s_info["price"] - j_gamer[user]["twStocks"][s]["Average_Price"]))

    return round(income, 2)

# 取的使用者當前的"期貨"獲利
def get_current_futures_income(user):
    j_gamer = rw.r_gamer()
    income = 0
    if user in j_gamer:
        for f in j_gamer[user]["twFutures"]:
            f_info = get_futures_info(f)
            income += f_info[6]*(j_gamer[user]["twFutures"][f]["Lots"]*(f_info[2] - j_gamer[user]["twFutures"][f]["Average_Price"]))

    return round(income, 2)


def check_user_password(user, password, j_gamer=None):
    if j_gamer==None:
        j_gamer = rw.r_gamer()
    if user in j_gamer and j_gamer[user]["Password"] == password:
        return True
    return False
    
    

# 使用者登入
def user_login(user, password):
    j_gamer = rw.r_gamer()
    if user in j_gamer:
        if j_gamer[user]["Password"] == password:
            j_gamer[user]["SigninTimes"] += 1
            j_gamer[user]["lastSinginTime"] = datetime.now(timezone(timedelta(hours=+8))).strftime("%Y-%m-%d %H:%M:%S")
            rw.w_gamer(j_gamer)
            return "Ok!"
        else:
            return "密碼錯誤!"
    else:
        return "帳號不存在!"

# 取的HomePage資料
def get_HomePage_Data(user, password):
    detaiL = get_user_account_details(user, password)
    returnHomePageData = {
        "state":"ok",
        "returnHomePageInfo":{
            "masterStock" : [],
            "accountName" : detaiL["Name"],
            "accountTitle" : detaiL["nowTitle"],
            "accountAvatar" : detaiL["nowAvatar"],
            "twHotStocksRank_list" : get_twHotStocksRank_list()["rankList"]
        }
    }
    
    return returnHomePageData

# 取得台灣夯股清單
def get_twHotStocksRank_list():
    j_twHotStocksList = rw.r_twHotStocksList()
    renew_thread = threading.Thread(target=renew_twHotStocksList_json, args=(j_twHotStocksList, ))
    renew_thread.start()

    return j_twHotStocksList

def renew_twHotStocksList_json(j_twHotStocksList):
    twdt = datetime.now(timezone(timedelta(hours=+8))).strftime("%Y/%m/%d %H")
    if j_twHotStocksList["renewTime"] < twdt:
        print("renew j_twHotStocksList", j_twHotStocksList["renewTime"], twdt)
        j_twHotStocksList["renewTime"] = twdt
        headers = {
            "Accept-Language":"en-US,en;q=0.9",
            "Accept-Encoding":"gzip, deflate, br",
            "User-Agent":"Java-http-client/"
        }
        # reqVolume, reqChange_up, reqChange_down, reqTurnover
        req = [None, None, None, None]
        req[0] = requests.get("https://tw.stock.yahoo.com/rank/volume?exchange=ALL", headers = headers)
        req[1] = requests.get("https://tw.stock.yahoo.com/rank/change-up?exchange=ALL", headers = headers)
        req[2] = requests.get("https://tw.stock.yahoo.com/rank/change-down?exchange=ALL", headers = headers)
        req[3] = requests.get("https://tw.stock.yahoo.com/rank/turnover?exchange=ALL", headers = headers)
        
        rankList = []
        for r in req:
            soup = BeautifulSoup(r.text, "html5lib")
            stockList = soup.find_all("ul", class_ = "M(0) P(0) List(n)")[0]
            _str = ""
            c = 0
            for li in stockList:
                c+=1
                aaa = li.find_all("span")
                if ".TWO" in aaa[1].text:
                    _str += "otc_"
                elif ".TW" in aaa[1].text:
                    _str += "tse_"
                _str += aaa[1].text+"|"
                if c >= 20:
                    break
            rankList.append(_str.replace("TWO", "tw").replace("TW", "tw")[:-1])
        j_twHotStocksList["rankList"]=rankList
        rw.w_twHotStocksList(j_twHotStocksList)

# debug 專用
def debug_check():
    j_gamer = rw.r_gamer()
    j_order = rw.r_order()
    delListf = []
    delLists = []
    for o in j_order["twFutures"]:
        if o[:-5] not in j_gamer:
            delListf.append(o)
    for o in j_order["twStocks"]:
        if o[:-5] not in j_gamer:
            delLists.append(o)

    for d in delListf:
        del j_order["twFutures"][d]
    for d in delLists:
        del j_order["twStocks"][d]
    rw.w_order(j_order)

