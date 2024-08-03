import os
import openai
import requests
import json
import subprocess
import telebot
import redis
import pickle
import stripe
import math
import random
import pandas as pd
import datetime
import time
from telebot import types, util
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain import PromptTemplate
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from pydub import AudioSegment
from pydub.playback import play
from flask import Flask, request
from google_tts import google_text_to_speech
from ibm_tts import ibm_text_to_speech
from dotenv import load_dotenv
from unidecode import unidecode

load_dotenv()
stripe.api_key = os.getenv("STRIPE_API_KEY")
token = os.getenv("TELEGRAM_TOKEN")
xi_api_key = os.getenv("XI_TOKEN")
redis_pw = os.getenv("REDIS_PW")
redis_url = os.getenv("REDIS_URL")
webhook_url = os.getenv('WEBHOOK_URL')
endpoint_secret = os.getenv('ENDPOINT_SECRET')

bot = telebot.TeleBot(token)
llm = ChatOpenAI(temperature=0.9, model_name="gpt-4o")
r = redis.Redis(
    host=redis_url,
    port=10839,
    password=redis_pw)

welcome_messages = {
    '🇩🇪 German': "Ich freue mich darauf, dir dabei zu helfen, die Nuancen der deutschen Sprache zu entdecken! Auf geht's! 😍\n\n",
    '🇵🇱 Polish': 'Bardzo się cieszę, że mogę Ci pomóc odkryć subtelności języka polskiego! Zaczynamy? 😍\n\n',
    '🇪🇸 Spanish': '¡Estoy emocionada de ayudarte a descubrir los matices del idioma español! ¿Empezamos? 😍\n\n',
    '🇮🇹 Italian': "Non vedo l'ora di aiutarti a scoprire le sfumature della lingua italiana! Cominciamo? 😍\n\n",
    '🇫🇷 French': "J'ai hâte de t'aider à découvrir les nuances de la langue française! On commence? 😍\n\n",
    '🇧🇷 Portuguese': 'Estou ansiosa para ajudar você a descobrir as nuances da língua portuguesa! Vamos começar? 😍\n\n',
    '🇮🇳 Hindi': 'मुझे उत्साह है कि मैं आपको हिंदी भाषा की नई बातें सिखा सकूं! चलिए शुरू करते हैं? 😍\n\n',
    '🇳🇱 Dutch': 'Ik kan niet wachten om je de nuances van de Nederlandse taal te laten ontdekken! Laten we beginnen? 😍\n\n',
    '🇨🇳 Chinese': '我迫不及待要帮助你发现中文的微妙之处！我们开始吧？😍\n\n'
}

translation_messages = {
    '🇩🇪 German': "🇺🇸 _I am looking forward to helping you discover the nuances of the German language! Let's go! 😍_\n\n*(Disable translation\n clicking -> /translation)*",
    '🇵🇱 Polish': "🇺🇸 _I am very pleased to be able to help you discover the subtleties of the Polish language! Shall we start? 😍_\n\n*(Disable translation\n clicking -> /translation)*",
    '🇪🇸 Spanish': "🇺🇸 _I am excited to help you discover the nuances of the Spanish language! Shall we start? 😍_\n\n*(Disable translation\n clicking -> /translation)*",
    '🇮🇹 Italian': "🇺🇸 _I can't wait to help you discover the nuances of the Italian language! Shall we start? 😍_\n\n*(Disable translation\n clicking -> /translation)*",
    '🇫🇷 French': "🇺🇸 _I can't wait to help you discover the nuances of the French language! Shall we start? 😍_\n\n*(Disable translation\n clicking -> /translation)*",
    '🇧🇷 Portuguese': "🇺🇸 _I'm eager to help you discover the nuances of the Portuguese language! Shall we start? 😍_\n\n*(Disable translation\n clicking -> /translation)*",
    '🇮🇳 Hindi': "🇺🇸 _I'm excited that I can teach you new things about the Hindi language! Shall we start? 😍_\n\n*(Disable translation\n clicking -> /translation)*",
    '🇳🇱 Dutch': "🇺🇸 _I can't wait to help you discover the nuances of the Dutch language! Shall we start? 😍_\n\n*(Disable translation\n clicking -> /translation)*",
    '🇨🇳 Chinese': "🇺🇸 _I can't wait to help you discover the subtleties of Chinese! Shall we start? 😍_\n\n*(Disable translation\n clicking -> /translation)*"
}

