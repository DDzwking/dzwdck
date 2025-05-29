import base64
from urllib.parse import urlencode
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
# -*- coding: utf-8 -*-
import requests as requests
from flask import Flask, request
import json
from decimal import Decimal

app = Flask(__name__)


# 只接受POST方法访问
@app.route("/dzw1.0", methods=["POST"])  # http://192.168.1.196:5000/test_1.0
def check():
    # 默认返回内容

    # -*- coding: UTF-8 -*-

    return_dict = {'return_code': '200', 'return_info': '转发处理成功', 'result': False}
    # 判断传入的json数据是否为空
    if request.get_data() is None:
        return_dict['return_code'] = '5004'
        return_dict['return_info'] = '请求参数为空'
        return json.dumps(return_dict)

    # 获取传入的参数
    post_Data1 = request.get_data()
    # 传入的参数为bytes类型，需要转化成json
    post_Data = json.loads(post_Data1)

    workflowId = post_Data["workflowId"]
    requestName = post_Data["requestName"]
    mainData = post_Data["mainData"]
    mainData = json.dumps(mainData)
    detailData = post_Data["detailData"]
    detailData = json.dumps(detailData)
    requestid = post_Data["requestid"]
    USERID = post_Data["ygid"]
    otherParams = "save"
    # sqfkje = post_Data["mainData"]
    # (len(post_Data['mainData'])):
    # ata['mainData'][10]['fieldValue'])
    #
    urlid = 'http://192.168.51.55:8080/api/tai/GetUserID'
    dataid = '{"workCode":"%d"}' % USERID
    responseid = requests.post(url=urlid, data=dataid)
    print(urlid)
    print(dataid)
    # E错误 S成功
    print(responseid.text)
    if json.loads(responseid.text)["CODE"] == "S":
        id = json.loads(responseid.text)["USERID"]

        # 第一步获取加密公匙
        url = 'HTTP://192.168.51.55:8080/api/ec/dev/auth/regist'
        headers1 = {"appid": "jindie"}
        response = requests.post(url=url, headers=headers1)  # 返回值
        gkey = (json.loads(response.text))["spk"]
        # print(gkey)

        key = gkey
        pubkey = '''-----BEGIN PUBLIC KEY-----
           %s
               -----END PUBLIC KEY-----''' % key
        text1 = (json.loads(response.text))["secret"]
        rsakey = RSA.importKey(pubkey.encode())
        ciper = PKCS1_v1_5.new(rsakey)
        zh1 = base64.b64encode(ciper.encrypt(text1.encode())).decode()
        # print("-------------------------------------------------------------------------------------------------------")
        # print(zh1)

        # 第2步传入加密的secret和appid，获取token
        url2 = 'HTTP://192.168.51.55:8080/api/ec/dev/auth/applytoken'
        headers2 = {"secret": zh1, "appid": "jindie"}
        response1 = requests.post(url=url2, headers=headers2)  # 返回值
        token = (json.loads(response1.text))["token"]
        # print("-------------------------------------------------------------------------------------------------------")
        # print(token)
        # 加密suerid
        pubkey = '''-----BEGIN PUBLIC KEY-----
        %s
              -----END PUBLIC KEY-----''' % key
        text2 = id
        rsakey = RSA.importKey(pubkey.encode())
        ciper = PKCS1_v1_5.new(rsakey)
        zh2 = base64.b64encode(ciper.encrypt(text2.encode())).decode()
        # print("-------------------------------------------------------------------------------------------------------")
        # print(zh2)
        # 判断传入新增接口还是修改提交接口
        if requestid != '0':
            print("提交")
            url3 = 'HTTP://192.168.51.55:8080/api/workflow/paService/submitRequest'  # 修改
            headers3 = {"Content-Type": "application/x-www-form-urlencoded", "appid": "jindie", "token": token,
                        "userid": zh2}
            json_str = detailData
            data = json.loads(json_str)
            data[0]["deleteAll"] = "1"
            detailData = json.dumps(data)
            print(detailData)
            data = {'workflowId': workflowId, 'requestName': requestName, 'mainData': mainData,
                    'detailData': detailData,
                    'requestId': requestid}
            response = requests.post(url=url3, headers=headers3, data=data)  # 返回值
            b = json.loads(response.text)
        else:
            url3 = 'http://192.168.51.55:8080/api/workflow/paService/doCreateRequest'  # 新增
            headers3 = {"Content-Type": "application/x-www-form-urlencoded", "appid": "jindie", "token": token,
                        "userId": zh2}
            data = {'workflowId': workflowId, 'requestName': requestName, 'mainData': mainData,
                    'detailData': detailData, "otherParams": '{"isnextflow":0}'}
            response = requests.post(url=url3, headers=headers3, data=data)  # 返回值
            print(headers3)
            print(data)
            print(response.text+"12")
            b = json.loads(response.text)["data"]["requestid"]
            print(b)
        #print(b)
        #print(data)
        #print(post_Data)
        # print(requestid)

        # 对参数进行操作
        # return_dict['result'] = tt(data)#返回我写的返回值
        return_dict = b  # 返回mes接口的返回值
        return json.dumps(return_dict, ensure_ascii=False)
    else:
        print(responseid.text)

        return_dict = 0  # 返回mes接口的返回值
        return json.dumps(return_dict, ensure_ascii=False)


if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=100)
# {"return_code": "200", "return_info": "转发处理成功", "result": false, "OA返回result": 170924}
