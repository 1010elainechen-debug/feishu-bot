import os
from flask import Flask, request, jsonify
import requests
import anthropic
import json

FEISHU_APP_ID = "cli_a943592b2a799bc0"
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
BITABLE_APP_TOKEN = "IX9bbJgHvaQivvsWNEJcOzt8n53"
BITABLE_TABLE_ID = "tblfIkLpgsadLS1D"

app = Flask(__name__)

def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    res = requests.post(url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET})
    return res.json().get("tenant_access_token")

def send_feishu_message(chat_id, text):
    token = get_feishu_token()
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    requests.post(url, headers={"Authorization": f"Bearer {token}"}, json={
        "receive_id": chat_id,
        "msg_type": "text",
        "content": f'{{"text": "{text}"}}'
    })

def write_to_bitable(data):
    token = get_feishu_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{BITABLE_TABLE_ID}/records"
    res = requests.post(url, headers={"Authorization": f"Bearer {token}"}, json={"fields": data})
    return res.json()

def parse_with_claude(text):
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"""从下面这段文字中提取信息，以JSON格式返回，字段包括：
客户返利、客户名称、年框返利、下单日期、客户联系人、实际客户名称、刊例价(元)、含税金额(元)、收入类型、账号、ID、下单平台、下单形式、品牌名称、发布链接、销售、执行人（商务侧）。
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
            result_str = parse_with_claude(text)
            result = json.loads(result_str)
            fields = {k: v for k, v in result.items() if v is not None}
            write_to_bitable(fields)
            send_feishu_message(chat_id, "已记录到表格 ✓")
    except Exception as e:
        print(f"错误：{e}")
    return jsonify({"code": 0})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
