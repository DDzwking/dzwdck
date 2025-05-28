from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/receive', methods=['POST'])
def receive_message():
    """
    接收各种类型的 POST 请求数据（JSON、form-data、x-www-form-urlencoded、raw text 等）
    """
    content_type = request.headers.get('Content-Type')

    print("Received Content-Type:", content_type)

    if 'application/json' in content_type:
        data = request.get_json(silent=True)
        print("Received JSON Data:", data)
        return jsonify({
            "status": "success",
            "type": "json",
            "received_data": data
        }), 200

    elif 'application/x-www-form-urlencoded' in content_type:
        data = request.form.to_dict()
        print("Received Form Data:", data)
        return jsonify({
            "status": "success",
            "type": "form",
            "received_data": data
        }), 200

    elif 'multipart/form-data' in content_type:
        data = request.form.to_dict()
        files = {key: value.filename for key, value in request.files.to_dict().items()}
        print("Received FormData (Fields):", data)
        print("Received FormData (Files):", files)
        return jsonify({
            "status": "success",
            "type": "multipart",
            "received_fields": data,
            "received_files": files
        }), 200

    elif 'text/plain' in content_type:
        data = request.data.decode('utf-8')
        print("Received Plain Text:", data)
        return jsonify({
            "status": "success",
            "type": "text",
            "received_data": data
        }), 200

    else:
        data = request.data.decode('utf-8')
        print("Received Unknown Type Data:", data)
        return jsonify({
            "status": "success",
            "type": "unknown",
            "received_data": data
        }), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5666)
