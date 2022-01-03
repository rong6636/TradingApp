# read and write json file

import json
import os
import time
import requests
from datetime import datetime, timedelta, timezone



# 讀取signal JSON檔
def r_signal():
    check_fileExist('signal.json')
    with open ('signal.json', 'r', encoding='utf8') as jfile:
        jdata = json.load(jfile)
        jfile.close()
    return jdata

# 寫入signal JSON檔
def w_signal(jdata):
    with open ('signal.json', 'w', encoding='utf8') as f: 
        json.dump(jdata, f, indent=4)
        f.close()

# 讀取order JSON檔
def r_order():
    check_fileExist('order.json', data={"BackupTime": "2021/01/01 00:00:01", "twFutures": {},"twStocks": {},"twStocksDividend": {}})
    with open ('order.json', 'r', encoding='utf8') as jfile:
        jdata = json.load(jfile)
        jfile.close()
    return jdata

# 寫入order JSON檔
def w_order(jdata):
    with open ('order.json', 'w', encoding='utf8') as f: 
        json.dump(jdata, f, indent=4)
        f.close()

# 讀取gamerState JSON檔
def r_gamer():
    initData={
        
    }
    check_fileExist('gamerState.json', data=initData)
    with open ('gamerState.json', 'r', encoding='utf8') as jfile:
        jdata = json.load(jfile)
        jfile.close()
    return jdata

# 寫入gamer JSON檔
def w_gamer(jdata):
    with open ('gamerState.json', 'w', encoding='utf8') as f: 
        json.dump(jdata, f, indent=4)
        f.close()

# 讀取log JSON檔
def r_log():
    twdt = datetime.now(timezone(timedelta(hours=+8)))
    filepath = "log/"+twdt.strftime("%H_%M")+".json"
    check_fileExist(filepath)
        
    with open (filepath, 'r', encoding='utf8') as jfile:
        jdata = json.load(jfile)
        jfile.close()
    return jdata

# 寫入log JSON檔
def w_log(jdata):
    twdt = datetime.now(timezone(timedelta(hours=+8)))
    filepath = "log/"+twdt.strftime("%H_%M")+".json"
    with open (filepath, 'w', encoding='utf8') as f: 
        json.dump(jdata, f, indent=4)
        f.close()

# 寫str入log JSON檔
def w_str_to_log(str_log):
    str_time = datetime.now(timezone(timedelta(hours=+8))).strftime("%d_%H:%M:%S")
    j_log = r_log()
    j_log[str_time] = str_log
    w_log(j_log)

# renew GS_Log
def renew_Gs_Log():
    filepath = "GS_Log/"+datetime.now(timezone(timedelta(hours=+8))).strftime("%d")[-1]+datetime.now(timezone(timedelta(hours=+8))).strftime("_%H")+".json"
    check_fileExist(filepath)
    j_gamer = r_gamer()
    with open (filepath, 'w', encoding='utf8') as f:
        json.dump(j_gamer, f, indent=4)
        f.close()

# 讀announcement JSON檔
def r_announcement():
    check_fileExist('announcement.json')
    with open ('announcement.json', 'r', encoding='utf8') as jfile:
        jdata = json.load(jfile)
        jfile.close()
    return jdata

# 讀 talk json
def r_talk():
    check_fileExist('talk.json')
    with open ('talk.json', 'r', encoding='utf8') as jfile:
        jdata = json.load(jfile)
        jfile.close()
    return jdata

# 寫 talk json
def w_talk(jdata):
    with open ('talk.json', 'w', encoding='utf8') as f: 
        json.dump(jdata, f, indent=4)
        f.close()

# 讀 dividend json
def r_dividend():
    initData = {
        "renewTime":"2021/01/01", 
        "ex_dividend_day":"2021/01/01", 
        "BackupTime": "2021/01/01 00:01:01"
    }
    check_fileExist("dividend.json", data=initData)
    with open ('dividend.json', 'r', encoding='utf8') as jfile:
        jdata = json.load(jfile)
        jfile.close()
    return jdata

# 寫 dividend json
def w_dividend(jdata):
    with open ('dividend.json', 'w', encoding='utf8') as f: 
        json.dump(jdata, f, indent=4)
        f.close()

# 寫msg入talk JSON檔
def w_str_to_talk(userName, msg):
    str_time = datetime.now(timezone(timedelta(hours=+8))).strftime("%d_%H:%M:%S")
    j_talk = r_talk()
    j_talk["msg"].append({
        "time" : str_time[3:-3],
        "userName" : userName,
        "msg" : msg
    })
    w_talk(j_talk)

# read twHotStocksList json
def r_twHotStocksList():
    check_fileExist('twHotStocksList.json', {"renewTime":"2021/01/01 00"})
    with open ('twHotStocksList.json', 'r', encoding='utf8') as jfile:
        jdata = json.load(jfile)
        jfile.close()
    return jdata

# write twHotStocksList json
def w_twHotStocksList(jdata):
    with open ('twHotStocksList.json', 'w', encoding='utf8') as f: 
        json.dump(jdata, f, indent=4)
        f.close()

# 確認資料存在
def check_fileExist(filepath, data = {}):
    if os.path.isfile(filepath) == False:
        with open (filepath, 'w', encoding='utf8') as f:
            json.dump(data, f, indent=4)
            f.close()

# 設置冷卻訊號時間
def set_cdSignal(cdTime = 1):
    sjson = r_signal()
    sjson["roundCD"] = cdTime
    w_signal(sjson)


# ==============================================
#  =========       BACKUP AREA       ========== 
# ==============================================

