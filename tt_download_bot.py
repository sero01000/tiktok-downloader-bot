import logging
import time

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import InlineQuery, InputTextMessageContent, InlineQueryResultArticle, InlineQueryResultVideo, InlineQueryResultAudio

from re import findall
from httpx import AsyncClient
from hashlib import md5

from tt_video import tt_videos_or_images, convert_image, divide_chunks
from settings import languages, API_TOKEN


storage = MemoryStorage()
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

def get_user_lang(locale):
    user_lang = locale.language
    if user_lang not in languages:
        user_lang = "en"
    return user_lang


@dp.message_handler(commands=['start', 'help'])
@dp.throttled(rate=2)
async def send_welcome(message: types.Message):
    user_lang=get_user_lang(message.from_user.locale)
    await message.reply(languages[user_lang]["help"])


@dp.message_handler(regexp='https://\w{2,3}\.tiktok\.com/')
@dp.throttled(rate=3)
async def tt_download(message: types.Message):
    user_lang=get_user_lang(message.from_user.locale)

    await message.reply(languages[user_lang]["wait"])
    link = findall(r'\bhttps?://.*tiktok\S+', message.text)[0]
    link = link.split("?")[0]

    try:
        response = await tt_videos_or_images(link)
        if len(response["items"]) > 0:
            await message.reply(f'❤️ {languages[user_lang]["likes"]}:{response["statistic"]["digg_count"]}\n💬 {languages[user_lang]["comments"]}:{response["statistic"]["comment_count"]}\n📢 {languages[user_lang]["share"]}:{response["statistic"]["share_count"]}\n👤 {languages[user_lang]["views"]}:{response["statistic"]["play_count"]}\n🗣 {languages[user_lang]["nickname"]}:{response["nickname"]}\n{response["desc"]}')
            await message.reply_audio(response["music"], caption='@XLR_TT_BOT')
            if response["is_video"]:
                print("items",response["items"][0])
                if response["large_for_tg"]:
                    await message.reply(f'{languages[user_lang]["large_for_tg"]}:{response["items"][0]}')
                else:
                    await message.reply_video(response["items"][0], caption='@XLR_TT_BOT')
            #images
            else:
                # metod1 download,convert to jpg, load to telegram, send MediaGroup
                url_groups = list(divide_chunks(response["items"], 10))
                async with AsyncClient() as client:
                    for group in url_groups:
                        media = types.MediaGroup()
                        for url in group:
                            resp = await client.get(url)
                            img_jpeg = convert_image(resp.content, "JPEG")
                            media.attach_photo(types.InputFile(img_jpeg))
                        await message.reply_media_group(media=media)

                # metod2 send single photos by urls as webp sticker (less internet usage)
                # for url in response["items"]:
                #     await message.reply_document(url, caption='@XLR_TT_BOT')
        else:
            await message.reply("error 0 videos or images")
    except Exception as e:
        print(e)
        await message.reply(f"error: {e}")


@dp.throttled(rate=3)
@dp.inline_handler(regexp='https://\w{2,3}\.tiktok\.com/')
async def inline_echo(inline_query: InlineQuery):

    text = inline_query.query or 'xlr'

    link = findall(r'\bhttps?://.*tiktok\S+', text)[0]
    link = link.split("?")[0]

    user_lang=get_user_lang(inline_query.from_user.locale)

    try:
        response = await tt_videos_or_images(link)
        if len(response["items"]) > 0:
            statisctic = f'{link}\n❤️ {languages[user_lang]["likes"]}:{response["statistic"]["digg_count"]}\n💬 {languages[user_lang]["comments"]}:{response["statistic"]["comment_count"]}\n📢 {languages[user_lang]["share"]}:{response["statistic"]["share_count"]}\n👤 {languages[user_lang]["views"]}:{response["statistic"]["play_count"]}\n🗣 {languages[user_lang]["nickname"]}:{response["nickname"]}\n{response["desc"]}'
            audio_url = response["music"]

            result_id_statistic: str = md5(
                f"{link} statistic".encode()).hexdigest()
            statistic = InlineQueryResultArticle(

                id=result_id_statistic,

                title=f'statistic: {statisctic}',

                input_message_content=InputTextMessageContent(statisctic),

                thumb_url="https://ak.picdn.net/shutterstock/videos/1061280574/thumb/6.jpg?ip=x480",

                description=response["nickname"]
            )

            result_id_music: str = md5(
                f"{link} music".encode()).hexdigest()
            music = InlineQueryResultAudio(

                id=result_id_music,

                title='download music',

                audio_url=audio_url,

                performer=response["nickname"],

            )

            if response["is_video"]:
                video_url = response["items"][0]

                if response["large_for_tg"]:
                    result_id_video_url: str = md5(
                        video_url.encode()).hexdigest()
                    video = InlineQueryResultArticle(

                        id=result_id_video_url,

                        title=f'video get url',

                        input_message_content=InputTextMessageContent(
                            video_url),
                    )

                else:
                    result_id_video: str = md5(
                    f"{link} video".encode()).hexdigest()

                    video = InlineQueryResultVideo(

                        id=result_id_video,

                        title='download video',

                        video_url=video_url,

                        thumb_url=response["cover"],

                        mime_type="video/mp4",

                        description=response["desc"]
                    )

                await bot.answer_inline_query(inline_query.id, results=[statistic, music, video])

            else:

                text_url_images = '\n'.join(response["items"])
                result_id_url_images: str = md5(
                    text_url_images.encode()).hexdigest()
                images = InlineQueryResultArticle(

                    id=result_id_url_images,

                    title=f'get url of {len(response["items"])} images',

                    input_message_content=InputTextMessageContent(
                        text_url_images),
                )

                await bot.answer_inline_query(inline_query.id, results=[statistic, music, images])

        else:
            print("0 items")
            result_id: str = md5("0 items".encode()).hexdigest()
            error_inline = InlineQueryResultArticle(

                id=result_id,

                title=f'error_0_items',

                input_message_content=InputTextMessageContent('error_0_items'),
            )

            await bot.answer_inline_query(inline_query.id, results=[error_inline])

    except Exception as e:
        print("err1", e)
        result_id: str = md5(f"err1 {e}".encode()).hexdigest()
        error_inline = InlineQueryResultArticle(

            id=result_id,

            title=f'error: {e}',

            input_message_content=InputTextMessageContent(f'error {e!r}'),
        )

        await bot.answer_inline_query(inline_query.id, results=[error_inline])


@dp.message_handler()
@dp.throttled(rate=3)
async def echo(message: types.Message):
    user_lang=get_user_lang(message.from_user.locale)

    await message.answer(languages[user_lang]["invalid_link"])


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
