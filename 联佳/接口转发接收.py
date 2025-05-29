# -*- coding: utf-8 -*-
import requests as requests
from flask import Flask, request
import json
from loguru import logger

app = Flask(__name__)


# 只接受POST方法访问
@app.route("/dzw1.0", methods=["POST"])  # http://10.0.3.16:100/dzw1.0
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
    post_Data = json.dumps(json.loads(post_Data1), ensure_ascii=False)
    fromid = json.loads(post_Data)['from']
    """
        KH = 客户
        gys = 供应商
        SHZ = 设备组 辅助资料
        SCDD = 生产订单
        SCYLQL = 生产用料清单
        GDZC = 固定资产

    """
    data = json.dumps(json.loads(post_Data)['data'], ensure_ascii=False)
    urlone = ''

    if fromid == 'GYS':
        # 供应商接口地址
        urlone = 'http://175.6.211.210:10014/api/WebService/GYS?JsonDateList='
    elif fromid == 'KH':
        # 客户接口地址
        urlone = 'http://10.0.1.73:10014/api/WebService/KU?JsonDateList='
    elif fromid == 'SBZ':
        # 设备组接口地址
        urlone = 'http://10.0.1.73:10014/api/WebService/SBZ?JsonDateList='
    elif fromid == 'SCDD':
        # 生产订单接口地址
        urlone = 'http://10.0.1.73:10014/api/WebService/SCDD?JsonDateList='
    elif fromid == 'SCYLQD':
        # 生产用料清单接口地址
        urlone = 'http://10.0.1.73:10014/api/WebService/MesMORequirew?MoList='
        # 物料清单BOM
    elif fromid == 'WLQDBOM':
        urlone = 'http://10.0.1.73:10014/api/WebService/BomApiList?JsonDateList='
        # 固定资产
    elif fromid == 'GDZC':
        urlone = 'http://10.0.1.73:10014/api/WebService/SB?JsonDateList='

    url = urlone + data
    print(url)
    text = json.loads(requests.get(url).text)

    logger.add("接口日志.log", rotation="12:00", retention="10 days")
    logger.debug('返回信息：' + str(text) + '地址：' + url)
    return text


if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=100)

# {"return_code": "200", "return_info": "转发处理成功", "result": false, "OA返回result": 170924}
