import json
import os
import io
import random
import time
from datetime import date, datetime, timedelta, timezone
import threading

import pandas as pd
import requests
from bs4 import BeautifulSoup
import rw

# 清零 所有帳戶
def zeroing_all_accounts():
    wait_signal()
    # 歸零gamerState
    j_gamer = rw.r_gamer()
    for g in j_gamer:
        if "Name" in j_gamer[g]:
            j_gamer[g]["Cash"] = 10000000
            j_gamer[g]["realizedProfit"] = 0
            j_gamer[g]["twStocks"] = {}
            j_gamer[g]["twFutures"] = {}
            j_gamer[g]["detail"] = {}
    rw.w_gamer(j_gamer)

    # 歸零 order
    j_order = rw.r_order()
    j_order["twFutures"] = {}
    j_order["twStocks"] = {}
    j_order["twStocksDividend"] = {}
    rw.w_order(j_order)

    rw.w_str_to_log("於"+ datetime.now(timezone(timedelta(hours=+8))).strftime("%Y-%m-%d %H:%M:%S") +" 伺服器系統 執行 <所有帳戶歸零> 完成!")
    rw.w_str_to_talk("_SYSTEM", "於"+ datetime.now(timezone(timedelta(hours=+8))).strftime("%Y-%m-%d %H:%M:%S") +" 伺服器系統 執行 <所有帳戶歸零> 完成!")

# 清零 某帳戶
def zeroing_account(accountName):
    wait_signal()
    
    # 歸零gamerState
    j_gamer = rw.r_gamer()
    if "Name" in j_gamer[accountName]:
        j_gamer[accountName]["Cash"] = 0
        j_gamer[accountName]["realizedProfit"] = 0
        j_gamer[accountName]["twStocks"] = {}
        j_gamer[accountName]["twFutures"] = {}
        j_gamer[accountName]["detail"] = {}
    rw.w_gamer(j_gamer)

    # 歸零 order
    j_order = rw.r_order()
    delList = []
    for o_f, o_s, o_d in zip(j_order["twFutures"], j_order["twStocks"], j_order["twStocksDividend"]):
        if accountName in o_f:
            delList.append(o_f)
        if accountName in o_s:
            delList.append(o_s)
        if accountName in o_d:
            delList.append(o_d)

    for d in delList:
        if d in j_order["twFutures"]:
            del j_order[d]
        if d in j_order["twStocks"]:
            del j_order[d]
        if d in j_order["twStocksDividend"]:
            del j_order[d]
            
    rw.w_order(j_order)

    rw.w_str_to_log("於"+ datetime.now(timezone(timedelta(hours=+8))).strftime("%Y-%m-%d %H:%M:%S") +" 伺服器系統 執行 <"+accountName+"帳戶歸零> 完成!")


def wait_signal():
    count = 0
    while rw.r_signal()["roundCD"] == 0:
        time.sleep(0.5)
        count+=1
        if count > 40:
            print ("sudo.py wait_signal count > 40")
            break