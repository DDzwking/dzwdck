import requests
import json
import os
import time
import secrets
import string
import hashlib
import base64
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from flask import Flask, request, jsonify
from datetime import datetime, timedelta

app = Flask(__name__)

# 微信支付配置
CERT_PATH = 'D:/jindieyunxk/1636942942_20241205_cert/apiclient_cert.pem'
KEY_PATH = 'D:/jindieyunxk/1636942942_20241205_cert/apiclient_key.pem'
APPID = 'wx4f77606f6d58827b'
MCH_ID = '1636942942'
API_KEY = '1217752501201407033233368018'
NOTIFY_URL = 'https://www.weixin.qq.com/wxpay/pay.php'
SERIAL_NO = '2A94B31303735A73C1FE696B6B4B2E431BDE3D39'  # 从微信支付商户平台获取
PRIVATE_KEY_PATH = 'D:/jindieyunxk/1636942942_20241205_cert/apiclient_key.pem'

def load_private_key(path):
    with open(path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )
    return private_key

def generate_signature(message, private_key):
    signature = private_key.sign(
        message.encode('utf-8'),
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode('utf-8')

def generate_nonce_str(length=32):
    """
    生成指定长度的随机字符串，用于 nonce_str
    :param length: 随机字符串的长度，默认为32
    :return: 随机字符串
    """
    characters = string.ascii_letters + string.digits
    nonce_str = ''.join(secrets.choice(characters) for _ in range(length))
    return nonce_str

def create_order(out_trade_no, time_expire, total):
    url = "https://api.mch.weixin.qq.com/v3/pay/transactions/native"

    # 请求body参数
    reqdata = {
        "time_expire": time_expire,
        "amount": {
            "total": total,
            "currency": "CNY"
        },
        "mchid": MCH_ID,
        "description": "汉寿县人民医院微信支付",
        "notify_url": NOTIFY_URL,
        "out_trade_no": out_trade_no,
        "goods_tag": "WXG",
        "appid": APPID,
        "attach": "自定义数据说明",
        "detail": {
            "invoice_id": "wx123",
            "goods_detail": [
                {
                    "goods_name": "医院支付",
                    "wechatpay_goods_id": "1001",
                    "quantity": 1,
                    "merchant_goods_id": "99858",
                    "unit_price": 828800
                }
            ],
            "cost_price": 608800
        },
        "scene_info": {
            "store_info": {
                "address": "汉寿县人民医院",
                "area_code": "440305",
                "name": "汉寿县人民医院",
                "id": "0001"
            },
            "device_id": "013467007045764",
            "payer_client_ip": "14.23.150.211"
        }
    }

    body = json.dumps(reqdata)
    timestamp = str(int(time.time()))
    nonce_str = generate_nonce_str()
    message = f"POST\n/v3/pay/transactions/native\n{timestamp}\n{nonce_str}\n{body}\n"
    private_key = load_private_key(PRIVATE_KEY_PATH)
    signature = generate_signature(message, private_key)

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Wechatpay-Serial": SERIAL_NO,
        "Authorization": f"WECHATPAY2-SHA256-RSA2048 mchid=\"{MCH_ID}\",nonce_str=\"{nonce_str}\",serial_no=\"{SERIAL_NO}\",timestamp=\"{timestamp}\",signature=\"{signature}\"",
    }

    # 发送POST请求
    try:
        response = requests.post(url, headers=headers, data=body, cert=(CERT_PATH, KEY_PATH))
        response.raise_for_status()  # 如果响应状态码不是200，会抛出HTTPError异常

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")  # HTTP错误
        return None, f"HTTP error occurred: {http_err}"

    except requests.exceptions.RequestException as err:
        print(f"Other error occurred: {err}")  # 其他请求错误
        return None, f"Other error occurred: {err}"

    else:
        try:
            status_code = response.status_code
            if status_code == 200:  # 处理成功
                response_data = response.json()
                code_url = response_data.get('code_url')
                return code_url, None
            else:
                print("failed, resp code =", status_code, ", return body =", response.text)
                return None, f"Request failed with status code {status_code}"
        finally:
            response.close()

