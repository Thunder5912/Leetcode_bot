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
    
    # NEW: Expanded GraphQL Query to fetch Rank, Contests, and Recent Submissions
    query = """
    query getUserProfile($username: String!) {
      matchedUser(username: $username) {
        profile {
          ranking
          reputation
        }
        submitStats: submitStatsGlobal {
          acSubmissionNum {
            difficulty
            count
          }
        }
      }
      userContestRanking(username: $username) {
        rating
        topPercentage
      }
      recentAcSubmissionList(username: $username, limit: 1) {
        title
      }
    }
    """
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            url, 
            json={"query": query, "variables": {"username": username}},
            headers=headers,
            timeout=5
        )
        data = response.json()
        
        if "errors" in data or not data.get('data', {}).get('matchedUser'):
            return "❌ User not found."
            
        # 1. Base Problem Stats
        stats = data['data']['matchedUser']['submitStats']['acSubmissionNum']
        total = stats[0]['count']
        easy = stats[1]['count']
        medium = stats[2]['count']
        hard = stats[3]['count']
        
        # 2. Profile & Global Rank
        profile = data['data']['matchedUser']['profile']
        global_rank = profile.get('ranking', 'N/A')
        reputation = profile.get('reputation', 0)
        
        # 3. Contest Rating (Handles users who never took a contest)
        contest_data = data['data'].get('userContestRanking')
        if contest_data:
            rating = round(contest_data.get('rating', 0))
            top_percent = contest_data.get('topPercentage', 'N/A')
            contest_text = f"🏆 **Contest Rating:** {rating} (Top {top_percent}%)"
        else:
            contest_text = "🏆 **Contest Rating:** Unranked (No contests)"
            
        # 4. Last Solved Problem
        recent_submissions = data['data'].get('recentAcSubmissionList', [])
        if recent_submissions:
            last_solved = recent_submissions[0]['title']
            last_solved_text = f"🔥 **Last Solved:** {last_solved}"
        else:
            last_solved_text = "🔥 **Last Solved:** None recently"
            
        # Final formatting
        return (
            f"🧑‍💻 **LeetCode Profile: {username}**\n"
            f"🌍 **Global Rank:** {global_rank:,}\n"
            f"{contest_text}\n"
            f"🤝 **Reputation:** {reputation}\n\n"
            f"📈 **Problems Solved (Total: {total})**\n"
            f"🟢 **Easy:** {easy} | 🟡 **Medium:** {medium} | 🔴 **Hard:** {hard}\n\n"
            f"{last_solved_text}"
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
    bot.reply_to(message, f"Fetching advanced stats for {username}... ⏳")
    
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
