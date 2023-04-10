import logging
import time
import os

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import InlineQuery, InputTextMessageContent, InlineQueryResultArticle, InlineQueryResultVideo, InlineQueryResultAudio

from re import findall
from httpx import AsyncClient
from hashlib import md5

from tt_video import tt_videos_or_images, convert_image, divide_chunks, yt_dlp, get_url_of_yt_dlp
from settings import languages, API_TOKEN

storage = MemoryStorage()
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

def is_tool(name):
    from shutil import which

    return which(name) is not None

def get_user_lang(locale):
    user_lang = locale.language
    if user_lang not in languages:
        user_lang = "en"
    return user_lang


@dp.message_handler(commands=['start', 'help'])
@dp.throttled(rate=2)
async def send_welcome(message: types.Message):
    user_lang = get_user_lang(message.from_user.locale)
    await message.reply(languages[user_lang]["help"])


@dp.message_handler(regexp='https://\w{1,3}?\.?\w+\.\w{1,3}/')
@dp.throttled(rate=3)
async def tt_download2(message: types.Message):
    user_lang = get_user_lang(message.from_user.locale)

    await message.reply(languages[user_lang]["wait"])
    link = findall(r'\bhttps?://.*\w{1,30}\S+', message.text)[0]

    try:
        response = await yt_dlp(link)
        if response.endswith(".mp3"):
            await message.reply_audio(open(response, 'rb'), caption='@XLR_TT_BOT', title=link)
        # video
        else:
            logging.info(f"VIDEO: {response}")
            await message.reply_video(open(response, 'rb'), caption='@XLR_TT_BOT',)
        os.remove(response)

    except Exception as e:
        logging.error(e)
        await message.reply(f"error: {e}")
        os.remove(response)


@dp.message_handler()
@dp.throttled(rate=3)
async def echo(message: types.Message):
    user_lang = get_user_lang(message.from_user.locale)

    await message.answer(languages[user_lang]["invalid_link"])


if __name__ == '__main__':
    if is_tool("yt-dlp"):
        logging.info("yt-dlp installed")
        executor.start_polling(dp, skip_updates=True)
    else:
        logging.info("yt-dlp not installed")
        yt_dlp_url=get_url_of_yt_dlp()
        if yt_dlp_url != None:
            logging.info(f"found link: {yt_dlp_url}")
            if yt_dlp_url.endswith(".exe"):
                program_name="yt-dlp.exe"
            else:
                "yt-dlp"
            import urllib.request
            try:
                urllib.request.urlretrieve(yt_dlp_url, program_name)
                executor.start_polling(dp, skip_updates=True)
            except Exception as e:
                logging.error(e)
        else:
            logging.error("Cant find yt-dlp download link for your OS.")

