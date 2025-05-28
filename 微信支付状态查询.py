import requests
import json
import time
import secrets
import string
import hashlib
import base64
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from flask import Flask, request, jsonify

app = Flask(__name__)

# 微信支付配置
CERT_PATH = 'F:/python charm/项目文档/1636942942_20241205_cert/apiclient_cert.pem'
KEY_PATH = 'F:/python charm/项目文档/1636942942_20241205_cert/apiclient_key.pem'
APPID = 'wx4f77606f6d58827b'
MCH_ID = '1636942942'
API_KEY = '1217752501201407033233368018'
NOTIFY_URL = 'https://www.weixin.qq.com/wxpay/pay.php'
SERIAL_NO = '2A94B31303735A73C1FE696B6B4B2E431BDE3D39'  # 从微信支付商户平台获取
PRIVATE_KEY_PATH = 'F:/python charm/项目文档/1636942942_20241205_cert/apiclient_key.pem'

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
    characters = string.ascii_letters + string.digits
    nonce_str = ''.join(secrets.choice(characters) for _ in range(length))
    return nonce_str

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

@app.route('/query_order', methods=['POST'])
def handle_query_order():
    data = request.json
    out_trade_no = data.get('out_trade_no')

    if not out_trade_no:
        return jsonify({"error": "out_trade_no is required"}), 400

    trade_state_desc = query_order(out_trade_no)
    print(out_trade_no+"订单状态："+trade_state_desc)
    return jsonify({"trade_state_desc": trade_state_desc})

if __name__ == "__main__":
    app.run(debug=True,  host='0.0.0.0', port=5001)
#{"out_trade_no": "1217752501201407033233368018"}  ##http://127.0.0.1:5001/query_order