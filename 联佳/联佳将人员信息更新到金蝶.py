import json
import requests
from flask import Flask, request, jsonify
import datetime
import time
import pandas as pd

# 获取当前日期和时间
app = Flask(__name__)

# ================== 企业微信配置 ==================
CORP_ID = "wwe776c298a1e9788e"  # 企业ID
CORP_SECRET = "UUgYCqIB3XAo4kqHnBrBCqSMy0zbzpZM8ZAb42Xqa40"  # 通讯录同步Secret

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


# ================== 部门映射加载 ==================
def load_department_mapping():
    """从 dyb.xlsx 中加载企业微信部门与金蝶岗位映射"""
    df = pd.read_excel("C:\\Users\\Administrator\\PycharmProjects\\pythonProject\\dyb.xlsx")

    mapping = {}
    for _, row in df.iterrows():
        wecom_dept_id = str(row["企业微信部门ID"]).strip() if not pd.isna(row["企业微信部门ID"]) else ""

        # 强制转换为字符串，并去掉 .0
        kingdee_dept_id = str(int(row["金蝶部门ID"])) if not pd.isna(row["金蝶部门ID"]) else "qywxbm"
        job_code = str(row["岗位编码"]).strip() if not pd.isna(row["岗位编码"]) else "GW098145"

        mapping[wecom_dept_id] = {
            "kingdee_dept_id": kingdee_dept_id,
            "job_code": job_code
        }
    return mapping


# 全局缓存一次
try:
    DEPARTMENT_MAPPING = load_department_mapping()
except Exception as e:
    print(f"❌ 加载 dyb.xlsx 失败: {str(e)}")
    DEPARTMENT_MAPPING = {}


