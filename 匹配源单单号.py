from flask import Flask, request, jsonify
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

app = Flask(__name__)

CERT_PATH = 'F:/python charm/项目文档/1636942942_20241205_cert/apiclient_cert.pem'
KEY_PATH = 'F:/python charm/项目文档/1636942942_20241205_cert/apiclient_key.pem'
# 微信支付配置
APPID = 'wxd678efh567hg6787'
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
    """
    生成指定长度的随机字符串，用于 nonce_str
    :param length: 随机字符串的长度，默认为32
    :return: 随机字符串
    """
    characters = string.ascii_letters + string.digits
    nonce_str = ''.join(secrets.choice(characters) for _ in range(length))
    return nonce_str

@app.route('/create_order', methods=['POST'])
def create_order():
    try:
        # 获取请求体中的 JSON 数据
        reqdata = request.get_json()

        # 确保请求体包含必要的字段
        required_fields = ["time_expire", "amount", "mchid", "description", "notify_url", "out_trade_no", "goods_tag", "appid", "attach", "detail", "scene_info"]
        if not all(field in reqdata for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

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
        response = requests.post("https://api.mch.weixin.qq.com/v3/pay/transactions/native", headers=headers, data=body, cert=(CERT_PATH, KEY_PATH))
        response.raise_for_status()  # 如果响应状态码不是200，会抛出HTTPError异常

        return jsonify(response.json()), 200

    except requests.exceptions.HTTPError as http_err:
        return jsonify({"error": f"HTTP error occurred: {http_err}"}), 500

    except requests.exceptions.RequestException as err:
        return jsonify({"error": f"Other error occurred: {err}"}), 500

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