def refund_order(out_trade_no, out_refund_no, refund_amount, total_amount):
    url = "https://api.mch.weixin.qq.com/v3/refund/domestic/refunds"

    # 请求body参数
    reqdata = {
        "out_trade_no": out_trade_no,
        "out_refund_no": out_refund_no,
        "amount": {
            "refund": refund_amount,
            "total": total_amount,
            "currency": "CNY"
        },
        "reason": "退款",
        "notify_url": NOTIFY_URL
    }

    body = json.dumps(reqdata)
    timestamp = str(int(time.time()))
    nonce_str = generate_nonce_str()
    message = f"POST\n/v3/refund/domestic/refunds\n{timestamp}\n{nonce_str}\n{body}\n"
    private_key = load_private_key(PRIVATE_KEY_PATH)
    signature = generate_signature(message, private_key)

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Wechatpay-Serial": SERIAL_NO,
        "Authorization": f"WECHATPAY2-SHA256-RSA2048 mchid=\"{MCH_ID}\",nonce_str=\"{nonce_str}\",serial_no=\"{SERIAL_NO}\",timestamp=\"{timestamp}\",signature=\"{signature}\"",
    }

    # 发送POST请求
    try:
        response = requests.post(url, headers=headers, data=body, cert=(CERT_PATH, KEY_PATH))
        response.raise_for_status()  # 如果响应状态码不是200，会抛出HTTPError异常

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")  # HTTP错误
        return None, f"HTTP error occurred: {http_err}"

    except requests.exceptions.RequestException as err:
        print(f"Other error occurred: {err}")  # 其他请求错误
        return None, f"Other error occurred: {err}"

    else:
        try:
            status_code = response.status_code
            if status_code == 200:  # 处理成功
                response_data = response.json()
                return response_data, None
            else:
                print("failed, resp code =", status_code, ", return body =", response.text)
                return None, f"Request failed with status code {status_code}"
        finally:
            response.close()

def query_order(out_trade_no):
    url = f"https://api.mch.weixin.qq.com/v3/pay/transactions/out-trade-no/{out_trade_no}?mchid={MCH_ID}"

    timestamp = str(int(time.time()))
    nonce_str = generate_nonce_str()
    message = f"GET\n/v3/pay/transactions/out-trade-no/{out_trade_no}?mchid={MCH_ID}\n{timestamp}\n{nonce_str}\n\n"
    private_key = load_private_key(PRIVATE_KEY_PATH)
    signature = generate_signature(message, private_key)

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Wechatpay-Serial": SERIAL_NO,
        "Authorization": f"WECHATPAY2-SHA256-RSA2048 mchid=\"{MCH_ID}\",nonce_str=\"{nonce_str}\",serial_no=\"{SERIAL_NO}\",timestamp=\"{timestamp}\",signature=\"{signature}\"",
    }

    try:
        response = requests.get(url, headers=headers, cert=(CERT_PATH, KEY_PATH))
        response.raise_for_status()  # 如果响应状态码不是200，会抛出HTTPError异常
        response_data = response.json()
        trade_state_desc = response_data.get('trade_state_desc', 'Unknown')
        return trade_state_desc
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")  # HTTP错误
        return f"HTTP error occurred: {http_err}"
    except requests.exceptions.RequestException as err:
        print(f"Other error occurred: {err}")  # 其他请求错误
        return f"Other error occurred: {err}"

@app.route('/create_order', methods=['POST'])
def handle_create_order():
    data = request.json
    out_trade_no = data.get('out_trade_no')
    total = data.get('total')

    if not out_trade_no or not total:
        return jsonify({"error": "out_trade_no and total are required"}), 400

    # 计算 time_expire 为当前时间加上24小时
    time_expire = (datetime.utcnow() + timedelta(hours=24)).isoformat() + "+00:00"

    code_url, error = create_order(out_trade_no, time_expire, total)
    if error:
        return jsonify({"error": error}), 500

    return jsonify({"code_url": code_url})

@app.route('/refund_order', methods=['POST'])
def handle_refund_order():
    data = request.json
    out_trade_no = data.get('out_trade_no')
    out_refund_no = data.get('out_refund_no')
    refund_amount = data.get('refund_amount')
    total_amount = data.get('total_amount')

    if not out_trade_no or not out_refund_no or not refund_amount or not total_amount:
        return jsonify({"error": "out_trade_no, out_refund_no, refund_amount, and total_amount are required"}), 400

    refund_data, error = refund_order(out_trade_no, out_refund_no, refund_amount, total_amount)
    if error:
        return jsonify({"error": error}), 500

    return jsonify(refund_data)

@app.route('/query_order', methods=['POST'])
def handle_query_order():
    data = request.json
    out_trade_no = data.get('out_trade_no')

    if not out_trade_no:
        return jsonify({"error": "out_trade_no is required"}), 400

    trade_state_desc = query_order(out_trade_no)
    print(out_trade_no + "订单状态：" + trade_state_desc)
    return jsonify({"trade_state_desc": trade_state_desc})

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5401)
#1. 查询订单接口 (/query_order)#http://192.168.0.110:5401/query_order---{"out_trade_no": "12177525s407033233368018313212"}--
#2. 退款接口 (/refund_order)#http://192.168.0.110:5401/refund_order----{"out_trade_no": "12177525s407033233368018313212", "out_refund_no": "12177525s407033233368018313212", "refund_amount": 1, "total_amount": 1}
#3. 创建订单接口 (/create_order)#http://192.168.0.110:5401/create_order---{"out_trade_no": "12177525s407033233368018313212", "total": 1}



