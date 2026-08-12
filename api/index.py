import os
import requests
from flask import Flask, request
import telebot

# Fallback prevents Vercel build crashes before the environment variable is set
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
    try:
        response = requests.post(url, json={"query": query, "variables": {"username": username}})
        data = response.json()
        
        if "errors" in data:
            return "❌ User not found or LeetCode is temporarily blocking requests."
            
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
    except Exception as e:
        return "❌ Error parsing LeetCode data."

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! Send `/leetcode your_username` to check your DSA progress.", parse_mode="Markdown")

@bot.message_handler(commands=['leetcode'])
def leetcode_check(message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ Please provide a username.\nExample: `/leetcode adithya`", parse_mode="Markdown")
        return
    
    bot.reply_to(message, "Fetching stats... ⏳")
    stats_msg = get_leetcode_stats(parts[1])
    bot.reply_to(message, stats_msg, parse_mode="Markdown")

# Webhook receiver route (Vercel routes Telegram's hidden pings here)
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

# Activation route to wire Telegram to your Vercel URL
@app.route('/set_webhook')
def set_webhook():
    webhook_url = request.host_url + TOKEN
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return f"✅ Webhook successfully bound to: {webhook_url}", 200

@app.route('/')
def home():
    return "Bot API is live. Visit /set_webhook to bind Telegram.", 200
