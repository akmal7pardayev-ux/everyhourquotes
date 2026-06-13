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


FONT_PATHS = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
    '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
    '/System/Library/Fonts/Helvetica.ttc',
    'C:\\Windows\\Fonts\\arial.ttf',
]

FALLBACK_QUOTES = [
    "Stay hungry, stay foolish. \u2014 Steve Jobs",
    "The only limit is your mind.",
    "Be the change you wish to see in the world. \u2014 Gandhi",
    "Less talk, more action.",
    "Dream big. Work hard. Stay focused.",
    "Kindness is free, sprinkle it everywhere.",
    "Focus on the good.",
    "Make today count.",
    "Simplicity is the ultimate sophistication.",
    "Trust the process.",
    "Act as if what you do makes a difference. It does.",
    "Do what you love, love what you do.",
    "Every moment is a fresh beginning.",
    "Happiness is not a destination, it's a way of life.",
    "In a world where you can be anything, be kind.",
    "Success is not final, failure is not fatal: it is the courage to continue that counts.",
    "Believe you can and you're halfway there.",
    "It does not matter how slowly you go as long as you do not stop.",
    "The future belongs to those who believe in the beauty of their dreams.",
    "What you get by achieving your goals is not as important as what you become.",
]


def load_font(size):
    for path in FONT_PATHS:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def generate_quote_image(quote_text, author=None):
    width, height = 1080, 1080
    img = Image.new('RGB', (width, height), color=(18, 18, 30))
    draw = ImageDraw.Draw(img)

    font = load_font(52)
    author_font = load_font(40)

    wrapper = textwrap.TextWrapper(width=28)
    lines = wrapper.wrap(quote_text)

    total_h = len(lines) * 70
    y = (height - total_h) // 2

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (width - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, fill=(245, 245, 255), font=font)
        y += 70

    if author:
        author_text = f'\u2014 {author}'
        bbox = draw.textbbox((0, 0), author_text, font=author_font)
        x = (width - (bbox[2] - bbox[0])) // 2
        draw.text((x, y + 30), author_text, fill=(160, 160, 180), font=author_font)

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf.getvalue()


def fetch_quote():
    sources = [
        'https://zenquotes.io/api/random',
        'https://api.quotable.io/random',
    ]
    for url in sources:
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
    quote = random.choice(FALLBACK_QUOTES)
    if ' \u2014 ' in quote:
        parts = quote.split(' \u2014 ', 1)
        return parts[0].strip(), parts[1].strip()
    return quote, None


def _build_multipart(fields, files, boundary):
    body = io.BytesIO()
    for key, value in fields.items():
        body.write(f'--{boundary}\r\n'.encode())
        body.write(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        body.write(f'{value}\r\n'.encode())
    for name, filename, content_type, data in files:
        body.write(f'--{boundary}\r\n'.encode())
        body.write(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode())
        body.write(f'Content-Type: {content_type}\r\n\r\n'.encode())
        body.write(data)
        body.write(b'\r\n')
    body.write(f'--{boundary}--\r\n'.encode())
    return body.getvalue()


def send_telegram_photo(bot_token, chat_id, photo_bytes):
    boundary = uuid.uuid4().hex
    url = f'https://api.telegram.org/bot{bot_token}/sendPhoto'
    body = _build_multipart(
        {'chat_id': chat_id},
        [('photo', 'quote.png', 'image/png', photo_bytes)],
        boundary,
    )
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
    image_bytes = generate_quote_image(quote_text, author)
    send_telegram_photo(bot_token, chat_id, image_bytes)
    print(f'Posted: {quote_text[:80]}...')


if __name__ == '__main__':
    main()
