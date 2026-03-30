import os
from flask import Flask, request, jsonify
import requests
import anthropic
import json

FEISHU_APP_ID = "cli_a943592b2a799bc0"
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")

app = Flask(__name__)

def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    res = requests.post(url, json={
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    })
    return res.json().get("tenant_access_token")

def send_feishu_message(chat_id, text):
    token = get_feishu_token()
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    requests.post(url, headers={"Authorization": f"Bearer {token}"}, json={
        "receive_id": chat_id,
        "msg_type": "text",
        "content": f'{{"text": "{text}"}}'
    })

def parse_with_claude(text):
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"""从下面这段文字中提取数据记录信息，以JSON格式返回，字段包括：
客户姓名、电话、商品名称、数量、金额、备注。
如果某字段没有信息则填null。只返回JSON，不要其他内容。

文字内容：{text}"""
        }]
    )
    return message.content[0].text

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data.get("challenge")})
    try:
        event = data.get("event", {})
        msg = event.get("message", {})
        chat_id = msg.get("chat_id")
        content = msg.get("content", "{}")
        text = json.loads(content).get("text", "")
        if text:
            result = parse_with_claude(text)
            send_feishu_message(chat_id, f"已记录\n{result}")
    except Exception as e:
        print(f"错误：{e}")
    return jsonify({"code": 0})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