offer = "*Nobody ever learnt a language using Duolingo - Stop the Procrastination and Go Pro with LLA! 🚀*\n\n*Get your Personal AI Language Teacher with Unlimited Messages* 🧠\n\n_This is a limited-time beta offer. Subscriptions can be easily managed and cancelled with the /settings command._ 🌟"

app = Flask(__name__)

def translate(text_to_translate):
    prompt = f"Translate the following text to English: {text_to_translate}"
    print(prompt)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    # Extract the assistant's reply from the response
    translated_text = response['choices'][0]['message']['content']

    return translated_text

def update_stats(content_type, user_id=None, characters_count=0):
    print(f"update_stats called with content_type: {content_type}, user_id: {user_id}, characters_count: {characters_count}")
    today = datetime.date.today()
    try:
        if user_id is not None:
            if content_type == 'text':
                r.incr('text_messages_count')
            elif content_type == 'voice':
                r.incr('audio_messages_received')
                r.hincrby('audio_messages_per_user', user_id, 1)
            is_existing_user = r.sismember('all_users', user_id)
            if not is_existing_user:
                r.incr(f'new_users_{today}')
            r.sadd('all_users', user_id)
            key = f'daily_users_{today}'
            r.sadd(key, user_id)
            r.hincrby('messages_per_user', user_id, 1)# increment the count for this user
            r.hincrby(f'messages_per_day_{user_id}_{today}', 'count', 1)
            daily = int(r.hget(f'messages_per_day_{user_id}_{today}', 'count') or 0)
            print(daily)
            pro_user = False
            if r.sismember('pro_users', user_id):
                pro_user = True
            if daily > 6 and not pro_user:
                print("free daily messages over.")
                return False
            user_messagesx = int(r.hget('messages_per_user', user_id) or 0)  # retrieve this user's count
            print("This user sent a total of " + str(user_messagesx) + " messages")
            if user_messagesx == 3:
                user_audio_messages = int(r.hget('audio_messages_per_user', user_id) or 0)
                if user_audio_messages == 0:
                    bot.send_message(user_id, '_Try sending a voice message as well! 😊_', parse_mode='Markdown')
            if user_messagesx == 5:
                quizzes_played = int(r.hget('quizzes_played', user_id) or 0)
                if quizzes_played == 0:
                    time.sleep(2)
                    bot.send_message(user_id, '_Want to test your 📖 Vocabulary 📖 knowledge? Click → /play _', parse_mode='Markdown')    
        elif user_id is None:
            r.incr('audio_messages_sent')
            r.incrby('characters_to_tts', characters_count)
    except redis.exceptions.RedisError as e:
        print(f"An error occurred with user_id: {user_id} and content type: {content_type}. Error details: {str(e)}")
    return True
        
def list_files(dir_path='.'):
    for path in os.listdir(dir_path):
        full_path = os.path.join(dir_path, path)
        if os.path.isdir(full_path):
            print(f'{full_path}/')
            list_files(full_path)
        else:
            print(full_path)

def convert_ogg_to_mp3(ogg_file_path, mp3_file_path):
    print("YOOO")
    command = ['ffmpeg', '-y', '-i', ogg_file_path, '-c:a', 'libmp3lame', mp3_file_path]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, check=True)
    
def convert_mp3_to_ogg(mp3_file_path, ogg_file_path):
    command = ['ffmpeg', '-y', '-i', mp3_file_path, '-c:a', 'libopus', ogg_file_path]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, check=True)

def generate_template(selected_language):
    return f"""
    you are a friendly, informal native {selected_language} teacher conversing with a student who is learning {selected_language}. 
            
    you adapt to student level. if they ask you a lot of questions in english or they make a lot of mistakes, you will speak a simpler {selected_language} and you will use more english for context. 
        
    if the student asks a question in english --> respond with the answer to the question in english, give a real life example with the translation in {selected_language}, and resume the conversation with a question in {selected_language}.
        
    only use english when the student does so first. you only generate the teacher's sentences, not the student's, and each student's input should receive a single, supportive response from you.
    
    DO NOT EVER ASK "ANYTHING ELSE YOU WANT TO TALK ABOUT?". USE PREVIOUS CONVERSATION DETAILS TO CREATE INTERESTING QUESTIONS.
        
    Engage with the student's personal stories and plans, asking relevant follow-up questions. Communicate informally like a friend rather than an assistant. 
    Your responses should be no more than 200 characters to keep the conversation flowing.
    
    Here's the current conversation:
    Teacher: *welcomes student in {selected_language} and asks if excited to learn it*
    {{history}}
    Student: {{input}}
    Teacher:
    """

