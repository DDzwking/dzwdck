import logging
import xml.etree.ElementTree as ET
from flask import Flask, request, abort, Response, jsonify
import requests
from urllib.parse import unquote
import ierror  # 企业微信官方错误码
from WXBizMsgCrypt import WXBizMsgCrypt  # 企业微信官方加解密库

# ================== 配置区域 ==================
# 企业微信配置
WX_CORPID = "wwe776c298a1e9788e"          # 企业ID
WX_SECRET = "UUgYCqIB3XAo4kqHnBrBCqSMy0zbzpZM8ZAb42Xqa40"  # 通讯录同步Secret
WX_TOKEN = "6k9K42"     # 事件订阅Token
WX_AES_KEY = "u6SGLPGPtY2Gshiqv2MgJh7aR7XKzzcsUa31fL71tki"  # EncodingAESKey

# 服务配置
SERVER_PORT = 8623                        # 服务端口

# ================== 日志配置 ==================
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("WX-Kingdee-Sync")

app = Flask(__name__)

# ================== 初始化企业微信加解密对象 ==================
wx_crypt = WXBizMsgCrypt(WX_TOKEN, WX_AES_KEY, WX_CORPID)

# ================== 路由处理 ==================
@app.route('/wx_callback', methods=['GET', 'POST'])
def wx_callback():
    """企业微信回调入口"""
    logger.info("收到请求: %s %s", request.method, request.url)
    logger.info("Headers: %s", dict(request.headers))

    if request.method == 'GET':
        try:
            args = request.args.to_dict()
            logger.info("GET 参数: %s", args)

            msg_sign = args.get('msg_signature', '')
            timestamp = args.get('timestamp', '')
            nonce = args.get('nonce', '')
            echo_str_encoded = args.get('echostr', '')
            echo_str = unquote(echo_str_encoded)

            ret, decrypted_echo = wx_crypt.VerifyURL(
                sMsgSignature=msg_sign,
                sTimeStamp=timestamp,
                sNonce=nonce,
                sEchoStr=echo_str
            )

            if ret != ierror.WXBizMsgCrypt_OK:
                logger.error(f"验证失败，错误码: %d", ret)
                abort(403)

            if isinstance(decrypted_echo, bytes):
                decrypted_echo = decrypted_echo.decode('utf-8')
            logger.info("返回 echostr: %s", decrypted_echo)
            return Response(decrypted_echo, mimetype='text/plain')

        except Exception as e:
            logger.error(f"GET处理异常: %s", str(e), exc_info=True)
            abort(500)

    elif request.method == 'POST':
        try:
            post_data = request.data
            #logger.info("POST 原始数据 (加密内容): %s", post_data)

            args = request.args.to_dict()
            #logger.info("POST URL参数: %s", args)

            msg_sign = args.get('msg_signature', '')
            timestamp = args.get('timestamp', '')
            nonce = args.get('nonce', '')

            ret, decrypted_xml = wx_crypt.DecryptMsg(
                sPostData=post_data,
                sMsgSignature=msg_sign,
                sTimeStamp=timestamp,
                sNonce=nonce
            )

            if ret != ierror.WXBizMsgCrypt_OK:
                logger.error(f"解密失败，错误码: %d", ret)
                return "fail"

            #logger.info("解密后XML内容: %s", decrypted_xml)

            root = ET.fromstring(decrypted_xml)
            event_type = root.find('Event').text
            change_type = root.find('ChangeType').text if root.find('ChangeType') is not None else ''
            user_id = root.find('UserID').text if root.find('UserID') is not None else ''

            logger.info("收到事件类型: %s, 变更类型: %s, UserID: %s", event_type, change_type, user_id)

            # ✅ 构造并发送给本地服务
            forward_data = {
                "change_type": change_type,
                "userid": user_id
            }

            try:
                response = requests.post(
                    "http://127.0.0.1:5000/query_user",
                    json=forward_data,
                    timeout=5
                )
                logger.info("【自动转发】响应码: %d, 返回内容: %s", response.status_code, response.text)
            except Exception as e:
                logger.error("【自动转发失败】错误: %s", str(e))

            return "success"

        except Exception as e:
            logger.exception("POST处理异常: %s", str(e))
            return "fail"


# ================== 启动服务 ==================
if __name__ == '__main__':
    logger.info("启动服务...")
    app.run(host='0.0.0.0', port=SERVER_PORT)