# ================== 企业微信API ==================
class WeComAPI:
    def __init__(self):
        self.access_token = None
        self.expires_in = 0
        self.fetch_time = 0  # 获取 token 的时间戳

    def get_access_token(self):
        current_time = time.time()

        # 如果 token 存在且未过期，直接返回
        if self.access_token and (current_time - self.fetch_time) < self.expires_in:
            return self.access_token

        url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={CORP_ID}&corpsecret={CORP_SECRET}"
        try:
            response = requests.get(url)
            result = response.json()
            if result.get('errcode') == 0:
                self.access_token = result['access_token']
                self.expires_in = result.get('expires_in', 7200)  # 默认 2 小时
                self.fetch_time = current_time
                print(f"✅ 成功获取 access_token，有效期 {self.expires_in} 秒")
                return self.access_token
            else:
                print(f"❌ 获取 access_token 失败: {result.get('errmsg')}")
                return None
        except Exception as e:
            print(f"请求接口异常: {str(e)}")
            return None

    def get_user_info(self, userid):
        if not self.get_access_token():
            print("⚠️ access_token 获取失败")
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
    if change_type in ['create_user']:
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
        # 获取企业微信部门ID
        wecom_dept_ids = user_info.get("department", [])
        print(f"【创建员工】企业微信部门ID: {wecom_dept_ids}")

        # 默认值
        kingdee_dept_id = "qywxbm"
        job_code = "GW098145"

        # 只取第一个部门进行匹配
        if wecom_dept_ids:
            main_wecom_dept_id = str(wecom_dept_ids[0])
            dept_map = DEPARTMENT_MAPPING.get(main_wecom_dept_id)
            if dept_map:
                kingdee_dept_id = dept_map["kingdee_dept_id"]
                job_code = dept_map["job_code"]
            else:
                print(f"⚠️ 未找到企业微信部门ID [{main_wecom_dept_id}] 对应的金蝶映射，使用默认值")

        kingdee_data = {
            "formid": "BD_Empinfo",
            "data": json.dumps({
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
                    "FUseOrgId": {"FNumber": "98"},
                    "FCreateOrgId": {"FNumber": "98"},
                    "FDescription ": "",
                    "FCreateSaler": "false",
                    "FCreateUser": "false",
                    "FCreateCashier": "false",
                    "FJoinDate": "",
                    "FSHRMapEntity": {},
                    "FPostEntity": [{
                        "FWorkOrgId": {"FNumber": "98"},
                        "FPostDept": {"FNumber": kingdee_dept_id},
                        "FPost": {"FNumber": job_code},
                        "FStaffStartDate": current_time,
                        "FIsFirstPost": "true",
                        "FStaffDetails": 0
                    }]
                }
            })
        }

        try:
            response = requests.post(
                url=KINGDEE_CREATE_URL,
                cookies=cookies,
                json=kingdee_data,
                timeout=10
            )
            result = response.json()

            # 判断是否创建成功
            if result.get('Result', {}).get('ResponseStatus', {}).get('IsSuccess') is True:
                print("✅ 金蝶员工创建成功", result, "创建员工数据:", kingdee_data, "企业微信查询的数据", user_info)
            else:
                print("❌ 金蝶员工创建失败，详细信息:", result, "创建员工数据:", kingdee_data)

            return jsonify({
                "code": 0,
                "message": "创建员工完成",
                "data": result
            })

        except Exception as e:
            print("创建员工失败:", str(e))
            return jsonify({"code": -5, "message": "创建员工失败", "error": str(e)})

    elif change_type == 'delete_user':
        delete_data = {
            "formid": "BD_Empinfo",
            "data": json.dumps({
                "CreateOrgId": 0,
                "Numbers": [userid],
                "Ids": "",
                "PkEntryIds": [],
                "NetworkCtrl": "",
                "IgnoreInterationFlag": ""
            })
        }

        try:
            response = requests.post(
                url=KINGDEE_DELETE_URL,
                cookies=cookies,
                json=delete_data,
                timeout=10
            )
            result = response.json()

            # 判断是否删除成功
            if result.get('Result', {}).get('ResponseStatus', {}).get('IsSuccess') is True:
                print("✅ 金蝶员工反审核成功", result)
            else:
                print("❌ 金蝶员工反审核失败，详细信息:", result)

            return jsonify({
                "code": 0,
                "message": "反审核员工完成",
                "data": result
            })

        except Exception as e:
            print("删除员工失败:", str(e))
            return jsonify({"code": -6, "message": "删除员工失败", "error": str(e)})

    elif change_type == 'update_user':  # 先删除反审核员工任岗明细，在新建审核立员工任岗明细
        print(change_type, "修改类型")
        user_info = wecom_api.get_user_info(userid)
        staff_number = user_info.get("userid", "")
        ygbh = staff_number

        # 获取企业微信部门ID
        wecom_dept_ids = user_info.get("department", [])
        print(f"【更新员工】企业微信部门ID: {wecom_dept_ids}")

        # 默认值
        kingdee_dept_id = "qywxbm"
        job_code = "GW098145"

        # 只取第一个部门进行匹配
        if wecom_dept_ids:
            main_wecom_dept_id = str(wecom_dept_ids[0])
            dept_map = DEPARTMENT_MAPPING.get(main_wecom_dept_id)
            if dept_map:
                kingdee_dept_id = dept_map["kingdee_dept_id"]
                job_code = dept_map["job_code"]
            else:
                print(f"⚠️ 未找到企业微信部门ID [{main_wecom_dept_id}] 对应的金蝶映射，使用默认值")

        update_data = {"data": json.dumps({
            "FormId": "BD_NEWSTAFF",
            "FieldKeys": "FStaffNumber",
            "FilterString": [
                {"Left": "", "FieldName": "FPerson.fnumber", "Compare": "67", "Value": staff_number, "Right": "",
                 "Logic": 0}],
            "OrderString": "",
            "TopRowCount": 0,
            "StartRow": 0,
            "Limit": 2000,
            "SubSystemId": ""
        })}
        query_response = requests.post(
            url="http://127.0.0.1/K3Cloud/Kingdee.BOS.WebApi.ServicesStub.DynamicFormService.ExecuteBillQuery.common.kdsvc",
            cookies=cookies,
            json=update_data,
            timeout=10
        )
        query_result = query_response.json()
        # 假设 query_result 是接口返回的 json 数据
        print(query_result)
        if query_result:
            result_list = query_result[0]  # 取出第一层列表 → ['65as4d65a4d_GW098132_100372']
            staff_number = result_list[0]  # 取出字符串 → '65as4d65a4d_GW098132_100372'
            print("查询旧记录", query_result)
            FSH_data = {"FormId": "BD_NEWSTAFF", "DATA": json.dumps({
                "CreateOrgId": 0,
                "Numbers": [staff_number],
                "Ids": "",
                "InterationFlags": "",
                "IgnoreInterationFlag": "",
                "NetworkCtrl": "",
                "IsVerifyProcInst": ""
            })}
            FSH_RESPONSE = requests.post(
                url="http://127.0.0.1/K3Cloud/Kingdee.BOS.WebApi.ServicesStub.DynamicFormService.UnAudit.common.kdsvc",
                cookies=cookies,
                json=FSH_data,
                timeout=10
            )
            print("反审核旧记录", FSH_RESPONSE.json())
            DELETE_DATA = {"FormId": "BD_NEWSTAFF", "DATA": json.dumps({
                "CreateOrgId": 0,
                "Numbers": [staff_number],
                "Ids": "",
                "NetworkCtrl": ""
            })}
            DELETE_RESPONSE = requests.post(
                url="http://127.0.0.1/K3Cloud/Kingdee.BOS.WebApi.ServicesStub.DynamicFormService.Delete.common.kdsvc",
                cookies=cookies,
                json=DELETE_DATA,
                timeout=10
            )
            print("删除旧记录", DELETE_RESPONSE.json())
            xj_data = {"FormId": "BD_NEWSTAFF", "DATA": json.dumps({
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
                "Model": {
                    "FSTAFFID": 0,
                    "FCreateOrgId": {
                        "FNumber": "98"
                    },
                    "FNumber": ygbh,
                    "FPerson": {
                        "FNumber": ygbh
                    },
                    "FUseOrgId": {
                        "FNumber": "98"
                    },
                    "FDept": {
                        "FNumber": kingdee_dept_id
                    },
                    "FPosition": {
                        "FNumber": job_code
                    },
                    "FEmpInfoId": {
                        "FNumber": ygbh
                    },
                    "FStartDate": current_time,
                    "FPOSTBILLEntity": {
                        "FIsFirstPost": "true"
                    },
                    "FOtherEntity": {},
                    "FSHRMapEntity": {}
                }})
                       }
            xj_response = requests.post(
                url="http://127.0.0.1/K3Cloud/Kingdee.BOS.WebApi.ServicesStub.DynamicFormService.Save.common.kdsvc",
                cookies=cookies,
                json=xj_data,
                timeout=10
            )
            result = xj_response.json()
            print("✅ 新建任岗员工返回:", result, "发送的json", xj_data)

            rgbm = result.get("Result", {}).get("ResponseStatus", {}).get("SuccessEntitys", [{}])[0].get(
                "Number")  # 建立的单号
            print("新建立的任岗单据为", rgbm)
            tj_data = {"FormId": "BD_NEWSTAFF", "DATA": json.dumps({
                "CreateOrgId": 0,
                "Numbers": [rgbm],
                "Ids": "",
                "SelectedPostId": 0,
                "NetworkCtrl": "",
                "IgnoreInterationFlag": ""
            })}
            tj_response = requests.post(
                url="http://127.0.0.1/K3Cloud/Kingdee.BOS.WebApi.ServicesStub.DynamicFormService.Submit.common.kdsvc",
                cookies=cookies,
                json=tj_data,
                timeout=10
            )
            sh_response = requests.post(
                url="http://127.0.0.1/K3Cloud/Kingdee.BOS.WebApi.ServicesStub.DynamicFormService.Audit.common.kdsvc",
                cookies=cookies,
                json=tj_data,
                timeout=10
            )
            print("审核任岗单", sh_response.json())

        else:
            print("金蝶未查询到该员工的任岗信息，请手工在金蝶建立对应员工的任岗信息，或者在企业微信删除该员工后重新建立")
            return jsonify({"code": -4, "message": "未找到员工信息"})

        return jsonify({"code": -3, "message": "修改类型"})
    else:
        print(change_type, "其他类型不做操作")
        return jsonify({"code": -3, "message": "未知操作"})


# ================== 启动服务 ==================
if __name__ == "__main__":
    app.run(debug=True, port=5000)
