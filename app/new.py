import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
from playwright.sync_api import sync_playwright
from app.chatgpt_setting import chatgpt_4omini

def open_browser(url, p):
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(url, wait_until="load")
    return browser, page

def extract_form_elements(page):
    elements = page.evaluate("""
    () => {
        const fields = [];
        const targets = document.querySelectorAll('input, select, textarea, button, a[role="button"], div[role="button"]');

        targets.forEach((el, index) => {
            const tag = el.tagName.toLowerCase();
            const type = el.getAttribute("type")?.toLowerCase() || "";
            const role = el.getAttribute("role") || "";
            const value = el.getAttribute("value") || "";
            const text = el.innerText?.trim() || value;
            const visible = !!(el.offsetParent !== null);  // 非表示除外

            // MECEな抽出条件
            const isInputFillable = tag === "input" && !["hidden", "submit", "reset", "button"].includes(type);
            const isButtonLikeInput = tag === "input" && ["submit", "button"].includes(type);
            const isSemanticButton = tag === "button";
            const isTextArea = tag === "textarea";
            const isSelect = tag === "select";
            const isRoleButton = (tag === "div" || tag === "a") && role === "button";

            const isTarget =
                visible && (
                    isInputFillable ||
                    isTextArea ||
                    isSelect ||
                    isButtonLikeInput ||
                    isSemanticButton ||
                    isRoleButton
                );

            if (!isTarget) return;

            const attrs = {};
            for (const attr of el.attributes) {
                attrs[attr.name] = attr.value;
            }

            const nearby = [];

            const id = el.getAttribute("id");
            if (id) {
                const label = document.querySelector(`label[for="${id}"]`);
                if (label) nearby.push(label.innerText.trim());
            }

            let parent = el.parentElement;
            let depth = 0;
            while (parent && depth < 2) {
                const txt = parent.innerText.trim();
                if (txt.length > 0) nearby.push(txt);
                parent = parent.parentElement;
                depth++;
            }

            const prev = el.previousElementSibling;
            if (prev && prev.innerText) {
                nearby.push(prev.innerText.trim());
            }

            const options = isSelect
                ? Array.from(el.options)
                    .map(opt => opt.label || opt.innerText || "")
                    .filter(txt => txt && txt.trim().length > 0)
                : undefined;

            fields.push({
                index,
                tag,
                type,
                text,
                attributes: attrs,
                nearby_text: [...new Set(nearby)].filter(t => t),
                ...(options ? { options } : {})
            });
        });

        return fields;
    }
    """)

    return elements

def fillout_prompt(user_info, sentence, elements_json):
    basic_prompt = """
あなたはブラウザ操作エージェントです。

1. タスク
【要素情報】に基づいて、問い合わせフォームに【個人情報】を入力し、確実に送信すること。
【個人情報】とは別に【本件】は「問い合わせ内容」やそれに類似した項目に入力すること。
以下の情報をもとに、指定されたタスクを正確に実行するためのアクションリストを生成してください。


2. 出力ルール
・各【要素情報】を1つずつ精査し、操作が必要な項目には "action" キーを追加してください。
・各要素について、以下のJSON形式で出力してください。
・コードブロック（```json）などは付けず、プレーンテキストで返してください。

各 "action" オブジェクトには以下の3項目を含めます：
    ・"fill"：入力や選択を伴う要素（input, text, textarea, selectなど）
    ・"click"：checkbox, radio, その他クリック操作
    ・"send"：送信ボタン（フォーム送信を行う唯一のボタン）

fill (control: "fill" のときのみ) の設定基準:
・記入または選択する値（例：氏名、メールアドレスなど）
・基本的に全て全角で入力する。
・type = "select" の場合、おそらく "option" の値から選択する。

xpath の設定基準:
>【要素情報】の中で、以下を参考に、最も一意に要素を特定できるXPathを出力してください
・tag（例: input, button など）
・attributes（例: id, name, type, placeholder など）
・nearby_text（例: ラベルや見出しのテキスト）

> 優先ルールとパターン
1. id がある → //*[@id="user_email"]
2. name + type → //input[@name="email" and @type="email"]
3. placeholder → //input[@placeholder="メールアドレス"]
4. label[for=id] が存在する → //label[text()="お名前"]/following-sibling::input
5. nearby_text を含むテキストノードから → //div[contains(text(), "電話番号")]/following::input[1]

> checkbox や 非表示の input（特に submit / checkbox / radio）について
・対象の input 要素が非表示などでクリックできない場合、label[for=...] に対応する要素が nearby_text に含まれていれば、代わりに label をクリックするXPathを生成しても構いません。
・例：<input type="checkbox" id="agree" style="display:none"> → //label[@for="agree"]

> XPath構文の活用
・部分一致には contains() を使う：
//input[contains(@placeholder, "住所")]
//button[contains(text(), "送信")]
・ancestor::, following-sibling::, label[text()] なども活用可能

> xpath出力形式
・xpathは **リスト形式** で返してください（例：["xpath1", "xpath2", ...]）
・最も有力だと思われるXPathをリストの **最初に置いてください**
・リスト内には **意味の異なる複数パターン**（例：id指定・placeholder指定・nearby指定など）をできるだけ含めてください

> 避けるべきXPath
・/html/body/... のような絶対パス
・位置依存のみの指定（例：//div[4]/input[2]）

フォーマット例：
[
  {
    "index": 1, #---既存の項目・何も変更は加えなくて良い---
    "tag": "input",
    "type": "email",
    "text": "",
    "attributes": {
      "id": "email",
      "name": "user_email",
      "placeholder": "メールアドレス"
    },
    "nearby_text": ["メールアドレス", "ご連絡先"], 
    "options": [
        "選択してください",
        "お問い合わせ",
        "ご意見ご要望",
        "その他"
    ], #---既存の項目・何も変更は加えなくて良い---
    "action": {
      "control": "fill",
      "fill": "yamada.taro@example.com",
      "xpath": ["//input[@id='email']", "//input[@name='email']"...]
    }
  },
  ...
]
"""

    overall_prompt = f"""
{basic_prompt}

3. 個人情報
{user_info}

4. 本件
{sentence}

5. 要素情報
{elements_json}
"""
    
    return overall_prompt

