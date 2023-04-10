from httpx import AsyncClient

from re import findall
from io import BytesIO
from PIL import Image
from subprocess import check_output, Popen, TimeoutExpired, PIPE
import time
import asyncio
import platform


def divide_chunks(list, n):
    for i in range(0, len(list), n):
        yield list[i:i + n]


def convert_image(image, extention):  # "JPEG"
    byteImgIO = BytesIO()
    byteImg = Image.open(BytesIO(image)).convert("RGB")
    byteImg.save(byteImgIO, extention)
    byteImgIO.seek(0)
    return byteImgIO

def get_url_of_yt_dlp():
    download_url="https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"

    os = platform.system().lower()
    arch = platform.machine().lower();
    if os == None or arch == None:
        print(f"Cant detect os({os}) or arch({arch})")
    else:
        print(os,arch)
        if os == "darwin":
            return f"{download_url}_macos"
        elif os == "windows":
            if arch in ["amd64","x86_64"]:
                arch=".exe"
            elif arch in ["i386","i686"]:
                arch="_x86.exe"
            else:
                return None
            return f"{download_url}{arch}"
        elif os == "linux":
            if arch in ["aarch64","aarch64_be", "armv8b", "armv8l"]:
                arch = "_linux_aarch64"
            elif arch in ["amd64","x86_64"]:
                arch = "_linux"
            elif arch == "armv7l":
                arch="_linux_armv7l"
            else:
                return None
            return f"{download_url}{arch}"

# only video or music
# async
async def yt_dlp(url):
    proc = await asyncio.create_subprocess_exec(
        'yt-dlp', url, "--max-filesize", "50M", "--max-downloads", "1", "--restrict-filenames",#, "-o", "%(title)s.%(ext)s", 
        stdout=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    except asyncio.exceptions.TimeoutError:
        try:
            proc.kill()
        except OSError:
            print("timeout no such process")
            # Ignore 'no such process' error
            pass
        raise Exception('timeout')

    for line in stdout.decode("utf-8").splitlines():
        print(line)
        filename = findall(r" Destination: (.*?)$", line)
        if len(filename) == 0:
            filename = findall(r" (.*?) has already been downloaded$", line)
            if len(filename) > 0:
                filename = filename[0]
                print("FOUND")
                break
        else:
            filename = filename[0]
            print("FOUND")
            break
    else:
        print("file not found")
        raise Exception('file not found')
    return filename


async def tt_videos_or_images(url):
    video_id_from_url = findall('https://www.tiktok.com/@.*?/video/(\d+)', url)
    user_agent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:105.0) Gecko/20100101 Firefox/105.0"
    if len(video_id_from_url) > 0:
        video_id = video_id_from_url[0]
    else:
        headers1 = {
            "User-Agent": user_agent,
            "Accept": "text/html, application/xhtml+xml, application/xml; q=0.9, image/avif, image/webp, */*; q=0.8"
        }

        async with AsyncClient() as client:
            r1 = await client.get(url, headers=headers1)
        print("r1", r1.status_code)
        if r1.status_code == 301:
            video_id = findall(
                'a href="https://\w{1,3}\.tiktok\.com/(?:@.*?/video|v)/(\d+)', r1.text)[0]
        elif r1.status_code == 403:
            video_id = findall("video&#47;(\d+)", r1.text)[0]
        else:
            # raise BaseException('Unknown status code', r1.status_code)
            return BaseException('Unknown status code', r1.status_code)

    print("video_id:", video_id)
    url2 = f"http://api16-normal-useast5.us.tiktokv.com/aweme/v1/aweme/detail/?aweme_id={video_id}"
    async with AsyncClient() as client:
        r2 = await client.get(url2, headers={"User-Agent": user_agent})
    print("r2", r2.status_code)
    print("r2_headers:", r2.headers)
    print("r2_text:", r2.text)
    # resp = r2.json()
    resp = r2.json().get("aweme_detail")
    if resp == None:
        # raise BaseException('No video here')
        return BaseException('No video here')

    is_video = len(resp["video"]["bit_rate"]) > 0
    print("is_video", is_video)

    nickname = resp["author"]["nickname"]
    desc = resp["desc"]
    statistic = resp["statistics"]
    music = resp["music"]["play_url"]["uri"]
    if is_video:
        cover_url = resp["video"]["origin_cover"]["url_list"][0]

        for bit_rate in resp["video"]["bit_rate"]:
            height = bit_rate["play_addr"]["height"]
            width = bit_rate["play_addr"]["width"]
            data_size = int(bit_rate["play_addr"]["data_size"])

            url_list = bit_rate["play_addr"]["url_list"]
            quality_type = bit_rate["quality_type"]

            if data_size > 19999999:
                print("to_large_for_tg", height, "x", width, data_size /
                      1000000, "MB", "quality_type:", quality_type)
            else:
                print("good_for_tg", height, "x", width, data_size /
                      1000000, "MB", "quality_type:", quality_type,
                      "url:", url_list[0])
                videos_url = url_list
                large_for_tg = False
                break
        else:
            videos_url = resp["video"]["bit_rate"][0]["play_addr"]["url_list"]
            large_for_tg = True
        return {"is_video": True, "large_for_tg": large_for_tg, "cover": cover_url, "items": videos_url, "nickname": nickname, "desc": desc, "statistic": statistic, "music": music}

    else:
        images_url = []
        images = resp["image_post_info"]["images"]
        for i in images:
            if len(i["display_image"]["url_list"]) > 0:
                images_url.append(i["display_image"]["url_list"][0])
            else:
                print("err. images_url 0 len")
        return {"is_video": False, "large_for_tg": False, "cover": None, "items": images_url, "nickname": nickname, "desc": desc, "statistic": statistic, "music": music}
