from app.chatgpt_setting import chatgpt_4omini, chatgpt_4o_image_model
from utilities.logger import logger
import json
import base64
import os
import re
from app.playwrite_setting import get_encoded_image


#feilds: basic_fields + selected_fields
def ask_for_feilds(elements, sender_info, sentence):
    task_purpose = open_md_file("prompt/task_purpose.md")
    action_fields_prompt = open_md_file("prompt/action_fields.md")
    xpath_fields_prompt = open_md_file("prompt/xpath_fields.md")
    selected_fields_prompt = open_md_file("prompt/selected_fields.md")


    #selected_index: get index number
    try:
        logger.info(f'>ask for select index')
        elements_json = json.dumps(elements, indent=4, ensure_ascii=False)
        selected_index = ask_for_select_feilds(elements_json, selected_fields_prompt, task_purpose)
        if not selected_index:
            raise RuntimeError(f'Could not get select index')
        logger.info(f'>Got select index')
        selected_index_dict = convert_to_dict(selected_index)
        if not selected_index_dict:
            raise RuntimeError(f'Could not convert to dict')
        logger.info(f'>converted to dict')
    except Exception as e:
        raise RuntimeError(f'{e}') from e
    
    selected_fields_list = []
    for field in elements:
        if field["index"] in selected_index_dict["index"]:
            selected_fields_list.append(field)
    logger.info(f'>Got selected fields ({len(elements)} → {len(selected_fields_list)})')


    logger.info(f'>selected fields:\n{json.dumps(selected_fields_list, indent=4, ensure_ascii=False)}')


    #action feilds: get action {value}
    try:
        logger.info(f'>ask for action feilds')
        selected_fields_json = json.dumps(selected_fields_list, indent=4, ensure_ascii=False)
        action_feilds_json = ask_for_action_feilds(
            selected_fields_json,
            sender_info, sentence,
            action_fields_prompt, task_purpose
        )
        if not action_feilds_json:
            raise RuntimeError(f'Could not get action fields')
        logger.info(f'>Got action fields')
        action_feilds_dict = convert_to_dict(action_feilds_json)
        if not action_feilds_dict:
            raise RuntimeError(f'Could not convert to dict')
        logger.info(f'>converted to dict')
    except Exception as e:
        raise RuntimeError(f'{e}') from e
    

    logger.info(f'>action:\n{json.dumps(action_feilds_dict, indent=4, ensure_ascii=False)}')
    

    #xpath feilds: get action {xpath}
    try:
        logger.info(f'>ask for xpath feilds')
        selected_fields_json = json.dumps(selected_fields_list, indent=4, ensure_ascii=False)
        xpath_feilds_json = ask_for_xpath_feilds(
            selected_fields_json, 
            xpath_fields_prompt, task_purpose
        )
        if not xpath_feilds_json:
            raise RuntimeError(f'Could not get xpath fields')
        logger.info(f'>Got xpath fields')
        xpath_feilds_dict = convert_to_dict(xpath_feilds_json)
        if not xpath_feilds_dict:
            raise RuntimeError(f'Could not convert to dict')
        logger.info(f'>converted to dict')
    except Exception as e:
        raise RuntimeError(f'{e}') from e
    

    logger.info(f'>xpath:\n{json.dumps(xpath_feilds_dict, indent=4, ensure_ascii=False)}')
    

    try:
        final_feilds_dict = merge_fields(action_feilds_dict, xpath_feilds_dict, selected_fields_list)
    except Exception as e:
        raise RuntimeError(f'{e}') from e
    

    logger.info(f'>final:\n{json.dumps(final_feilds_dict, indent=4, ensure_ascii=False)}')

    
    logger.info(f'>🏠 Return to logic.py')
    return final_feilds_dict

def ask_for_action_feilds(elements, sender_info, sentence, prompt, task_purpose):
    overall_prompt = f"""
{task_purpose}
{prompt}

## フォーム情報
{elements}

## 個人情報
{sender_info}

## お問い合わせ内容および本件
{sentence}
"""
    logger.info(f' - Make prompt')

    try:
        responce = chatgpt_4omini(overall_prompt)
        if not responce:
            raise RuntimeError(f'Could not get responce')
        logger.info(f' - Got responce')
    except Exception as e:
        raise RuntimeError(f'{e}') from e
    
    logger.info(f' - Return to main function')
    return responce

def ask_for_xpath_feilds(elements, prompt, task_purpose):
    overall_prompt = f"""
{task_purpose}
{prompt}

## フォーム情報
{elements}
"""
    logger.info(f' - Make prompt')

    try:
        responce = chatgpt_4omini(overall_prompt)
        if not responce:
            raise RuntimeError(f'Could not get responce')
        logger.info(f' - Got responce')
    except Exception as e:
        raise RuntimeError(f'{e}') from e
    
    logger.info(f' - Return to main function')
    return responce

def ask_for_select_feilds(feilds, prompt, task_purpose):
    overall_prompt = f"""
{task_purpose}
{prompt}

### フィールド
{feilds}
"""
    logger.info(f' - Make prompt')

    try:
        responce = chatgpt_4omini(overall_prompt)
        if not responce:
            raise RuntimeError(f'Could not get responce')
        logger.info(f' - Got responce')
    except Exception as e:
        raise RuntimeError(f'{e}') from e
    
    logger.info(f' - Return to main function')
    return responce