def select_prompt(fields):
    basic_prompt = """
あなたはリストマーケティングにおける、フォーム自動送信エージェントです。

タスク
以下にフォームを構成する要素とアクション（xpathや入力値）が含まれたfeildsが渡されます。
そこからフォーム送信に必要な要素のみ選択し、index番号を出力してください。

出力ルール
・各要素について、以下のJSON形式で出力してください。
・コードブロック（```json）などは付けず、プレーンテキストで返してください。

フォーマット例：
{
    "index": [0, 1, 3, 4 ...]
}

注意
・基本的にフォームで指定されている項目は全て含める
・同意のチェックボックスや送信のボタンなど必ず含める
・選択型のラジオやチェックボックスなどに関して、nameが同じものは1つのグループとしてみて、そのなかから選択肢が当てはまるもののみ含める。

・フォームの項目とは異なる項目は含めない
・アクションが埋まっていないものは含めない
・フォームのリセットや戻るなど必要のないものは含めない
    """

    overall_prompt = f"""
{basic_prompt}

feilds
{fields}
"""

    return overall_prompt

def select_feilds(fields_dict, index_dict):
    selected_fields = []
    for field in fields_dict:
        if field["index"] in index_dict["index"]:
            selected_fields.append(field)

    return selected_fields

def control_browser(url, fields, browser, page, time_sleep=2):
    fill_list = []
    click_list = []
    send_list = []

    for field in fields:
        control = field.get("action", {}).get("control")
        if control == "fill":
            fill_list.append(field)
        elif control == "click":
            click_list.append(field)
        elif control == "send":
            send_list.append(field)

    print(f'fill_list: {len(fill_list)}')
    print(f'click_list: {len(click_list)}')
    print(f'send_list: {len(send_list)}')

    def get_locator(xpath):
        locator = page.locator(f"xpath={xpath}")
        if locator.count() == 0:
            return False
        if not locator.is_visible():
            return False
        
        locator.scroll_into_view_if_needed()
        locator.wait_for(state="attached", timeout=500)
        return locator

    for fill in fill_list:
        value = fill["action"]["fill"]
        xpath_list = fill["action"]["xpath"]
        tag = fill["tag"]

        for xpath in xpath_list:
            try:
                locator = get_locator(xpath)
                if locator == False:
                    print(f' - fill: {xpath} - {value} : not found')
                    continue
                
                if tag == "select":
                    locator.select_option(value)
                else:
                    locator.type(value)
                    locator.evaluate("e => e.blur()")

                print(f' - fill: {xpath} - {value}')
                time.sleep(time_sleep)
                break

            except Exception:
                print(f' - fill: {xpath} - {value} : not found')
                continue

    for click in click_list:
        xpath_list = click["action"]["xpath"]

        for xpath in xpath_list:
            try:
                locator = get_locator(xpath)
                if locator == False:
                    print(f' - click: {xpath} : not found')
                    continue

                locator.click()

                print(f' - click: {xpath}')
                time.sleep(time_sleep)
                break
            
            except Exception:
                print(f' - click: {xpath} : not found')
                continue

    time.sleep(5)

    for send in send_list:
        xpath_list = send["action"]["xpath"]

        for xpath in xpath_list:
            try:
                locator = get_locator(xpath)
                if locator == False:
                    print(f' - send: {xpath} : not found')
                    continue

                locator.click()

                print(f' - send: {xpath}')
                time.sleep(time_sleep)
                break

            except Exception:
                print(f' - send: {xpath} : not found')
                continue

    return True


if __name__ == "__main__":
    url = "https://www.nobuta123.co.jp/contact"
    screenshot_path = "'/Users/shinnosuke/Desktop/業務/Samurai marketing/開発/new_file_format/selenium_formsend_V1/clients/client_test/screenshots'"

    user_info = """
会社名：サンプル株式会社
氏名：山田太郎
フリガナ：ヤマダタロウ
郵便番号：146-0085
住所（都道府県）：東京都
住所（市区町村）：大田区久が原
住所（番地・建物名）：3丁目12-8 久が原ハイツ203
電話番号：03-3456-7890
メールアドレス：yamada.taro@example.com
性別：男性
生年月日：1985年4月10日
職業：会社員
"""

    sentence = """
始めました、新之介です。
"""
    
    with sync_playwright() as p:
        browser, page = open_browser(url, p)
        elements = extract_form_elements(page)
        elements_json = json.dumps(elements, indent=4, ensure_ascii=False).encode('utf-8').decode('utf-8')
        
        prompt = fillout_prompt(user_info, sentence, elements_json)
        fields = chatgpt_4omini(prompt)
        fields_dict = json.loads(fields)
        print(json.dumps(fields_dict, indent=4, ensure_ascii=False))

        prompt = select_prompt(fields_dict)
        index_json = chatgpt_4omini(prompt)
        index_dict = json.loads(index_json)
        print(json.dumps(index_dict, indent=4, ensure_ascii=False))

        selected_fields = select_feilds(fields_dict, index_dict)
        print(json.dumps(selected_fields, indent=4, ensure_ascii=False))

        status = control_browser(url, selected_fields, browser, page)
        if status == True:
            print("フォーム送信成功")
        else:
            print("フォーム送信失敗")

        input("Enterを押して終了")
        browser.close()