def get_ai_response(chat_id, message_text, selected_language):
    template = generate_template(selected_language)
    prompt = PromptTemplate(
        input_variables=["history", "input"], template=template
    )
    if not r.exists(chat_id):
        conversation = ConversationChain(
            prompt=prompt,
            llm=llm,
            verbose=False,
            memory=ConversationBufferWindowMemory(human_prefix="Student", ai_prefix="Teacher", k=10)
        )
        r.set(chat_id, pickle.dumps(conversation))
    else:
        print("Loading existing conversation.")
        conversation = pickle.loads(r.get(chat_id))
        print(conversation.llm.model_name)
    ai_response = conversation.predict(input=message_text)
    # Update the conversation chain and store it back to Redis
    r.set(chat_id, pickle.dumps(conversation))
    return ai_response

def generate_question(chat_id):
    df = pd.read_csv('quiz.csv')
    selected_language = r.get(f"{chat_id}_language")
    selected_language = selected_language.decode('utf-8') if selected_language else 'English'
    word = random.choice(df['Word'].tolist())
    r.set(f"{chat_id}_current_word", word)
    example = df.loc[df['Word'] == word, 'Example'].values[0]
    bot.send_message(chat_id, f"How do you write '{word}' in {selected_language}? As in '{example}'")
    
