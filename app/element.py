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
    const value = el.getAttribute("value")?.trim() || "";

    // text_candidates
    const text_candidates = {
      inner_text: el.innerText?.trim() || "",
      value: value,
      placeholder: el.getAttribute("placeholder")?.trim() || "",
      aria_label: el.getAttribute("aria-label")?.trim() || "",
      title: el.getAttribute("title")?.trim() || "",
      alt: el.getAttribute("alt")?.trim() || ""
    };

    // 可視判定
    const style = window.getComputedStyle(el);
    const visible = !!(
      el.offsetParent !== null &&
      style.display !== "none" &&
      style.visibility !== "hidden" &&
      style.opacity !== "0"
    );

    // MECEな対象判定
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

    // 全属性
    const attrs = {};
    for (const attr of el.attributes) {
      attrs[attr.name] = attr.value;
    }

    // text_structure の構築
    let hasDirectText = false;
    let hasDescendantText = false;
    const descendantsWithText = new Set();
    let textSource = null;

    // 直下にテキストノードがあるか確認
    Array.from(el.childNodes).forEach(node => {
      if (node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0) {
        hasDirectText = true;
      }
    });

    // 子孫にテキストノードを含む要素があるか確認
    el.querySelectorAll("*").forEach(descendant => {
      const txt = descendant.textContent?.trim();
      if (txt && txt.length > 0) {
        hasDescendantText = true;
        descendantsWithText.add(descendant.tagName.toLowerCase());
        if (!textSource) {
          textSource = descendant.tagName.toLowerCase();
        }
      }
    });

    const text_structure = {
      has_direct_text: hasDirectText,
      has_descendant_text: hasDescendantText,
      descendants_with_text: Array.from(descendantsWithText),
      ...(textSource ? { text_source: textSource } : {})
    };

    // nearby_text（構造化）
    const nearby = [];

    const id = el.getAttribute("id");
    if (id) {
      const forLabel = document.querySelector(`label[for="${id}"]`);
      if (forLabel) {
        nearby.push({ source: "label", text: forLabel.innerText.trim() });
      }
    }

    let wrapped_by_label = false;
    let current = el;
    while (current.parentElement) {
      current = current.parentElement;
      if (current.tagName.toLowerCase() === "label") {
        nearby.push({ source: "label", text: current.innerText.trim() });
        wrapped_by_label = true;
        break;
      }
    }

    let parent = el.parentElement;
    let depth = 0;
    while (parent && depth < 2) {
      const txt = parent.innerText?.trim();
      if (txt) {
        nearby.push({ source: "parent", text: txt });
      }
      parent = parent.parentElement;
      depth++;
    }

    const prev = el.previousElementSibling;
    if (prev && prev.innerText) {
      nearby.push({ source: "sibling", text: prev.innerText.trim() });
    }

    const options = isSelect
      ? Array.from(el.options)
          .map(opt => ({
            label: opt.label?.trim() || opt.innerText?.trim() || "",
            value: opt.value?.trim() || ""
          }))
          .filter(opt => opt.label && opt.value)
      : undefined;

    // 最終出力
    fields.push({
      index,
      tag,
      type,
      attributes: attrs,
      text_candidates,
      text_structure,
      nearby_text: nearby,
      ...(options ? { options } : {}),
      ...(attrs.name && ["radio", "checkbox"].includes(type) ? { group_name: attrs.name } : {}),
      ...(wrapped_by_label ? { wrapped_by_label: true } : {})
    });
  });

  return fields;
}
    """)

    return elements

def form_elements_v2(page):
    elements = page.evaluate("""
() => {
  const fields = [];
  const targets = document.querySelectorAll('input, select, textarea, button, a[role="button"], div[role="button"]');

  targets.forEach((el, index) => {
    const tag = el.tagName.toLowerCase();
    const type = el.getAttribute("type")?.toLowerCase() || "";
    const role = el.getAttribute("role") || "";
    const value = el.getAttribute("value")?.trim() || "";

    // text_candidates を構築
    const text_candidates = {
      inner_text: el.innerText?.trim() || "",
      value: value,
      placeholder: el.getAttribute("placeholder")?.trim() || "",
      aria_label: el.getAttribute("aria-label")?.trim() || "",
      title: el.getAttribute("title")?.trim() || "",
      alt: el.getAttribute("alt")?.trim() || ""
    };

    // 表示判定（厳密）
    const style = window.getComputedStyle(el);
    const visible = !!(
      el.offsetParent !== null &&
      style.display !== "none" &&
      style.visibility !== "hidden" &&
      style.opacity !== "0"
    );

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

    // 全属性
    const attrs = {};
    for (const attr of el.attributes) {
      attrs[attr.name] = attr.value;
    }

    // nearby_text（構造化）
    const nearby = [];

    const id = el.getAttribute("id");
    if (id) {
      const forLabel = document.querySelector(`label[for="${id}"]`);
      if (forLabel) {
        nearby.push({ source: "label", text: forLabel.innerText.trim() });
      }
    }

    // labelラップされている場合
    let wrapped_by_label = false;
    let current = el;
    while (current.parentElement) {
      current = current.parentElement;
      if (current.tagName.toLowerCase() === "label") {
        nearby.push({ source: "label", text: current.innerText.trim() });
        wrapped_by_label = true;
        break;
      }
    }

    // 親テキスト（2階層まで）
    let parent = el.parentElement;
    let depth = 0;
    while (parent && depth < 2) {
      const txt = parent.innerText?.trim();
      if (txt) {
        nearby.push({ source: "parent", text: txt });
      }
      parent = parent.parentElement;
      depth++;
    }

    // 直前の兄弟
    const prev = el.previousElementSibling;
    if (prev && prev.innerText) {
      nearby.push({ source: "sibling", text: prev.innerText.trim() });
    }

    // select用 options
    const options = isSelect
      ? Array.from(el.options)
          .map(opt => ({
            label: opt.label?.trim() || opt.innerText?.trim() || "",
            value: opt.value?.trim() || ""
          }))
          .filter(opt => opt.label && opt.value)
      : undefined;

    // 構成
    fields.push({
      index,
      tag,
      type,
      attributes: attrs,
      text_candidates,
      nearby_text: nearby,
      ...(options ? { options } : {}),
      ...(attrs.name && ["radio", "checkbox"].includes(type) ? { group_name: attrs.name } : {}),
      ...(wrapped_by_label ? { wrapped_by_label: true } : {})
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