# 備份 app.jsonstorage gamerState
def backup_gamerState_json():
    j_gamer = r_gamer()
    twdt = datetime.now(timezone(timedelta(hours=+8))).strftime("%Y/%m/%d %H:%M:%S") # 備份時間
    j_gamer["BackupTime"] = twdt

    req = requests.put("https://api.jsonstorage.net/v1/json/f7bb18e6-cf4c-427f-bb80-89df18e7707e?apiKey=5b4ffe5f-a617-403e-854a-c97a4e90eb28", json = j_gamer)
    if req:
        w_gamer(j_gamer)
        print ("BackUp gamer Success in " + twdt)
    else:
        print("gamerState"+str(req))
        w_str_to_log("json_backup_gamerState() "+"req"+str(req))

# check 備份 app.jsonstorage gamerState
def check_backup_gamerState():
    j_gamer = r_gamer()
    req = requests.get("https://api.jsonstorage.net/v1/json/f7bb18e6-cf4c-427f-bb80-89df18e7707e")
    if req:
        backupGamer = req.json()
        if j_gamer["BackupTime"] < backupGamer["BackupTime"]:
            w_gamer(backupGamer)
            time.sleep(2)
            w_str_to_log("backupGamer"+"o"+j_gamer["BackupTime"]+"n"+backupGamer["BackupTime"])

# 備份到 app.jsonstorage order
def backup_order_json():
    j_order = r_order()
    twdt = datetime.now(timezone(timedelta(hours=+8))).strftime("%Y/%m/%d %H:%M:%S") # 備份時間
    j_order["BackupTime"] = twdt

    req = requests.put( "https://api.jsonstorage.net/v1/json/30632ea3-6fe0-4aa3-b10a-54c1551c021f?apiKey=5b4ffe5f-a617-403e-854a-c97a4e90eb28", json = j_order)
    if req:
        w_order(j_order)
        print ("BackUp order Success in " + twdt)
    else:
        print("order"+str(req))
        w_str_to_log("json_backup_order() "+"req"+str(req))

# check 備份 app.jsonstorage order
def check_backup_order():
    j_order = r_order()
    req = requests.get("https://api.jsonstorage.net/v1/json/30632ea3-6fe0-4aa3-b10a-54c1551c021f")
    if req:
        backupOrder = req.json()
        if j_order["BackupTime"] < backupOrder["BackupTime"]:
            w_order(backupOrder)
            time.sleep(2)
            w_str_to_log("backupOrder"+"o"+j_order["BackupTime"]+"n"+backupOrder["BackupTime"])

# 備份到 app.jsonstorage talk
def backup_talk_json():
    j_talk = r_talk()
    twdt = datetime.now(timezone(timedelta(hours=+8))).strftime("%Y/%m/%d %H:%M:%S") # 備份時間
    j_talk["BackupTime"] = twdt
    
    req = requests.put( "https://api.jsonstorage.net/v1/json/cb00cc08-990c-4935-9d9e-ac6fbe0cf372?apiKey=5b4ffe5f-a617-403e-854a-c97a4e90eb28", json = j_talk)
    if req:
        w_talk(j_talk)
        print ("BackUp talk Success in " + twdt)
    else:
        print("talk"+str(req))
        w_str_to_log("json_backup_talk() "+"req"+str(req))

# check 備份 app.jsonstorage talk
def check_backup_talk():
    j_talk = r_talk()
    req = requests.get("https://api.jsonstorage.net/v1/json/cb00cc08-990c-4935-9d9e-ac6fbe0cf372")
    if req:
        backupTalk = req.json()
        if j_talk["BackupTime"] < backupTalk["BackupTime"]:
            w_talk(backupTalk)
            time.sleep(2)
            w_str_to_log("backupTalk"+"o"+j_talk["BackupTime"]+"n"+backupTalk["BackupTime"])

# 備份到 app.jsonstorage dividend
def backup_dividend_json():
    j_dividend = r_dividend()
    twdt = datetime.now(timezone(timedelta(hours=+8))).strftime("%Y/%m/%d %H:%M:%S") # 備份時間
    j_dividend["BackupTime"] = twdt
    
    req = requests.put("https://api.jsonstorage.net/v1/json/7d67a5b3-c277-4729-bbce-d66bbb56ea1c?apiKey=5b4ffe5f-a617-403e-854a-c97a4e90eb28", json = j_dividend)
    if req:
        w_dividend(j_dividend)
        print ("BackUp dividend Success in " + twdt)
    else:
        print("dividend"+str(req))
        w_str_to_log("backup_dividend_json() "+"req"+str(req))

# check 備份 app.jsonstorage dividend
def check_backup_dividend():
    j_dividend = r_dividend()
    req = requests.get("https://api.jsonstorage.net/v1/json/7d67a5b3-c277-4729-bbce-d66bbb56ea1c")
    if req:
        backupDividend = req.json()
        if j_dividend["BackupTime"] < backupDividend["BackupTime"]:
            w_dividend(backupDividend)
            time.sleep(2)
            w_str_to_log("backupDividend"+"o"+j_dividend["BackupTime"]+"n"+backupDividend["BackupTime"])

# 備份到 app.jsonstorage
def backup_jsonData():
    if wait_signal == False:
        return
    set_cdSignal(3)
    backup_gamerState_json()
    backup_order_json()
    backup_talk_json()
    backup_dividend_json()

# check 備份 app.jsonstorage
def check_backup():
    check_backup_gamerState()
    check_backup_order()
    check_backup_talk()
    check_backup_dividend()

# ^=^=^=^=^=^=^=^=^=^=^=^=^=^=^=^=^=^=^=^=^=^=^=


# 等待冷卻訊號
def wait_signal(maxCount = 40):
    count = 0
    while r_signal()["roundCD"] == 0:
        time.sleep(0.5)
        count+=1
        if count > maxCount:
            print ("count over maxCount:", maxCount)
            return False
    return True
