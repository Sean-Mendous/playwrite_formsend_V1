from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)

def chatgpt_4omini(prompt, client=client):
    load_dotenv()
    api_key = os.getenv('OPENAI_API_KEY')
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a form sender agent."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.9
    )
    return response.choices[0].message.content

def chatgpt_4o_image_model(encoded_image, prompt, client=client):
    load_dotenv()
    api_key = os.getenv('OPENAI_API_KEY')
    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
    model="gpt-4o",
        messages=[
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_image}"}}
            ]}
        ],
        temperature=0
    )

    result = response.choices[0].message.content.strip().lower()
    return result


if __name__ == "__main__":
    prompt = """
このサイトについて詳細に教えて。

サイト：
https://sb-blm.discover-news.tokyo/ab/eLfux-HDTNsPTiYCsuhw?utm_creative=002_tiktok_001__013_004&utm_source=tiktok&utm_medium=paid&utm_id=__CAMPAIGN_ID__&utm_campaign=__CAMPAIGN_NAME__
"""
    print(chatgpt_4omini(prompt))

