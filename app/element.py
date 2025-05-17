import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.playwrite_setting import open_browser
from playwright.sync_api import sync_playwright
from utilities.logger import logger

#form_elements: 
def form_elements(page):
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

def get_form_elements(url, p):
    try:    
        browser, page = open_browser(url, p)
        if not browser:
            raise RuntimeError(f'error: Did not get browser from playwrite')
        else:
            logger.info(f'>Got browser from playwrite')
        if not page:
            raise RuntimeError(f'error: Did not get page from playwrite')
        else:
            logger.info(f'>Got page from playwrite')
    except Exception as e:
        raise RuntimeError(f'error: {e}') from e
        
    try:    
        elements = form_elements(page)
        if not elements:
            raise RuntimeError(f'error: Did not get elements')
        else:
            logger.info(f'>Got elements from page')
    except Exception as e:
        raise RuntimeError(f'error: {e}') from e
    
    logger.info(f'>🏠 Return to logic.py')
    return elements, browser, page

#confirm_elements: 
def confirm_elements(page):
    elements = page.evaluate("""
() => {
    const fields = [];

    // ボタンとしての役割を判定する関数
    const isButtonLike = (el) => {
        const tag = el.tagName.toLowerCase();
        const type = el.getAttribute("type")?.toLowerCase() || "";
        const role = el.getAttribute("role")?.toLowerCase() || "";

        return (
            tag === "button" ||
            (tag === "input" && ["submit", "button"].includes(type)) ||
            (["a", "div", "span"].includes(tag) && role === "button") ||
            el.hasAttribute("onclick")
        );
    };

    const targets = Array.from(document.querySelectorAll("*")).filter(el => {
        const visible = !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
        return visible && isButtonLike(el);
    });

    targets.forEach((el, index) => {
        const tag = el.tagName.toLowerCase();
        const type = el.getAttribute("type")?.toLowerCase() || "";
        const value = el.getAttribute("value") || "";
        const text = el.innerText?.trim() || value;

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

        fields.push({
            index,
            tag,
            type,
            text,
            attributes: attrs,
            nearby_text: [...new Set(nearby)].filter(t => t)
        });
    });

    return fields;
}
""")

    return elements

def get_confirm_elements(page):
    try:
        elements = confirm_elements(page)
        if not elements:
            raise RuntimeError(f'error: Did not get elements')
        else:
            logger.info(f'>Got elements from page')
    except Exception as e:
        raise RuntimeError(f'error: {e}') from e
    
    logger.info(f'>🏠 Return to logic.py')
    return elements


if __name__ == "__main__":
    with sync_playwright() as p:
        browser, page = open_browser("https://www.pantry-lucky.jp/contact/", p)
        input()
        elements = get_confirm_elements(page)
        print(elements)
        input()

