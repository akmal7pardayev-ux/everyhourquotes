import json
import os
import random
import sys
import urllib.parse
import urllib.request
import urllib.error


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
                    return f'{data[0]["q"]} \u2014 {data[0]["a"]}'
                elif isinstance(data, dict) and data.get('content'):
                    return f'{data["content"]} \u2014 {data["author"]}'
        except Exception:
            continue
    return random.choice(FALLBACK_QUOTES)


def send_telegram(bot_token, chat_id, message):
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    data = urllib.parse.urlencode({
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML',
    }).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def main():
    bot_token = os.environ.get('BOT_TOKEN')
    chat_id = os.environ.get('CHAT_ID')

    if not bot_token or not chat_id:
        print("Missing BOT_TOKEN or CHAT_ID environment variables")
        sys.exit(1)

    quote = fetch_quote()
    send_telegram(bot_token, chat_id, quote)
    print(f'Posted: {quote[:80]}...')


if __name__ == '__main__':
    main()
