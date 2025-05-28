import PySimpleGUI as sg
import pandas as pd
import pyodbc
from retry import retry
try:
    layout = [
        [sg.Text('链接IP地址'), sg.InputText(key='IP')],
        [sg.Text('sa的密码'), sg.Input(key='password', password_char='*')],
        [sg.Text('数据库名称'), sg.Input(key='sjkmc')],
        [sg.Button('登录'), sg.Button('退出')]
    ]
# 创建窗口

    window = sg.Window('登录界面', layout)

    while True:
        event, values = window.read()
        if event in (None, '退出'):
            break
        elif event == '登录':

            # 连接到SQLServer数据库
            cnxn = pyodbc.connect('DRIVER={ODBC Driver 11 for SQL Server};SERVER=%s;DATABASE=%s;UID=sa;PWD=%s' % (
                values['IP'], values['sjkmc'], values['password']))
            cursor = cnxn.cursor()

            if cursor:
                sg.popup('登录成功！')
                window.close()

                text = sg.popup_get_file('选择文件')

                if text == '':
                    sg.popup('请选择', text)  # 弹窗，显示变量。
                else:


                    df = pd.read_excel(text, sheet_name='sheet1')
                    sg.popup_scrolled(df, size=(80, 25))
                    # 将数据导入数据库
                    for index, row in df.iterrows():
                        cursor.execute("INSERT INTO [dbo].[6666] (DDID, KD, KDDH) values ('%s', '%s', '%s')" % (row['订单号'], row['快递'], row['快递单号']))
                    cnxn.commit()
                    sg.popup('插入表6666完成')
                    #修改金蝶表   匹配单据编号
                    update_table_sql = '''
                                UPDATE B set b.F_KBL_Assistant = d.fmasterid,b.F_KBL_TEXT3 = C.KDDH from T_SAL_OUTSTOCK a inner join T_SAL_OUTSTOCKENTRY b on a.fid = b.fid
                                    LEFT JOIN [dbo].[6666] C ON A.FBILLNO = C.DDID inner join (
                                    select a.fid ,fmasterid,a.FNUMBER,b.FDATAVALUE from T_BAS_ASSISTANTDATAENTRY a 
                                    inner join T_BAS_ASSISTANTDATAENTRY_L b on a.FENTRYID = b.FENTRYID) d on c.kd = d.FDATAVALUE
                                    WHERE FDocumentStatus<>'C'
                        '''
                    cursor.execute(update_table_sql)
                    cnxn.commit()
                    sg.popup('update完成')
                    #清空表
                    delete_table_sql = '''
                        delete  from  [dbo].[6666]
                        '''
                    cursor.execute(delete_table_sql)
                    cnxn.commit()
                    sg.popup('完成！')



            else:
                sg.popup('连接失败！请确认数据库IP地址或者密码，数据库名是否正确')
except pyodbc.ProgrammingError as e:
    sg.popup(e)

except pyodbc.InterfaceError as e:
    sg.popup(e)
# connect = pymssql.connect('192.168.0.112', 'sa', 'kingdee@123', 'cs111')
