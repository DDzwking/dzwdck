import json

import requests
from flask import Flask, request, jsonify
import datetime

# 获取当前日期和时间

app = Flask(__name__)

# ================== 企业微信配置 ==================
CORP_ID = "wwe776c298a1e9788e"
CORP_SECRET = "UUgYCqIB3XAo4kqHnBrBCqSMy0zbzpZM8ZAb42Xqa40"

# ================== 金蝶配置 ==================
KINGDEE_LOGIN_URL = "http://127.0.0.1/K3Cloud/Kingdee.BOS.WebApi.ServicesStub.AuthService.ValidateUser.common.kdsvc"
KINGDEE_CREATE_URL = "http://127.0.0.1/K3Cloud/Kingdee.BOS.WebApi.ServicesStub.DynamicFormService.Save.common.kdsvc"
KINGDEE_DELETE_URL = "http://127.0.0.1/K3Cloud/Kingdee.BOS.WebApi.ServicesStub.DynamicFormService.UnAudit.common.kdsvc"

current_time = datetime.datetime.now().strftime("%Y-%m-%d")
KINGDEE_LOGIN_DATA = {
    "acctID": "64a274e6e9c230",
    "username": "administrator",
    "password": "kingdee!23",
    "lcid": 2052
}


# ================== 企业微信API ==================
class WeComAPI:
    def __init__(self):
        self.access_token = None

    def get_access_token(self):
        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={CORP_ID}&corpsecret={CORP_SECRET}"
        try:
            response = requests.get(url)
            result = response.json()
            if result.get('errcode') == 0:
                self.access_token = result['access_token']
                return True
            else:
                print(f"获取access_token失败: {result.get('errmsg')}")
                return False
        except Exception as e:
            print(f"请求接口异常: {str(e)}")
            return False

    def get_user_info(self, userid):
        if not self.access_token:
            if not self.get_access_token():
                return None

        url = f"https://qyapi.weixin.qq.com/cgi-bin/user/get?access_token={self.access_token}&userid={userid}"

        try:
            response = requests.get(url)
            result = response.json()

            if result.get('errcode') == 0:
                return result
            else:
                print(f"获取成员信息失败: {result.get('errmsg')}")
                return None
        except Exception as e:
            print(f"请求接口异常: {str(e)}")
            return None


# 实例化 WeComAPI
wecom_api = WeComAPI()


# ================== 金蝶登录函数 ==================
def kingdee_login():
    """登录金蝶系统，返回完整 cookies"""
    try:
        response = requests.post(
            url=KINGDEE_LOGIN_URL,
            data=KINGDEE_LOGIN_DATA,
            timeout=10
        )
        response.raise_for_status()

        # 直接返回全部 cookies
        cookies = response.cookies.get_dict()
        print("【金蝶】登录成功，Cookies:", cookies)
        return cookies

    except Exception as e:
        print("【金蝶】登录异常:", str(e))
        return None