@bot.callback_query_handler(func=lambda call: call.data == 'delete_data')
def handle_delete_data(call):
    print("deleting")
    chat_id = call.message.chat.id
    user_id = call.message.from_user.id
    if r.sismember('translation_disabled', user_id):
        print("io")
        r.srem('translation_disabled', user_id)
    if r.sismember('translation_enabled', user_id):
        print("yo")
        r.srem('translation_enabled', user_id)
    if r.exists(chat_id):
        r.delete(chat_id)
    if r.exists(f"{chat_id}_language"):
        r.delete(f"{chat_id}_language")
    if r.sismember('translation_disabled', user_id):
        r.srem('translation_disabled', user_id)
        print("abl")
    if r.sismember('translation_enabled', user_id):
        print("dis")
        r.srem('translation_enabled', user_id)
    bot.send_message(chat_id, "Let's Start Fresh!")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    itembtn1 = types.KeyboardButton('🇮🇳 Hindi')
    itembtn2 = types.KeyboardButton('🇩🇪 German')
    itembtn3 = types.KeyboardButton('🇵🇱 Polish')
    itembtn4 = types.KeyboardButton('🇪🇸 Spanish')
    itembtn5 = types.KeyboardButton('🇮🇹 Italian')
    itembtn6 = types.KeyboardButton('🇫🇷 French')
    itembtn7 = types.KeyboardButton('🇧🇷 Portuguese')
    itembtn8 = types.KeyboardButton('🇳🇱 Dutch')
    itembtn9 = types.KeyboardButton('🇨🇳 Chinese')
    markup.row(itembtn1, itembtn2, itembtn3, itembtn4, itembtn5, itembtn6, itembtn7, itembtn8, itembtn9)
    bot.send_message(chat_id, "⬇️ Please select the desired language using the Buttons below! ⬇️", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id  # Get chat id from the call
    if call.data == "restart_quiz":
        r.set(f"{chat_id}_mode", "quiz")
        r.set(f"{chat_id}_quiz_counter", 0)
        r.set(f"{chat_id}_quiz_score", 0)
        generate_question(chat_id)
    elif call.data == "stop_quiz":
        # Stop the quiz
        bot.send_message(chat_id, "You can now continue your conversation :)")

@bot.message_handler(func=lambda message: message.text is not None and message.text != "/settings" and r.get(f"{message.chat.id}_mode") is not None and r.get(f"{message.chat.id}_mode").decode('utf-8') == 'quiz')
def handle_quiz_answer(message):
    chat_id = message.chat.id
    user_answer = message.text
    try:
        word = r.get(f"{chat_id}_current_word")
        word = word.decode('utf-8') if word else None
        selected_language = r.get(f"{chat_id}_language")
        selected_language = selected_language.decode('utf-8') if selected_language else None
        if selected_language:
            language = selected_language[2:].strip()
        score = int(r.get(f"{chat_id}_quiz_score") or 0)  # Get the current quiz score
        quiz_counter = int(r.get(f"{chat_id}_quiz_counter") or 0)
        print(language)
        
        # Load the quiz.csv file
        quiz_df = pd.read_csv('quiz.csv')

        # Get the possible answers for the current word in the selected language
        possible_answer_string = quiz_df.loc[quiz_df['Word'] == word,language].values[0]
        possible_answers = possible_answer_string.split(',') if isinstance(possible_answer_string, str) else []

        # Check if the user_answer is in the possible answers
        if unidecode(user_answer.strip().lower()) in [unidecode(answer.strip().lower()) for answer in possible_answers]:
            score = int(r.get(f"{chat_id}_quiz_score") or 0)  # Get the current quiz score
            score += 1  # Increment score if the answer is correct
            bot.send_message(chat_id, "🥰 Correct answer! 🥰")
            # Save the updated score
            r.set(f"{chat_id}_quiz_score", score)
        else:
            bot.send_message(chat_id, f"Incorrect answer! Possible answers are: {', '.join(possible_answers[:3])}")
            # time.sleep(1)
            # markup = types.InlineKeyboardMarkup()
            # itembtn1 = types.InlineKeyboardButton('👂 Listen', callback_data='restart_quiz')
            # itembtn2 = types.InlineKeyboardButton('Next Question!', callback_data='next_question')
            # markup.add(itembtn1, itembtn2)
            # bot.send_message(chat_id, "Want to 👂 listen to the answers?", reply_markup=markup)
        quiz_counter += 1  # Increment quiz counter
        r.set(f"{chat_id}_quiz_score", score)  # Update the quiz score
        r.set(f"{chat_id}_quiz_counter", quiz_counter)  # Update the quiz counter
        bot.send_message(chat_id, f"This was question {quiz_counter} of 5.")
        if quiz_counter >= 5:  # Check if quiz is complete
            if r.exists(f"{chat_id}_mode"):
                r.delete(f"{chat_id}_mode")
            bot.send_message(chat_id, f"YOU GOT {score}/5 RIGHT❗Live reaction below ⬇️ ")
            time.sleep(1)
            if score == 5:
                bot.send_animation(chat_id, "CgACAgQAAxkBAAIWYGSlmOsPHs6EaE2M6xpnkNiMjAoqAAJgAwACjd4EU72Y4al_E-94LwQ")
            elif score == 4:
                bot.send_animation(chat_id, "CgACAgQAAxkBAAIWX2SlmL720dsgRw90Lals9kj4Xh2TAAK9AgAC6GgNUwx_cFG4cuCbLwQ")
            elif score == 3:
                bot.send_animation(chat_id, "CgACAgIAAxkBAAIWYWSlmQqD0u2xST52aKhDyCvRlL2_AAIDEgACPpZJSIgHs4XE-BI5LwQ")
            elif score == 2:
                bot.send_animation(chat_id, "CgACAgQAAxkBAAIWYmSlmSg02tCKULh6Zicg1T7nr9ZEAAIYAwACAdAFUxiKYqMJinb0LwQ")
            elif score == 1:
                bot.send_animation(chat_id, "CgACAgQAAxkBAAIWY2SlmTwpgbaxBdFb4n6IHqEiZUESAAIWAwACjKwFU0I3JWIy37XRLwQ")
            else:
                bot.send_animation(chat_id, "CgACAgQAAxkBAAIWZmSlmVBVodUE2QeNn-Wn6-hfDGsPAAImAwACaaQMU4OHIQ-15py8LwQ")
            # Clear quiz data
            r.delete(f"{chat_id}_mode", f"{chat_id}_current_word", f"{chat_id}_quiz_score", f"{chat_id}_quiz_counter")
            r.incr('quiz_count')
            markup = types.InlineKeyboardMarkup()
            itembtn1 = types.InlineKeyboardButton('🟢 ANOTHER QUIZ!', callback_data='restart_quiz')
            itembtn2 = types.InlineKeyboardButton('🛑 Stop the quiz', callback_data='stop_quiz')
            markup.add(itembtn1, itembtn2)
            bot.send_message(chat_id, "WHAT'S NEXT?", reply_markup=markup)
        else:
            r.delete(f"{chat_id}_current_word")
            generate_question(chat_id)
    except Exception as e:
        print(f"An error occurred in handle_quiz_answer: {str(e)}")

@bot.message_handler(commands=['start', 'pro', 'play', 'settings', 'translation'])
def handle_commands(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if message.text == '/pro':
        r.incr('checked_upgrade')
        time.sleep(1)
        bot.send_message(user_id, offer, parse_mode='Markdown')
        time.sleep(1)
        pro_payment_link = f"https://buy.stripe.com/7sI03ta0c2qjf6g4gk?client_reference_id={user_id}"
        markup = types.InlineKeyboardMarkup()
        pro_pay_button = types.InlineKeyboardButton('Pro subscription ($1.99/week)', url=pro_payment_link)
        markup.add(pro_pay_button)
        bot.send_message(chat_id, "Click the Link Below!", reply_markup=markup)
    elif message.text == '/translation': 
        if r.sismember('translation_enabled', user_id):
            print("Translation is already enabled")
            r.sadd('translation_disabled', user_id)
            r.srem('translation_enabled', user_id)
            bot.send_message(chat_id, "Translation disabled. You can continue the conversation 😀")
        else:
            print("Translation is not enabled")
            print(f"Setting translation for chat_id: {chat_id}")  # Print the chat_id
            try:
                r.sadd('translation_enabled', user_id)  # Add to set
                if r.sismember('translation_disabled', user_id):
                    r.srem('translation_disabled', user_id)
            except Exception as e:
                print(f"An error occurred when trying to add the user to the set in Redis: {e}")  # Print the error if one occurs
            bot.send_message(chat_id, "Translation enabled. All subsequent messages from the teacher will be translated.")       
    elif message.text == '/play':
        r.hincrby('quizzes_played', user_id, 1)
        r.set(f"{chat_id}_mode", "quiz")
        r.set(f"{chat_id}_quiz_counter", 0)
        r.set(f"{chat_id}_quiz_score", 0)
        quizzes_played = int(r.hget('quizzes_played', user_id) or 0)
        quiz_message = translation_messages.get(message.text, f'<b>This is your {quizzes_played}° quiz! </b>💪')
        bot.send_message(chat_id, quiz_message, parse_mode='HTML')
        generate_question(chat_id)
    elif message.text.startswith('/start'):
        try:
            if not r.sismember('translation_enabled', user_id):
                r.sadd('translation_enabled', user_id)
        except Exception as e:
            print(f"An error occurred when trying to add the user to the set in Redis: {e}") 
        referral_code = message.text[7:]  # extract the referral code
        if referral_code:
            if referral_code == '4myfriends':
                r.incr('referred_users')
            elif referral_code == 'website':
                r.incr('users_from_website')
        else:
            pass
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        itembtn1 = types.KeyboardButton('🇮🇳 Hindi')
        itembtn2 = types.KeyboardButton('🇩🇪 German')
        itembtn3 = types.KeyboardButton('🇵🇱 Polish')
        itembtn4 = types.KeyboardButton('🇪🇸 Spanish')
        itembtn5 = types.KeyboardButton('🇮🇹 Italian')
        itembtn6 = types.KeyboardButton('🇫🇷 French')
        itembtn7 = types.KeyboardButton('🇧🇷 Portuguese')
        itembtn8 = types.KeyboardButton('🇳🇱 Dutch')
        itembtn9 = types.KeyboardButton('🇨🇳 Chinese')
        markup.row(itembtn1, itembtn2, itembtn3, itembtn4, itembtn5, itembtn6, itembtn7, itembtn8, itembtn9)
        bot.send_message(chat_id, "⬇️ Please select the desired language using the Buttons below! ⬇️", reply_markup=markup)
    elif message.text == '/settings':
        if r.exists(f"{chat_id}_mode"):
            r.delete(f"{chat_id}_mode")
        if r.exists(f"{chat_id}_current_word"):
            r.delete(f"{chat_id}_current_word")
        if r.exists(f"{chat_id}_quiz_score"):
            r.delete(f"{chat_id}_quiz_score")
        if r.exists(f"{chat_id}_quiz_counter"):
            r.delete(f"{chat_id}_quiz_counter")
        markup = types.InlineKeyboardMarkup()
        support_button = types.InlineKeyboardButton('Get Support/Leave Feedback', url='http://t.me/franzstupar')
        manage_sub_button = types.InlineKeyboardButton('Manage Subscription', url='https://billing.stripe.com/p/login/00geXqgxBavv2JO000')
        delete_data_button = types.InlineKeyboardButton('Reset Language & Conversation Data', callback_data='delete_data')
        markup.row(delete_data_button)
        markup.row(support_button)
        markup.row(manage_sub_button)
        bot.send_message(chat_id, "Control Center 🎛️: Use the buttons below to manage your settings.", reply_markup=markup)
    else:
        bot.send_message(chat_id, "Confusion.")

@bot.message_handler(func=lambda message: message.text is not None and message.text in ['🇩🇪 German', '🇵🇱 Polish', '🇪🇸 Spanish', '🇮🇹 Italian', '🇫🇷 French', '🇧🇷 Portuguese', '🇮🇳 Hindi', '🇳🇱 Dutch', '🇨🇳 Chinese'])
def handle_language_selection(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    translation_possible = True
    if r.sismember('translation_disabled', user_id):
        translation_possible = False
    try:
        # Get current selected language
        selected_language = r.get(f"{chat_id}_language")
        print(f"Current selected language for chat_id {chat_id}: {selected_language}")

        if selected_language is not None:
            # If a language is already selected, delete it
            r.delete(f"{chat_id}_language")
            if r.exists(chat_id):
                r.delete(chat_id)
            if r.exists(f"{chat_id}_language"):
                r.delete(f"{chat_id}_language")
            if r.exists(f"{chat_id}_mode"):
                r.delete(f"{chat_id}_mode")
            if r.exists(f"{chat_id}_current_word"):
                r.delete(f"{chat_id}_current_word")
            if r.exists(f"{chat_id}_quiz_score"):
                r.delete(f"{chat_id}_quiz_score")
            if r.exists(f"{chat_id}_quiz_counter"):
                r.delete(f"{chat_id}_quiz_counter")
            print(f"Deleted language for chat_id {chat_id}")

        # Set new language
        r.set(f"{chat_id}_language", message.text)
        # bot.send_message(chat_id, "<b>If you send a voice message, you will receive a voice message back!\n\nAnd remember to try command /play 😊</b>", parse_mode='HTML')
        # time.sleep(1)
        
        welcome_message = welcome_messages.get(message.text, "<b>Welcome to Learn Languages AI! Try sending a voice message or text message.</b>")
        bot.send_message(chat_id, welcome_message)
        if translation_possible:
            time.sleep(1)
            translation_message = translation_messages.get(message.text, "<b>Welcome to Learn Languages AI! Try sending a voice message or text message.</b>")
            bot.send_message(chat_id, translation_message, parse_mode='Markdown')
    except redis.exceptions.RedisError as e:
        print(f"Redis error: {e}")
        bot.send_message(chat_id, f"An error occurred: {str(e)}")

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    user_id = message.from_user.id
    daily = update_stats(message.content_type, user_id)
    if daily == False:
        r.incr('checked_upgrade')
        print("user finished daily messages")
        bot.send_message(user_id, "You finished your 7 free daily messages.")
        try:
            bot.send_message(user_id, offer, parse_mode='Markdown')
        except Exception as e:
            print(f"Error when trying to send promotional offer: {e}")
            
        pro_payment_link = f"https://buy.stripe.com/7sI03ta0c2qjf6g4gk?client_reference_id={user_id}"
        markup = types.InlineKeyboardMarkup()
        pro_pay_button = types.InlineKeyboardButton('Become a Pro ($1.99/week) ', url=pro_payment_link)
        markup.add(pro_pay_button)
        try:
            bot.send_message(user_id, "Click the Link Below!", reply_markup=markup)
        except Exception as e:
            print(f"Error when trying to send subscription link: {e}")
        return "yo"
    chat_id = message.chat.id
    ogg_file_path = f'{chat_id}_voice.ogg'
    mp3_file_path = f'{chat_id}_voice.mp3'
    audio_duration = message.voice.duration  # duration in seconds
    if audio_duration > 120:
        bot.send_message(chat_id, "Sorry, your audio is too long. 2 minutes max!")
        return
    try:
        selected_language = r.get(f"{chat_id}_language").decode('utf-8') or 'English'  # fallback to English if not found
    except redis.exceptions.RedisError as e:
        bot.send_message(chat_id, f"An error occurred: {str(e)}")
        return
    print(f"Handling message for chat {chat_id} with selected language: {selected_language}")
    try:
        file_info = bot.get_file(message.voice.file_id)
    except Exception as e:
        print(f"Error occurred while getting the file: {e}")
        return
    try:
        downloaded_file = bot.download_file(file_info.file_path)
    except Exception as e:
        print(f"Error occurred while downloading the file: {e}")
        return
    try:
        with open(ogg_file_path, 'wb') as new_file:
            new_file.write(downloaded_file)
    except IOError as e:
        print(f"Error occurred while opening/writing the file: {e}")
        return
    convert_ogg_to_mp3(ogg_file_path, mp3_file_path)
    audio_file = open(mp3_file_path, "rb")
    try:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
    except Exception as e:
        print(f"Error occurred while transcribing the audio: {e}")
        return
    text = transcript.text
    print(f"Transcribed text: {text}")
    # Check if transcription was successful
    if text:
        print("Transcription was successful")
    else:
        print("Transcription failed")
    ai_response = get_ai_response(chat_id, text, selected_language)        
    if selected_language != '🇵🇱 Polish' and selected_language != '🇨🇳 Chinese' and selected_language != '🇮🇳 Hindi':
        response_ogg_path = ibm_text_to_speech(ai_response, chat_id, selected_language)
    else:
        response_ogg_path = google_text_to_speech(ai_response, chat_id, selected_language)
    audio_file = open(response_ogg_path, 'rb')
    bot.send_voice(message.chat.id, audio_file, caption=ai_response)
    audio_file.close()
    if r.sismember('translation_enabled', user_id):
        translation = translate(ai_response)
        flag_emoji = u"\U0001F1FA\U0001F1F8"  # Unicode for American Flag emoji
        formatted_translation = f"{flag_emoji} _{translation}_"
        bot.send_message(message.chat.id, formatted_translation, parse_mode='Markdown')
    try:
        os.remove(response_ogg_path)  # delete response audio file
    except Exception as e:
        print(f"Error occurred while trying to delete response audio file: {e}")
    try:
        os.remove(ogg_file_path)  # delete original voice message file
    except Exception as e:
        print(f"Error occurred while trying to delete original voice message file: {e}")

    try:
        os.remove(mp3_file_path)  # delete converted voice message file
    except Exception as e:
        print(f"Error occurred while trying to delete converted voice message file: {e}")

@bot.message_handler(func=lambda message: message.text is not None)
def handle_text(message):
    print(message.text)
    chat_id = message.chat.id
    user_id = message.from_user.id
    if len(message.text) > 500:
        bot.send_message(chat_id, "Sorry, your message is too long")
        return
    daily = update_stats(message.content_type, user_id)
    if daily == False:
        print("user finished daily messages")
        r.incr('checked_upgrade')
        bot.send_message(user_id, "You finished your 7 free daily messages.")
        time.sleep(1)
        try:
            bot.send_message(user_id, offer, parse_mode='Markdown')
        except Exception as e:
            print(f"Error when trying to send promotional offer: {e}")   
        pro_payment_link = f"https://buy.stripe.com/7sI03ta0c2qjf6g4gk?client_reference_id={user_id}"
        markup = types.InlineKeyboardMarkup()
        pro_pay_button = types.InlineKeyboardButton('Become a Pro ($1.99/week) ', url=pro_payment_link)
        markup.add(pro_pay_button)
        time.sleep(1)
        try:
            bot.send_message(user_id, "Click the Link Below!", reply_markup=markup)
        except Exception as e:
            print(f"Error when trying to send subscription link: {e}")
        return "yo"
    try:
        selected_language = r.get(f"{chat_id}_language").decode('utf-8') or 'English'  # fallback to English if not found
    except redis.exceptions.RedisError as e:
        bot.send_message(chat_id, f"An error occurred: {str(e)}")
        return
    print(f"Handling message for chat {chat_id} with selected language: {selected_language}")
    ai_response = get_ai_response(chat_id, message.text, selected_language)
    print(f"AI response: {ai_response}")
    bot.send_message(message.chat.id, ai_response)
    if r.sismember('translation_enabled', user_id):
        translation = translate(ai_response)
        flag_emoji = u"\U0001F1FA\U0001F1F8"  # Unicode for American Flag emoji
        formatted_translation = f"{flag_emoji} _{translation}_"
        bot.send_message(message.chat.id, formatted_translation, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)  # this will catch every message
def error_handler(message):
    chat_id = message.chat.id
    try:
        bot.send_message(chat_id, "Sorry, there's been an error. Text http://t.me/franzstupar for support.")
    except Exception as e:
        print(f"An error occurred while trying to send a message to chat_id: {chat_id}. Error details: {str(e)}")

@app.route('/' + token, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "HELLO!", 200

@app.errorhandler(404)
def handle_404(error):
    app.logger.error('A 404 error occurred: %s', (str(error)))
    return str(error), 404

@app.route("/", methods=["GET"])
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url= webhook_url + token)
    return "HEY", 200

@app.route("/dashboard", methods=["GET"])
def dashboard():
    try:
        total_users = r.scard('all_users')
        text_messages_count = int(r.get('text_messages_count') or 0)
        checked_upgrade = int(r.get('checked_upgrade') or 0)
        audio_messages_received = int(r.get('audio_messages_received') or 0)
        audio_messages_sent = int(r.get('audio_messages_sent') or 0)
        characters_to_tts = int(r.get('characters_to_tts') or 0)
        average_characters_per_audio = characters_to_tts / audio_messages_sent if audio_messages_sent > 0 else 0
        average_characters_per_audio = math.ceil(average_characters_per_audio)
        quiz_count = int(r.get('quiz_count') or 0)
        referred_users = int(r.get('referred_users') or 0)
        users_from_website = int(r.get('users_from_website') or 0)
        daily_users_data = "<ul>"
        for i in range(90):
            date = (datetime.date.today() - datetime.timedelta(days=i))
            key = f'daily_users_{date}'
            new_users_key = f'new_users_{date}'
            if r.exists(key): # check if key exists in Redis
                users_on_date = r.scard(key)
                new_users_on_date = int(r.get(new_users_key) or 0)  # get new users count for the date
                daily_users_data += f'<li>{date}: {users_on_date} users, {new_users_on_date} new users</li>'
            else:
                daily_users_data += ''
        daily_users_data += "</ul>" 
    except redis.exceptions.RedisError as e:
        return f"<h1>An error occurred:</h1><p>{str(e)}</p>", 500

    return f'''
    <h1>DASHBOARD</h1>
    <p>Total users: {total_users}</p>
    <p>Times that people saw price (either with /pro or ended free daily messages): {checked_upgrade}</p>
    <p>Text messages received: {text_messages_count}</p>
    <p>Audio messages received: {audio_messages_received}</p>
    <p>Characters sent to TTS: {characters_to_tts}</p>
    <p>Average characters sent to TTS: {average_characters_per_audio}</p>
    <p>Quiz Count: {quiz_count}</p>
    <p>Referred Users: {referred_users}</p>
    <p>Users from website: {users_from_website}</p>
    <h2>Daily users:</h2>
    {daily_users_data}
    ''', 200, {'Content-Type': 'text/html'}

@app.route('/stripe_webhook', methods=['POST'])
def webhook_received():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    event = None
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return 'Invalid signature', 400
    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get('client_reference_id')
        customer_id = session.get('customer')
        print("User " + user_id + " went Pro")
        r.sadd('pro_users', user_id)
        try:
            bot.send_message(user_id, "You are a PRO MEMBER now!!")
        except telebot.apihelper.ApiTelegramException as e:
            print(f"Failed to send message to user {user_id}: {e}")
        r.hset('stripe_customers', customer_id, user_id)
    if event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        customer_id = subscription.get('customer')
        user_id = r.hget('stripe_customers', customer_id)
        print("user removed from pro - deleted sub")
        r.srem('pro_users', user_id)
    if event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        customer_id = invoice.get('customer')
        user_id = r.hget('stripe_customers', customer_id)
        if user_id is None:
            print(f"Failed to find user ID for customer {customer_id}")
        print(f"Payment for User {user_id} has failed")
        try:
            r.srem('pro_users', user_id)
            print("User removed from pro - payment failed")
        except Exception as e:
            print(f"Failed to remove user {user_id} from pro_users: {e}")
        try:
            bot.send_message(user_id, "Your payment failed! You are momentarily a free member. Come back to pro with /pro command!")
        except telebot.apihelper.ApiTelegramException as e:
            print(f"Failed to send message to user {user_id}: {e}")
    if event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        customer_id = invoice.get('customer')
        user_id = r.hget('stripe_customers', customer_id)
        subscription_id = invoice['subscription']
        subscription = stripe.Subscription.retrieve(subscription_id)
        print(f"User {user_id} has successfully renewed their subscription")
        r.hset('messages_per_user', user_id, 0)
        try:
            bot.send_message(user_id, "Congrats on still being a PRO member! Keep going strong in your language learning process! 💪")
        except telebot.apihelper.ApiTelegramException as e:
            print(f"Failed to send message to user {user_id}: {e}")
    return 'Success', 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))