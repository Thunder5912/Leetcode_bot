import os
import requests
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'DUMMY_TOKEN')

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

def get_leetcode_stats(username):
    url = "https://leetcode.com/graphql"
    query = """
    query getUserProfile($username: String!) {
      matchedUser(username: $username) {
        submitStats: submitStatsGlobal {
          acSubmissionNum {
            difficulty
            count
          }
        }
      }
    }
    """
    
    # NEW: Fake browser headers to bypass LeetCode's Cloudflare security
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Content-Type": "application/json"
    }
    
    try:
        # NEW: Added headers and a strict 5-second timeout to prevent Vercel crashes
        response = requests.post(
            url, 
            json={"query": query, "variables": {"username": username}},
            headers=headers,
            timeout=5
        )
        data = response.json()
        
        if "errors" in data:
            return "❌ User not found."
            
        stats = data['data']['matchedUser']['submitStats']['acSubmissionNum']
        total = stats[0]['count']
        easy = stats[1]['count']
        medium = stats[2]['count']
        hard = stats[3]['count']
        
        return (
            f"📊 **LeetCode Stats for {username}**\n\n"
            f"🔹 **Total Solved:** {total}\n"
            f"🟢 **Easy:** {easy}\n"
            f"🟡 **Medium:** {medium}\n"
            f"🔴 **Hard:** {hard}"
        )
    except requests.exceptions.Timeout:
        return "❌ LeetCode is taking too long to respond (Timeout). Try again."
    except Exception as e:
        return "❌ Error parsing LeetCode data or LeetCode blocked the request."

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    btn = InlineKeyboardButton("🔍 Search LeetCode User", callback_data="ask_username")
    markup.add(btn)
    bot.reply_to(message, "Welcome! Click the button below to check any LeetCode profile.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "ask_username")
def callback_ask(call):
    bot.answer_callback_query(call.id)
    markup = ForceReply()
    bot.send_message(call.message.chat.id, "👇 Reply to this message with the LeetCode username:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.reply_to_message is not None and m.reply_to_message.text == "👇 Reply to this message with the LeetCode username:")
def handle_username(message):
    username = message.text.strip()
    bot.reply_to(message, f"Fetching stats for {username}... ⏳")
    
    stats_msg = get_leetcode_stats(username)
    bot.send_message(message.chat.id, stats_msg, parse_mode="Markdown")

@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route('/set_webhook')
def set_webhook():
    webhook_url = f"https://{request.host}/{TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return f"✅ Webhook successfully bound to: {webhook_url}", 200

@app.route('/')
def home():
    return "Bot API is live.", 200
