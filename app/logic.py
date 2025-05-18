import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import json
from playwright.sync_api import sync_playwright
from app.element import get_form_elements, get_confirm_elements
from app.ask import ask_for_feilds, ask_for_confirmation, ask_for_progress
from app.control import control_browser
from utilities.google_spreadsheet import *
from utilities.logger import logger

prompt_paths = {
    "task_purpose": "prompt/task_purpose.md",
    "basic_fields": "prompt/basic_fields.md",
    "selected_fields": "prompt/selected_fields.md",
    "confirm": "prompt/confirm.md",
    "progress": "prompt/progress.md",
}

def run_flow(start_row, end_row, spreadsheet, sender_info):
    sheet_id = spreadsheet["sheet_id"]
    sheet = spreadsheet["sheet"]
    column_map = spreadsheet["column_map"]
    credentials_path = spreadsheet["credentials_path"]

    try:
        sheet = certification_google_spreadsheet(sheet_id, sheet, credentials_path)
        if sheet:
            logger.info(f'🟢 Successfully to get google certification')
        else:
            raise RuntimeError(f'🔴 failed to get google certification')
    except Exception as e:
        raise RuntimeError(f'🔴 failed to get google certification: {e}') from e

    try:
        multi_data = input_google_spreadsheet_multi(sheet, column_map, start_row, end_row)
        if multi_data:
            logger.info(f'🟢 Successfully to get multi data')
        else:
            raise RuntimeError(f'🔴 failed to get multi data')
    except Exception as e:
        raise RuntimeError(f'🔴 failed to get multi data: {e}') from e

    row = start_row
    error_count = 0
    system_status = None

    for data in multi_data:
        if error_count:
            if error_count > 100:
                raise RuntimeError(f'🔴 #{row}: got failed multi times')
            try:
                output_status = {}
                output_status["system_status"] = system_status
                temp_status = output_google_spreadsheet(sheet, column_map, row, output_status)
                if temp_status == True:
                    logger.info(f'🟢 Successfully to output google spreadsheet')
                else:
                    raise RuntimeError(f'🔴 failed to output google spreadsheet')
            except Exception as e:
                raise RuntimeError(f'🔴 failed to output google spreadsheet: {e}') from e
            row += 1

        logger.info(f"==starting for #{row}===")
        logger.info(f"（error_count: {error_count}）")

        data_url = data["basic_url"]
        data_sentence = data["basic_sentence"]
        data_status = data["system_status"]

        if not data_url:
            logger.warning(f"🟡 No URL")
            row += 1
            continue
            
        if not data_sentence:
            logger.warning(f"🟡 No sentence")
            row += 1
            continue

        if data_status == 'completed':
            logger.warning(f"🟡 Already completed")
            row += 1
            continue

        try:
            system_status = basic_flow(
                data_url,
                data_sentence,
                sender_info,
            )
        except Exception as e:
            error_count += 1
            error_message = f'{e}'
            logger.error(f'🔴 {error_message}')
            continue

        try:
            output_status = {}
            output_status["system_status"] = system_status
            temp_status = output_google_spreadsheet(sheet, column_map, row, output_status)
            if temp_status == True:
                logger.info(f'🟢 Successfully to output google spreadsheet')
            else:
                raise RuntimeError(f'🔴 failed to output google spreadsheet')
        except Exception as e:
            raise RuntimeError(f'🔴 failed to output google spreadsheet: {e}') from e

        logger.info(f"==ending for #{row}===")
        error_count = 0
        row += 1