# ================== 接口路由 ==================
@app.route('/query_user', methods=['POST'])
def query_user():
    data = request.get_json()
    change_type = data.get('change_type')
    userid = data.get('userid')

    if not userid:
        return jsonify({"code": -1, "message": "缺少 userid 参数"}), 400

    print(f"【{change_type}】事件触发，UserID: {userid}")

    # 只有创建用户时才需要获取用户信息
    user_info = None
    if change_type == 'create_user' and 'update_user':
        user_info = wecom_api.get_user_info(userid)

        if not user_info:
            return jsonify({"code": -2, "message": "获取用户信息失败"})
        department_ids = user_info.get("department", [])
        user_name = user_info.get("name", "")
        print(f"【创建员工】人员姓名: {user_name}")
        print(f"【创建员工】所属部门编号: {department_ids}")

    # 登录金蝶系统获取 cookies
    cookies = kingdee_login()
    if not cookies:
        return jsonify({"code": -4, "message": "金蝶登录失败"})

    # 构造金蝶数据并执行操作
    if change_type == 'create_user':
        kingdee_data = {"formid": "BD_Empinfo", "data":json.dumps( {
            "NeedUpDateFields": [],
            "NeedReturnFields": [],
            "IsDeleteEntry": "true",
            "SubSystemId": "",
            "IsVerifyBaseDataField": "false",
            "IsEntryBatchFill": "true",
            "ValidateFlag": "true",
            "NumberSearch": "true",
            "IsAutoAdjustField": "false",
            "InterationFlags": "",
            "IgnoreInterationFlag": "",
            "IsControlPrecision": "false",
            "ValidateRepeatJson": "false",
            "IsAutoSubmitAndAudit": "true",
            "Model": {
                "FID": 0,
                "FName": user_info.get("name", ""),
                "FStaffNumber": user_info.get("userid", ""),
                "FMobile": user_info.get("mobile", ""),
                "FEmail": "",
                "FUseOrgId": {"FNumber": "96"},
                "FCreateOrgId": {"FNumber": "96"},
                "FCreateSaler": "false",
                "FCreateUser": "false",
                "FCreateCashier": "false",
                "FJoinDate": "",
                "FSHRMapEntity": {},
                "FPostEntity": [{
                    "FWorkOrgId": {"FNumber": "96"},
                    "FPostDept": {"FNumber": user_info.get("department", "")},
                    "FPost": {"FNumber": "GW000040"},
                    "FStaffStartDate": current_time,
                    "FIsFirstPost": "true",
                    "FStaffDetails": 0
                }]
            }
        })}

        try:
            response = requests.post(
                url=KINGDEE_CREATE_URL,
                cookies=cookies,
                json=kingdee_data,
                timeout=10
            )
            result = response.json()
            #print(f"创建的返回: {result}")
            #print(f"创建的data: {kingdee_data}")
            result = response.json()
            #print(f"创建的返回: {result}")

            # 判断是否创建成功
            if result.get('Result', {}).get('ResponseStatus', {}).get('IsSuccess') is True:
                print("✅ 金蝶员工创建成功", result)
            else:
                print("❌ 金蝶员工创建失败，详细信息:", result)

            return jsonify({
                "code": 0,
                "message": "创建员工完成",
                "data": result
            })

        except Exception as e:
            print("创建员工失败:", str(e))
            return jsonify({"code": -5, "message": "创建员工失败", "error": str(e)})

    elif change_type == 'delete_user':
        delete_data = {"formid": "BD_Empinfo", "data": json.dumps({
            "CreateOrgId": 0,
            "Numbers": [userid],
            "Ids": "",
            "PkEntryIds": [],
            "NetworkCtrl": "",
            "IgnoreInterationFlag": ""
        })}

        try:
            response = requests.post(
                url=KINGDEE_DELETE_URL,
                cookies=cookies,
                data=delete_data

            )
            result = response.json()
            # 打印原始数据用于调试
            #print(f"禁用的返回: {result}")
            #print(f"禁用的data: {delete_data}")

            # 判断是否删除成功
            if result.get('Result', {}).get('ResponseStatus', {}).get('IsSuccess') is True:
                print("✅ 金蝶员工反审核成功", result)
            else:
                print("❌ 金蝶员工反审核失败，详细信息:", result,delete_data)

            return jsonify({
                "code": 0,
                "message": "反审核员工完成",
                "data": result
            })

        except Exception as e:
            print("删除员工失败:", str(e))
            return jsonify({"code": -6, "message": "删除员工失败", "error": str(e)})

    elif change_type == 'update_user':
        print(change_type,"修改类型")
        return jsonify({"code": -3, "message": "修改类型"})
    else:
        print(change_type, "其他类型不做操作")
        return jsonify({"code": -3, "message": "未知操作"})


# ================== 启动服务 ==================
if __name__ == "__main__":
    app.run(debug=True, port=5000)
