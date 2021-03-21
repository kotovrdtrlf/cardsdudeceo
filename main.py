import os
import time
import telebot
import boto3
import pymongo
from slugify import slugify_url


ACCESS_KEY_ID = os.environ.get('ACCESS_KEY_ID')
ACCESS_SECRET_KEY = os.environ.get('ACCESS_SECRET_KEY')
BUCKET_NAME = os.environ.get('BUCKET_NAME')
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ALLOWED_USER_IDS = os.environ.get('ALLOWED_USER_IDS').split()
DB_USER = os.environ.get('DB_USER')
DB_PASS = os.environ.get('DB_PASS')
DB_NAME = os.environ.get('DB_NAME')

# helper fns
def isAdmin(userId): # check if admin
  return str(userId) in ALLOWED_USER_IDS

def upload_to_aws(local_file, bucket, s3_file_name):
  s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY_ID, aws_secret_access_key=ACCESS_SECRET_KEY)
  
  s3.upload_file(local_file, bucket, s3_file_name, ExtraArgs={'ACL':'public-read'})

  url = f"https://{bucket}.s3.eu-central-1.amazonaws.com/{s3_file_name}"
  
  return url

def upload_to_mongo(card_info):
  client = pymongo.MongoClient(f"mongodb+srv://{DB_USER}:{DB_PASS}@cluster0.ooomj.mongodb.net/{DB_NAME}?retryWrites=true&w=majority")
  db = client["main"]
  col = db["cards"]
  col.insert_one(card_info)
# initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
  if (isAdmin(message.chat.id)):
    bot.send_message(message.chat.id, "Здравствуйте")
  else:
    bot.send_message(message.chat.id, "Теряйся, путник")

@bot.message_handler(commands=['cmds'])
def cmds(message):
  if (isAdmin(message.chat.id)):
    bot.send_message(message.chat.id, "/addCard - добавить карту")
  else:
    bot.send_message(message.chat.id, "Я же сказал, теряйся")

@bot.message_handler(commands=['addCard'])
def addCard(message):
  if (isAdmin(message.chat.id)):
    card_info = {
      "name": "", 
      "slug": "", 
      "price": 0, 
      "image": ""
    }
    bot.send_message(message.chat.id, "Запущен процесс добавления карты, пожалуйста будьте осторожны")
    name_inquiry = bot.send_message(message.chat.id, "Пожалуйста введите название скина. На сайте название будет отображаться ровно так, как вы его напишите сейчас")
    bot.register_next_step_handler(name_inquiry, setName, card_info)
    while len(card_info["name"]) == 0 and len(card_info["name"]) == 0:
      time.sleep(1)
    price_inquiry = bot.send_message(message.chat.id, "Пожалуйста введите цену скина")
    bot.register_next_step_handler(price_inquiry, setPrice, card_info)
    while card_info["price"] == 0:
      time.sleep(1)
    # bot.send_message(message.chat.id, str(card_info))
    image_inquiry = bot.send_message(message.chat.id, "Пожалуйста скиньте фото скина")
    bot.register_next_step_handler(image_inquiry, setImage, card_info)
    while len(card_info["image"]) == 0:
      time.sleep(1)
    confirm_inquiry = bot.send_message(
      message.chat.id, 
      f"Подтвердите правильность данных:\nНазвание: {card_info['name']}\nСлаг: {card_info['slug']}\nЦена: {card_info['price']}\nКартинка:\n{card_info['image']}"
    )
    bot.register_next_step_handler(confirm_inquiry, confirmUpload, card_info)

@bot.message_handler(content_types=['text'])
def text(message):
  if (isAdmin(message.chat.id)):
    bot.send_message(message.chat.id, "Что бы посмотреть список команд - /cmds")
  else:
    bot.send_message(message.chat.id, "Я же сказал, теряйся")
def setName(message, card_info):
  card_info["name"] = message.text
  card_info["slug"] = slugify_url(message.text)
def setPrice(message, card_info):
  card_info["price"] = int(message.text)
def confirmUpload(message, card_info):
  if message.text.lower() == "да":
    upload_to_mongo(card_info)
    bot.send_message(message.chat.id, "Информация отправлена в базу данных")
    os.remove(os.path.join(card_info["slug"]+".png"))
  else:
    bot.send_message(message.chat.id, "/addCard что бы начать заново")

@bot.message_handler(content_types=['photo'])
def randomImage(message):
  bot.send_message(message.chat.id, "Сори, я не просил картинку, теряйся")
def setImage(message, card_info):
  file_id = message.photo[-1].file_id
  file_info = bot.get_file(file_id)
  downloaded_file = bot.download_file(file_info.file_path)

  with open(card_info["slug"]+".png", "wb") as new_file:
    new_file.write(downloaded_file)

  file_url = upload_to_aws(os.path.join(card_info["slug"]+".png"), BUCKET_NAME, card_info["slug"]+".png")
  card_info["image"] = file_url

bot.polling()