import requests
from flask import Flask, request, jsonify, json

app = Flask(__name__)


@app.route('/api/data', methods=['POST'])


def handle_data():
    data = request.get_json()
    if not data or 'billNo' not in data or 'FPLX' not in data:
        return jsonify({'error': 'Invalid input'}), 400

    djbh = data['billNo']
    fplx = data['FPLX']
    print(djbh, fplx)
    # 处理数据的逻辑
    response = {
        'message': 'Data received successfully',
        'DJBH': djbh,
        'FPLX': fplx
    }
    xt_url = "http://127.0.0.1/K3Cloud/Kingdee.BOS.WebApi.ServicesStub.DynamicFormService.Push.common.kdsvc"
    tj_url = "http://127.0.0.1/K3Cloud/Kingdee.BOS.WebApi.ServicesStub.DynamicFormService.Submit.common.kdsvc"
    sh_url = "http://127.0.0.1/K3Cloud/Kingdee.BOS.WebApi.ServicesStub.DynamicFormService.Audit.common.kdsvc"

    xt = {"FormId": "SAL_OUTSTOCK",
          "Data": json.dumps({"TargetFormId": "AR_receivable", "IsEnableDefaultRule": "true", "Numbers": [djbh]})}






    response_from_xt = requests.post(  # 下推单据
        cookies=login(),
        url=xt_url,  # 与Flask运行的端口一致
        json=xt  # 使用json参数自动序列化并设置Content-Type为application/json
    )
    print(response_from_xt.text, login())
    response_data_xt = response_from_xt.json()

    if response_data_xt['Result']['ResponseStatus']['IsSuccess'] == True:
        xthnumber = response_data_xt['Result']['ResponseStatus']['SuccessEntitys'][0]['Number']
        print(xthnumber)
        response['XTHNumber'] = xthnumber
        tj = {"FormId": "AR_receivable",  # 提交json
              "Data": json.dumps({
                   "Numbers": [xthnumber]
              })}
        response_from_tj = requests.post(
            cookies=login(),
            url=tj_url,  # 与Flask运行的端口一致
            json=tj  # 使用json参数自动序列化并设置Content-Type为application/json
        )
        print(response_from_tj.text, login())
        tjfh = response_from_tj.json()
        if tjfh['Result']['ResponseStatus']['IsSuccess'] == True:
            sh = {"FormId": "AR_receivable",
              "Data": json.dumps({
                   "Numbers": [xthnumber]
              })}
            response_from_sh = requests.post(  # 下推单据
                cookies=login(),
                url=sh_url,  # 与Flask运行的端口一致
                json=sh  # 使用json参数自动序列化并设置Content-Type为application/json
            )
            print(response_from_sh.text, login())
            shfh = response_from_sh.json()
            if shfh['Result']['ResponseStatus']['IsSuccess'] == True:#应收单审核后下推
                if fplx=="1":
                    xtptfpxt={"FormId":"AR_receivable","Data":json.dumps({"RuleId":"IV_ReceivableToSalesIC_Entry" ,"Numbers": [xthnumber]})}
                    IDB = "IV_SALESIC"

                else:
                    xtptfpxt={"FormId":"AR_receivable","Data":json.dumps({"RuleId":"IV_ReceivableToSalesOC_Entry" ,"Numbers": [xthnumber]})}
                    IDB = "IV_SALESOC"
                xtptfp = requests.post(  # 下推单据
                cookies=login(),
                url=xt_url,  # 与Flask运行的端口一致
                json=xtptfpxt  # 使用json参数自动序列化并设置Content-Type为application/json
                )
                print(xtptfp.text, login())
                response_data_xtptfp = xtptfp.json()

                if response_data_xtptfp['Result']['ResponseStatus']['IsSuccess'] == True:



                    xthfpnumber = response_data_xtptfp['Result']['ResponseStatus']['SuccessEntitys'][0]['Number']
                    print(xthfpnumber)

                    ptfltj = {"FormId": IDB,  # 提交json
                          "Data": json.dumps({
                              "Numbers": [xthfpnumber]
                          })}
                    ptfptj = requests.post(  # 下推单据
                        cookies=login(),
                        url=tj_url,  # 与Flask运行的端口一致
                        json=ptfltj  # 使用json参数自动序列化并设置Content-Type为application/json
                    )

                    print(ptfptj.text, login())
                    ptfptjjk = ptfptj.json()
                    if ptfptjjk['Result']['ResponseStatus']['IsSuccess'] == True:
                        ptfpsh = {"FormId": IDB,  # 提交json
                              "Data": json.dumps({
                                  "Numbers": [xthfpnumber]
                              })}
                        ptfpshjk = requests.post(
                            cookies=login(),
                            url=sh_url,  # 与Flask运行的端口一致
                            json=ptfpsh  # 使用json参数自动序列化并设置Content-Type为application/json
                        )
                        print(ptfpshjk.text, login())
                        ptfpshjkfh = ptfpshjk.json()

                        if ptfpshjkfh['Result']['ResponseStatus']['IsSuccess'] == True:
                            return jsonify({'error': '应收单下推成功，发票下推审核成功，请通过下查或者全流程查询查看单据'}), 200
                        else:
                            return jsonify({'error': '发票审核失败2', 'response': ptfptjjk}), 500
                    else:
                        return jsonify({'error': '发票提交失败2', 'response': ptfptjjk}), 500
                else:
                    return jsonify({'error': '发票下推失败2', 'response': response_data_xtptfp}), 500







                return jsonify({'error': '审核成功1'}), 200
            else:
                return jsonify({'error': '审核失败1', 'response': response_from_tj.text}), 500
        else:
            return jsonify({'error': '提交失败1', 'response': tjfh}), 500
    else:
        print(response_data_xt)
        return jsonify({'error': '下推失败1', 'response': response_data_xt}), 500

    return jsonify(response), 200


def login():  # 定义登录函数
    dll_url = "http://127.0.0.1/K3Cloud/Kingdee.BOS.WebApi.ServicesStub.AuthService.ValidateUser.common.kdsvc"

    dll = {  #登录json
        "acctID": "68219fcffae848",
        "username": "administrator",
        "password": "kingdee@123",
        "lcid": "2052"
    }
    login_response = requests.post(url=dll_url, data=dll)

    return login_response.cookies.get_dict()  # 返回cookies,方便下次访问时携带


if __name__ == '__main__':
    app.run(debug=True)

#http://ServerIp/K3Cloud/Kingdee.BOS.WebApi.ServicesStub.AuthService.ValidateUser.common.kdsvc 登录
#http://ServerIp/K3Cloud/Kingdee.BOS.WebApi.ServicesStub.DynamicFormService.Submit.common.kdsvc 提交
#http://ServerIp/K3Cloud/Kingdee.BOS.WebApi.ServicesStub.DynamicFormService.Audit.common.kdsvc 审核
#http://ServerIp/K3Cloud/Kingdee.BOS.WebApi.ServicesStub.DynamicFormService.Push.common.kdsvc 下推


#打包代码：pyinstaller --onefile --name=K3CloudFlaskApp 二开.py
