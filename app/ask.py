from app.chatgpt_setting import chatgpt_4omini, chatgpt_4o_image_model
from utilities.logger import logger
import json
import base64
import os
import re
from app.playwrite_setting import get_encoded_image


#feilds: basic_fields + selected_fields
def ask_for_feilds(elements, sender_info, sentence, prompt_paths):
    task_purpose = open_md_file(prompt_paths["task_purpose"])
    basic_fields_prompt = open_md_file(prompt_paths["basic_fields"])
    selected_fields_prompt = open_md_file(prompt_paths["selected_fields"])

    try:
        logger.info(f'>ask for select index')
        elements_json = json.dumps(elements)
        selected_index = ask_for_select_feilds(elements_json, selected_fields_prompt, task_purpose)
        if not selected_index:
            raise RuntimeError(f'Could not get select index')
        logger.info(f'>Got select index')
    except Exception as e:
        raise RuntimeError(f'{e}') from e
    
    try:
        selected_index_dict = convert_to_dict(selected_index)
    except Exception as e:
        raise RuntimeError(f'Could not convert to dict: {e}') from e
    logger.info(f'>Selected index:\n{json.dumps(selected_index_dict, indent=4, ensure_ascii=False)}')

    selected_fields_list = []
    for field in elements:
        if field["index"] in selected_index_dict["index"]:
            selected_fields_list.append(field)
    logger.info(f'>Got selected fields ({len(elements)} → {len(selected_fields_list)})')

    try:
        logger.info(f'>ask for basic feilds')
        selected_fields_json = json.dumps(selected_fields_list)
        final_feilds = ask_for_basic_feilds(selected_fields_json, sender_info, sentence, basic_fields_prompt, task_purpose)
        if not final_feilds:
            raise RuntimeError(f'Could not get final fields')
        logger.info(f'>Got final fields')
    except Exception as e:
        raise RuntimeError(f'{e}') from e
    
    try:
        final_feilds_dict = convert_to_dict(final_feilds)
    except Exception as e:
        raise RuntimeError(f'Could not convert to dict: {e}') from e
    logger.info(f'>Final fields:\n{json.dumps(final_feilds_dict, indent=4, ensure_ascii=False)}')
    
    logger.info(f'>🏠 Return to logic.py')
    return final_feilds_dict

def ask_for_basic_feilds(elements, sender_info, sentence, prompt, task_purpose):
    overall_prompt = f"""
{task_purpose}
---
{prompt}
---
## 個人情報
{sender_info}
---
## 本件
{sentence}
---
## 要素情報
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
---
{prompt}
---
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

#confirmation: 
def ask_for_confirmation(elements, prompt_paths):
    task_purpose = open_md_file(prompt_paths["task_purpose"])
    confirm_prompt = open_md_file(prompt_paths["confirm"])

    overall_prompt = f"""
{task_purpose}
---
{confirm_prompt}
---
## 要素情報
{elements}
"""

    try:
        logger.info(f'>ask for confirmation')
        indivisual_element = chatgpt_4omini(overall_prompt)
        if not indivisual_element:
            raise RuntimeError(f'Could not get responce')
        logger.info(f'>Got responce')
    except Exception as e:
        raise RuntimeError(f'{e}') from e
    
    indivisual_element_list = json.loads(indivisual_element)
    if not isinstance(indivisual_element_list, list):
        raise RuntimeError(f'Could not convert to list')
    logger.info(f'>Selected feild:\n{json.dumps(indivisual_element_list, indent=4, ensure_ascii=False)}')
    
    logger.info(f'>🏠 Return to logic.py')
    return indivisual_element_list

#progress: 
def ask_for_progress(page, prompt_paths):
    task_purpose = open_md_file(prompt_paths["task_purpose"])
    basic_prompt = open_md_file(prompt_paths["progress"])

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
{basic_prompt}
"""

    try:
        responce = chatgpt_4o_image_model(encoded_image, overall_prompt)
        if not responce:
            raise RuntimeError(f'Could not get responce')
        logger.info(f'>Got responce')
    except Exception as e:
        raise RuntimeError(f'{e}') from e

    if "true" in responce:
        logger.info(f'>Got "true"')
        logger.info(f'>🏠 Return to logic.py')
        return True
    elif "false" in responce:
        logger.info(f'>Got "false"')
        logger.info(f'>🏠 Return to logic.py')
        return False
    else:
        raise RuntimeError(f'Could not convert responce to boolean')

#overall
def open_md_file(path):
    with open(path, 'r') as file:
        return file.read()
    
def convert_to_dict(responce):
    remove_codeblock = re.sub(r'```.*?```', '', responce, flags=re.DOTALL)
    return json.loads(remove_codeblock)