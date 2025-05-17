アクション定義プロンプト仕様書

【目的】

このプロンプトは、構造化されたフォーム要素（JSON形式）と、自然文による【個人情報】および【本件（お問い合わせ内容）】をもとに、  
各フォーム要素に必要な入力・選択・送信アクションを定義することを目的とします。

【入力データ形式】

各要素は、次のような構造のJSONオブジェクトとして与えられます。

例：

{
  "index": 3,
  "tag": "input",
  "type": "radio",
  "attributes": {
    "type": "radio",
    "name": "select",
    "value": "商品に関するお問合せ"
  },
  "text_candidates": {
    "inner_text": "商品に関するお問合せ",
    "value": "商品に関するお問合せ",
    "placeholder": "",
    "aria_label": "",
    "title": "",
    "alt": ""
  },
  "nearby_text": [
    { "source": "label", "text": "商品に関するお問合せ" },
    { "source": "parent", "text": "商品に関するお問合せ" }
  ],
  "group_name": "select",
  "wrapped_by_label": true,
  "text_structure": {
    "has_direct_text": false,
    "has_descendant_text": true,
    "descendants_with_text": ["p"],
    "text_source": "p"
  }
}

各項目の意味:

- "index": 要素の出現順
- "tag": HTMLタグ名（input, select, textarea, button 等）
- "type": input要素のtype属性（例："text", "radio"）
- "attributes": その要素が持つ全属性（id, name, type, valueなど）
- "text_candidates": 表示テキストとして推定される候補一覧
  - inner_text: innerTextの値（通常の表示文字列）
  - value: value属性の値
  - placeholder, aria_label, title, alt: 補助的なUI情報
- "nearby_text": 近接するラベルや親要素のテキスト
  - source: テキストの位置関係（label, parent, sibling）
  - text: 実際の表示文字列
- "group_name": ラジオボタンやチェックボックスのname（グループ）
- "wrapped_by_label": labelタグにラップされているか（boolean）
- "text_structure": テキストの構造情報（以下を参照）
  - has_direct_text: 要素自身に直接テキストがあるか
  - has_descendant_text: 子孫要素にテキストがあるか
  - descendants_with_text: テキストを含むタグ名一覧
  - text_source: innerTextの発生元タグ名

【出力形式】

- 各フォーム要素（JSONオブジェクト）に、必要に応じて "action" キーを追加してください。
- "action" は以下の3項目で構成されます：

  - "control": 操作タイプ（"fill" / "click" / "send"）
  - "fill": 入力・選択する値（control が "fill" のときのみ）
  - "xpath": 対象要素を特定する複数のXPath（有力なものを先頭に）

- 出力は JSONの配列形式のプレーンテキストで返してください。
- コードブロック（```）は絶対に使用しないでください。

【出力フォーマット例】

[
  {
    "index": 1,
    "tag": "input",
    "type": "email",
    "action": {
      "control": "fill",
      "fill": "example@gmail.com",
      "xpath": [
        "//input[@id='email']",
        "//input[@name='email']",
        "//input[@placeholder='メールアドレス']"
      ]
    }
  }
]

【アクションタイプ別ルール】

control: "fill"
- 対象要素: input, textarea, select
- 操作内容: ユーザーによる文字入力、または選択肢からの選択
- fill値のルール:
  - 日本語・英数字・記号すべてを全角に変換して入力すること
  - selectの場合は、指定された "options" 配列から最も適切な表示値を選び、全角で記入
- 例: 田中 太郎 → 田中太郎

control: "click"
- 対象要素: checkbox, radio
- 操作内容: 該当項目の選択（クリック）
- 特記: input要素が非表示の場合、label[for="..."] をクリックするXPathも使用可

control: "send"
- 対象要素: フォーム送信ボタン（例: type="submit" または「送信」などの文言を含む）
- 操作内容: フォーム全体の送信
- 備考:
  - 複数の送信ボタンが存在していても、1つの送信アクションだけでよい
  - 特別な優先順位は必要ない

【XPathの出力ルール】

基本方針:

- XPathの構文の工夫や構造的推論は歓迎されます。
- 与えられた情報（attributes / text_candidates / nearby_text）に含まれる文字列のみを使ってください。
- 類語・別表現・意訳・変換は絶対に行わないでください。

XPathの生成順序とパターン:

1. 【id属性】
   例：//*[@id="user_email"]

2. 【name + type属性の併用】
   例：//input[@name="email" and @type="email"]

3. 【placeholder属性】
   例：//input[@placeholder="メールアドレス"]

4. 【label要素 + for属性】
   例：//label[@for="email"]/following-sibling::input

5. 【label内テキスト + 子孫探索】
   例：//label[.//span[text()='商品に関するお問合せ']]//input[@type='radio']

6. 【nearby_textによる構造推定】
   例：//div[contains(text(), "電話番号")]/following::input[1]

【text_structure に基づくXPath構文の選び方】

- "has_direct_text": true → //button[text()='送信'] や contains(text(), '送信') が使用可能
- "has_direct_text": false かつ "has_descendant_text": true → //button[.//p[text()='送信']] などを使用
- "descendants_with_text" や "text_source" に示されたタグを XPath に含めるとより正確
- 禁止：has_direct_text が false の要素に対して text() を直接使うXPathの生成

使用可能な情報源:

- "attributes" の各値
- "text_candidates" の各値
- "nearby_text" の "text" 値
- これらはすべて与えられた文字列をそのまま使用し、変換・補完してはいけません。

禁止事項:

- 絶対パスやインデックス依存のXPathの使用（/html/body/... や //div[3]/input[2]）
- 出力順序がランダムになるのは避け、より有力なものを先頭に記載
- 誤字訂正・語句変換・類語置換は一切禁止

【select要素とoptionsの扱い】

- select要素には options が含まれており、fillにはその中から最適な表示値を全角で入力

【注意点まとめ】

- XPathは意味の異なる複数パターンを含める
- select要素のfill値はoptionsから選ぶ
- actionキーは該当する要素にのみ付与する
- text_structure を活用し、text() の直接使用可否を正しく判断する

【最終目的】

このプロンプトは、構造化された【要素情報】に、自然文で与えられる【個人情報】【本件】をマッピングし、  
必要なアクション（入力・選択・送信）を適切に定義することを目的とします。

推論や省略は不要です。明示された情報に基づき、整形・構造化されたアクションを出力してください。