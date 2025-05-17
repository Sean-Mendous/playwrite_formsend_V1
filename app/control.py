import time
from utilities.logger import logger

def split_fields(fields):
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

    return fill_list, click_list, send_list

def control_browser(page, fields, time_sleep=2, form_check=True):
    page.set_default_timeout(10000)

    fill_list, click_list, send_list = split_fields(fields)
    logger.info(f'\nfill_list: {len(fill_list)}\nclick_list: {len(click_list)}\nsend_list: {len(send_list)}')

    if form_check:
        if not fill_list:
            raise RuntimeError(f'No fill to control')
        # if not click_list:
        #     raise RuntimeError(f'No click to control')
        if not send_list:
            raise RuntimeError(f'No send to control')

    try:
        fill_count = for_fill(page, fill_list, time_sleep)
    except Exception as e:
        raise RuntimeError(f'>Error: In fill: {e}') from e

    try:
        click_count = for_click(page, click_list, time_sleep)
    except Exception as e:
        raise RuntimeError(f'>Error: In click: {e}') from e

    try:
        send_count = for_send(page, send_list, time_sleep)
    except Exception as e:
        raise RuntimeError(f'>Error: In send: {e}') from e
    
    if fill_list and not fill_count:
        raise RuntimeError(f'>Did not fill any fields')
    if click_list and not click_count:
        raise RuntimeError(f'>Did not click any fields')
    if send_list and not send_count:
        raise RuntimeError(f'>Did not send any fields')

    return True

def for_fill(page, fill_list, time_sleep):
    count = 0
    for fill in fill_list:
        value = fill["action"]["fill"]
        xpath_list = fill["action"]["xpath"]
        tag = fill["tag"]

        for xpath in xpath_list:
            try:
                locator = get_locator(xpath, page)
                if locator == False:
                    logger.error(f' - Not found(fill): {xpath} - {value}')
                    continue
                
                if tag == "select":
                    locator.select_option(value)
                else:
                    locator.type(value)
                    locator.evaluate("e => e.blur()")

                count += 1
                logger.info(f' - Success(fill): {xpath} - {value}')
                time.sleep(time_sleep)
                break

            except Exception:
                logger.error(f' - Not found(fill): {xpath} - {value}')
                continue
    return count

def for_click(page, click_list, time_sleep):
    count = 0
    for click in click_list:
        xpath_list = click["action"]["xpath"]

        for xpath in xpath_list:
            try:
                locator = get_locator(xpath, page)
                if locator == False:
                    logger.error(f' - Not found(click): {xpath}')
                    continue

                locator.click()

                count += 1
                logger.info(f' - Success(click): {xpath}')
                time.sleep(time_sleep)
                break
            
            except Exception:
                logger.error(f' - Not found(click): {xpath}')
                continue
    return count

def for_send(page, send_list, time_sleep):
    count = 0
    for send in send_list:
        xpath_list = send["action"]["xpath"]

        for xpath in xpath_list:
            try:
                locator = get_locator(xpath, page)
                if locator == False:
                    logger.error(f' - Not found(send): {xpath}')
                    continue

                locator.click()

                count += 1
                logger.info(f' - Success(send): {xpath}')
                time.sleep(time_sleep)
                break

            except Exception:
                logger.error(f' - Not found(send): {xpath}')
                continue
    return count

def get_locator(xpath, page):
    try: 
        locator = page.locator(f"xpath={xpath}")
        if locator.count() == 0:
            return False
        if not locator.is_visible():
            return False
        
        locator.scroll_into_view_if_needed()
        locator.wait_for(state="attached")

        return locator
    
    except Exception as e:
        return False
