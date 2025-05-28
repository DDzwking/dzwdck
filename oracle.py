import cx_Oracle
import pyodbc
import time
from tqdm import tqdm

# Oracle数据库连接信息
oracle_dsn = cx_Oracle.makedsn('172.16.1.25', '1521', service_name='HSRMHIS')
oracle_user = 'shwz'
oracle_password = 'shwz'

# SQL Server数据库连接信息
sql_server_conn_str = (
    r'DRIVER={ODBC Driver 18 for SQL Server};'
    r'SERVER=127.0.0.1;'
    r'DATABASE=AIS20250115004927;'
    r'UID=jdyxk;'
    r'PWD=5*h7pyp;'
    r'Encrypt=no;'
    r'TrustServerCertificate=yes;'
    r'Connection Timeout=30;'
    r'Command Timeout=120;'
)

# 表名
oracle_table = 'zhiydba.v_wz_brxx'
sql_server_table = 'UNW_t_Cust100003'

# 字段映射关系（移除 fid）
field_mapping = {
    'FNUMBER': 'CODE',
    'FMC': 'MC',
    'FINTIME': 'INTIME',
    'FOUTTIME': 'OUTTIME',
    'FKSMC': 'KSMC',
    'FZYH': 'ZYH'
}

# 默认值
default_values = {
    'FDOCUMENTSTATUS': 'C',
    'FForbidStatus': 'A'
}

def load_data():
    print("Starting data load process...")

    # 连接到Oracle
    oracle_conn = cx_Oracle.connect(user=oracle_user, password=oracle_password, dsn=oracle_dsn)
    oracle_cursor = oracle_conn.cursor()
    print("Oracle connection successful.")

    # 连接到SQL Server
    sql_server_conn = pyodbc.connect(sql_server_conn_str)
    sql_server_cursor = sql_server_conn.cursor()
    print("SQL Server connection successful.")

    # 清空目标表（保留自增种子）
    sql_server_cursor.execute(f"TRUNCATE TABLE {sql_server_table}")
    sql_server_conn.commit()
    print(f"Table {sql_server_table} truncated successfully.")

    # 查询Oracle数据
    oracle_cursor.execute(f'SELECT * FROM {oracle_table} WHERE outtime >= ADD_MONTHS(SYSDATE, -8)')
    rows = oracle_cursor.fetchall()
    print(f"Query from Oracle completed. {len(rows)} rows fetched.")

    if not rows:
        print("No data to insert. Exiting.")
        return

    # 获取Oracle列名
    oracle_columns = [desc[0] for desc in oracle_cursor.description]

    # 构建插入列（新增 FID 列）
    insert_columns = ['FID'] + list(field_mapping.keys()) + list(default_values.keys())
    insert_placeholders = ', '.join(['?' for _ in insert_columns])
    insert_query = f'INSERT INTO {sql_server_table} ({", ".join(insert_columns)}) VALUES ({insert_placeholders})'

    # 插入数据
    fid_counter = 100001  # 初始化 FID 计数器
    batch_size = 3000  # 批量插入的大小
    batch_data = []

    with tqdm(total=len(rows), desc="Inserting data", unit="row") as pbar:
        for row in rows:
            # 构建插入数据，确保所有字段均为字符串
            insert_data = [
                str(fid_counter)  # 将 FID 转换为字符串
            ] + [
                str(row[oracle_columns.index(oracle_col)])  # 确保字段值为字符串
                for sql_col, oracle_col in field_mapping.items()
            ] + [
                str(default_value)  # 确保默认值为字符串
                for default_value in default_values.values()
            ]
            batch_data.append(insert_data)
            fid_counter += 1  # 每次插入后递增 FID
            pbar.update(1)

            # 批量插入
            if len(batch_data) >= batch_size:
                sql_server_cursor.executemany(insert_query, batch_data)
                sql_server_conn.commit()
                batch_data = []

        # 插入剩余的数据
        if batch_data:
            sql_server_cursor.executemany(insert_query, batch_data)
            sql_server_conn.commit()

    print(f"Data load completed. {len(rows)} rows inserted.")

    # 关闭连接
    oracle_cursor.close()
    oracle_conn.close()
    sql_server_cursor.close()
    sql_server_conn.close()

# 初始加载
load_data()

# 定时任务
interval = 15 * 60  # 15分钟
while True:
    load_data()
    time.sleep(interval)