def basic_flow(
        data_url, #from spreadsheet
        data_sentence, 
        sender_info, #from client
        prompt_paths=prompt_paths,
    ):
        
        url = data_url
        sentence = data_sentence

        with sync_playwright() as p:
            logger.info(f"🔄 1. Get form elements")
            try:
                elements, browser, page = get_form_elements(url, p)
                if not elements:
                    raise RuntimeError(f'1. get form elements')
                logger.info(f'🟢Successfully got elements from url\n')
            except Exception as e:
                raise RuntimeError(f'1. get form elements: {e}') from e
            
            logger.info(f'elements:\n{json.dumps(elements, indent=4, ensure_ascii=False)}')
            
            logger.info(f"🔄 2. Ask for fields")
            try:
                fields = ask_for_feilds(elements, sender_info, sentence, prompt_paths)
                if not fields:
                    raise RuntimeError(f'2. ask for fields')
                logger.info(f'🟢 Successfully got fields\n')
            except Exception as e:
                raise RuntimeError(f'2. ask for fields: {e}') from e
            
            logger.info(f"🔄 3. Control browser")
            try:
                status = None
                status = control_browser(page, fields, form_check=True)
                if status == True:
                    logger.info(f'🟢 Successfully controlled browser\n')
                else:
                    raise RuntimeError(f'3. control browser')
            except Exception as e:
                raise RuntimeError(f'3. control browser: {e}') from e
            
            for i in range(1, 4):
                logger.info(f"🔄 4.1 Check the progress ({i})")
                time.sleep(5)
                try:        
                    status, message = None
                    status, message = ask_for_progress(page, prompt_paths)
                    if status == True:
                        logger.info(f'🟢 Successfully checked the progress : True ({i})\n')
                    elif status == False:
                        logger.info(f'🟢 Successfully checked the progress : False ({i}) : {message}\n')
                    else:
                        raise RuntimeError(f'4.1 check the progress ({i})')
                except Exception as e:
                    raise RuntimeError(f'4.1 check the progress ({i}): {e}') from e
                
                if status == True:
                    break
                if i == 3:
                    break
                
                logger.info(f"🔄 4.2 Get confirm elements ({i})")
                try:
                    elements = get_confirm_elements(page)
                    if not elements:
                        raise RuntimeError(f'4.2 get confirm elements ({i})')
                    logger.info(f'🟢 Successfully got elements ({i})\n')
                except Exception as e:
                    raise RuntimeError(f'4.2 get confirm elements ({i}): {e}') from e
                
                logger.info(f"🔄 4.3 Ask for confirmation ({i})")
                try:
                    feild = ask_for_confirmation(elements, prompt_paths)
                    if not feild:
                        raise RuntimeError(f'4.3 ask for confirmation ({i})')
                    logger.info(f'🟢 Successfully asked for confirmation ({i})\n')
                except Exception as e:
                    raise RuntimeError(f'4.3 ask for confirmation ({i}): {e}') from e
            
                logger.info(f"🔄 4.4 Control browser ({i})")
                try:
                    status = None
                    status = control_browser(page, feild, form_check=False)
                    if status == True:
                        logger.info(f'🟢 Successfully controlled browser ({i})\n')
                    else:
                        raise RuntimeError(f'4.4 control browser ({i})')
                except Exception as e:
                    raise RuntimeError(f'4.4 control browser ({i}): {e}') from e
                
                logger.info(f'🟡 Continuing to check the progress ({i} → {i+1})\n')

        if status == False:
            logger.info(f"💣 99. Failed 💣")
            raise RuntimeError(f'99. Could not send form : {message}')
        elif status == True:
            logger.info(f"🦄 99. Completed 🦄")
            return True

if __name__ == "__main__":
    sender_info = """
会社名：サムライスタイル株式会社
氏名：那知上　真之介
フリガナ：ナチガミ　シンノスケ
郵便番号：150-0043
住所（都道府県）：東京都
住所（市区町村）：渋谷区道玄坂
住所（番地・建物名）：1-10-8 渋谷道玄坂東急ビル2F
電話番号：090-5589-8442
メールアドレス：sean@samurai-style.tokyo
性別：男性
生年月日：２００７年２月１５日
部署：マーケティング
職業：会社員
本題：新規リード獲得に関するお問い合わせ
 """
    sentence = """
マーケティング戦略立案担当者様へ

貴社のホームページを拝見し、プライズ事業やカプセルトイ事業などにおいて、Web広告に注力されており、
弊社で展開しているリストマーケティング『LeadMaker』でお力添えできるのではないかと思い、連絡させていただきました。

弊社は代表の橋本の事業会社およびマーケティング支援会社双方の経験を踏まえ、
事業理解に基づく顧客リスト・アプローチ文の作成、アプローチの実行までを軸にBtoBマーケティングを支援しております。
まだサービスリリース直後の状況のため、まずは1,000件分のリスト作成からアプローチの実行までを無料で実施いたしますので、
ご興味をお持ちいただけましたら、ぜひお声がけいただけると幸いです。
https://samurai-style.tokyo/

また、ぬいぐるみの企画・開発の領域を扱われていることからリード獲得後の成約までの期間が一定あるかと存じますが、
弊社では、リード獲得後の営業資料作成やスコアリングなど、リード獲得後のフォローフローの整備もご支援可能です。
詳細は上記URLよりご覧ください。
 """

    basic_flow(
        data_url = input("Enter the URL: "),
        data_sentence = sentence,
        sender_info = sender_info,
    )