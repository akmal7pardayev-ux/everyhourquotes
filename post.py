import datetime
import io
import json
import os
import random
import sys
import textwrap
import uuid
import urllib.error
import urllib.request

from PIL import Image, ImageDraw, ImageFont


FONT_NAME = 'Poppins'
FONT_URLS = {
    f'{FONT_NAME}-Regular.ttf': 'https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-Regular.ttf',
    f'{FONT_NAME}-Medium.ttf': 'https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-Medium.ttf',
    f'{FONT_NAME}-Bold.ttf': 'https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-Bold.ttf',
}

ACCENT_COLORS = [
    (255, 107, 107),
    (72, 219, 251),
    (255, 223, 0),
    (155, 89, 255),
    (46, 204, 113),
    (255, 165, 0),
    (0, 210, 211),
    (255, 99, 132),
]

API_SOURCES = [
    'https://zenquotes.io/api/random',
    'https://api.quotable.io/random',
]


def _font_path(style):
    for d in [os.path.dirname(__file__), '/tmp']:
        p = os.path.join(d, f'{FONT_NAME}-{style}.ttf')
        if os.path.exists(p):
            return p
    url = FONT_URLS.get(f'{FONT_NAME}-{style}.ttf')
    if url:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                dest = os.path.join('/tmp', f'{FONT_NAME}-{style}.ttf')
                with open(dest, 'wb') as f:
                    f.write(resp.read())
                return dest
        except Exception:
            pass
    return None


def load_font(size, style='Regular'):
    p = _font_path(style)
    if p:
        return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def create_gradient(w, h, c1, c2):
    strip = Image.new('RGB', (1, h))
    for y in range(h):
        r = int(c1[0] + (c2[0] - c1[0]) * y / h)
        g = int(c1[1] + (c2[1] - c1[1]) * y / h)
        b = int(c1[2] + (c2[2] - c1[2]) * y / h)
        strip.putpixel((0, y), (r, g, b))
    return strip.resize((w, h), Image.Resampling.LANCZOS)


def generate_quote_image(quote_text, author, accent):
    width, height = 1080, 1080
    bg = create_gradient(width, height, (10, 10, 24), (22, 20, 44))
    draw = ImageDraw.Draw(bg)

    quote_font = load_font(56, 'Bold')
    author_font = load_font(40, 'Regular')

    wrapper = textwrap.TextWrapper(width=26)
    lines = wrapper.wrap(quote_text)

    total_h = len(lines) * 75
    y = (height - total_h) // 2 - 40

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=quote_font)
        x = (width - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, fill=(245, 245, 255), font=quote_font)
        y += 75

    if author:
        y += 20
        lw = 60
        draw.rectangle([(width // 2 - lw // 2, y), (width // 2 + lw // 2, y + 3)], fill=accent)
        y += 25
        text = f'\u2014 {author}'
        bbox = draw.textbbox((0, 0), text, font=author_font)
        x = (width - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), text, fill=accent, font=author_font)

    buf = io.BytesIO()
    bg.save(buf, format='PNG')
    buf.seek(0)
    return buf.getvalue()


def load_local_quotes():
    p = os.path.join(os.path.dirname(__file__), 'quotes.json')
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def fetch_quote():
    for url in API_SOURCES:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                if isinstance(data, list) and data:
                    return data[0]['q'], data[0]['a']
                elif isinstance(data, dict) and data.get('content'):
                    return data['content'], data['author']
        except Exception:
            continue

    quotes = load_local_quotes()
    if quotes:
        cats = list(quotes.keys())
        cat = cats[datetime.datetime.now().weekday() % len(cats)]
        pool = quotes.get(cat, [])
        if pool:
            pick = random.choice(pool)
            return pick['text'], pick.get('author')

    return 'Stay hungry, stay foolish.', 'Steve Jobs'


def _build_multipart(fields, files, boundary):
    body = io.BytesIO()
    for k, v in fields.items():
        body.write(f'--{boundary}\r\n'.encode())
        body.write(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode())
        body.write(f'{v}\r\n'.encode())
    for name, filename, ctype, data in files:
        body.write(f'--{boundary}\r\n'.encode())
        body.write(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode())
        body.write(f'Content-Type: {ctype}\r\n\r\n'.encode())
        body.write(data)
        body.write(b'\r\n')
    body.write(f'--{boundary}--\r\n'.encode())
    return body.getvalue()


def send_telegram_photo(bot_token, chat_id, photo_bytes, caption=None):
    boundary = uuid.uuid4().hex
    url = f'https://api.telegram.org/bot{bot_token}/sendPhoto'
    fields = {'chat_id': chat_id}
    if caption:
        fields['caption'] = caption
    body = _build_multipart(fields, [('photo', 'quote.png', 'image/png', photo_bytes)], boundary)
    req = urllib.request.Request(url, data=body)
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def main():
    bot_token = os.environ.get('BOT_TOKEN')
    chat_id = os.environ.get('CHAT_ID')

    if not bot_token or not chat_id:
        print('Missing BOT_TOKEN or CHAT_ID environment variables')
        sys.exit(1)

    quote_text, author = fetch_quote()
    accent = random.choice(ACCENT_COLORS)
    image_bytes = generate_quote_image(quote_text, author, accent)
    caption = f'\u201c{quote_text}\u201d' + (f' \u2014 {author}' if author else '')
    send_telegram_photo(bot_token, chat_id, image_bytes, caption=caption)
    print(f'Posted: {quote_text[:80]}...')


if __name__ == '__main__':
    main()