def merge_fields(action_feilds, xpath_feilds, selected_fields):
    for action_feild in action_feilds:
        for xpath_feild in xpath_feilds:
            for field in selected_fields:
                if action_feild["index"] == xpath_feild["index"] == field["index"]:
                    xpath_action_xpath = xpath_feild["action"]["xpath"]
                    feild_action_control = action_feild["action"]["control"]
                    feild_action_fill = action_feild["action"]["fill"]
                    merged_actions = {
                        "xpath": xpath_action_xpath,
                        "control": feild_action_control,
                        "fill": feild_action_fill,
                    }
                    field["action"] = merged_actions

    return selected_fields


#confirmation: 
def ask_for_confirmation(elements):
    task_purpose = open_md_file("prompt/task_purpose.md")
    confirm_selected_fields_prompt = open_md_file("prompt/confirm_selected_fields.md")
    xpath_fields_prompt = open_md_file("prompt/xpath_fields.md")


    #selected_index: get index number
    try:
        logger.info(f'>ask for select index')
        elements_json = json.dumps(elements, indent=4, ensure_ascii=False)
        selected_index = ask_for_confirm_select_feilds(
            elements_json, 
            confirm_selected_fields_prompt, task_purpose
        )
        if not selected_index:
            raise RuntimeError(f'Could not get select index')
        logger.info(f'>Got select index')
        selected_index_dict = convert_to_dict(selected_index)
        if not selected_index_dict:
            raise RuntimeError(f'Could not convert to dict')
        logger.info(f'>converted to dict')
    except Exception as e:
        raise RuntimeError(f'{e}') from e
    
    selected_fields_list = []
    for field in elements:
        if field["index"] in selected_index_dict["index"]:
            selected_fields_list.append(field)
    logger.info(f'>Got selected fields ({len(elements)} → {len(selected_fields_list)})')


    logger.info(f'>selected fields:\n{json.dumps(selected_fields_list, indent=4, ensure_ascii=False)}')
    

    #xpath feilds: get action {xpath}
    try:
        logger.info(f'>ask for xpath feilds')
        selected_fields_json = json.dumps(selected_fields_list, indent=4, ensure_ascii=False)
        xpath_feilds_json = ask_for_xpath_feilds(
            selected_fields_json, 
            xpath_fields_prompt, task_purpose
        )
        if not xpath_feilds_json:
            raise RuntimeError(f'Could not get xpath fields')
        logger.info(f'>Got xpath fields')
        xpath_feilds_dict = convert_to_dict(xpath_feilds_json)
        if not xpath_feilds_dict:
            raise RuntimeError(f'Could not convert to dict')
        logger.info(f'>converted to dict')
    except Exception as e:
        raise RuntimeError(f'{e}') from e
    

    logger.info(f'>xpath:\n{json.dumps(xpath_feilds_dict, indent=4, ensure_ascii=False)}')

    
    logger.info(f'>🏠 Return to logic.py')
    return xpath_feilds_dict

def ask_for_confirm_select_feilds(elements, prompt, task_purpose):
    overall_prompt = f"""
{task_purpose}
{prompt}

## フォーム情報
{elements}
"""
    logger.info(f' - Make prompt')

    try:
        responce = chatgpt_4omini(overall_prompt)
        if not responce:
            raise RuntimeError(f'Could not get responce')
        logger.info(f' - Got responce')
    except Exception as e:
        raise RuntimeError(f'{e}') from e
    
    logger.info(f' - Return to main function')
    return responce


#progress: 
def ask_for_progress(page):
    task_purpose = open_md_file("prompt/task_purpose.md")
    progress_prompt = open_md_file("prompt/progress.md")

    try:
        page.wait_for_load_state("networkidle") 
        encoded_image = get_encoded_image(page)
        if not encoded_image:
            raise RuntimeError(f'Could not get encoded image')
        logger.info(f'>Got encoded image')
    except Exception as e:
        raise RuntimeError(f'{e}') from e

    overall_prompt = f"""
{task_purpose}
---
{progress_prompt}
"""

    try:
        responce = chatgpt_4o_image_model(encoded_image, overall_prompt)
        if not responce:
            raise RuntimeError(f'Could not get responce')
        logger.info(f'>Got responce')
    except Exception as e:
        raise RuntimeError(f'{e}') from e

    try:
        status, message = seperate_responce_for_progress(responce)
        if status == True or status == False:
            logger.info(f'>Seperated responce') 
        else:
            raise RuntimeError(f'Could not seperate responce')
    except Exception as e:
        raise RuntimeError(f'{e}') from e

    logger.info(f'>🏠 Return to logic.py')
    return status, message

def seperate_responce_for_progress(responce):
    responce_dict = json.loads(responce)

    status = responce_dict["status"]
    if "true" in status:
        logger.info(f' - Got "true" for status')
        status_bool = True
    elif "false" in status:
        logger.info(f' - Got "false" for status')
        status_bool = False
    else:
        raise RuntimeError(f'Could not convert responce to boolean')
    
    message = responce_dict["message"]

    return status_bool, message


#overall
def open_md_file(path):
    with open(path, 'r') as file:
        return file.read()
    
def convert_to_dict(responce):
    remove_codeblock = re.sub(r'```.*?```', '', responce, flags=re.DOTALL)
    return json.loads(remove_codeblock)