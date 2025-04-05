from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from pyromod import listen
from aiohttp import ClientSession
import helper
import time
import sys
import shutil
import os
import re
import logging
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import headers from separate file (create headers.py)
try:
    from headers import (
        ALLEN_HEADERS,
        CLASSPLUS_HEADERS,
        PHYSICSWALLAH_HEADERS,
        VISIONIAS_HEADERS
    )
except ImportError:
    logger.error("Create headers.py with required headers!")
    sys.exit(1)

# Bot configuration
class Config:
    BOT_TOKEN = "YOUR_BOT_TOKEN"
    API_ID = "YOUR_API_ID"
    API_HASH = "YOUR_API_HASH"
    VIP_USERS = [1714266885]  # Authorized user IDs

bot = Client(
    "edu_downloader",
    bot_token=Config.BOT_TOKEN,
    api_id=Config.API_ID,
    api_hash=Config.API_HASH
)

# Utility functions
async def validate_user(user_id: int) -> bool:
    """Check if user is authorized"""
    if user_id not in Config.VIP_USERS:
        await bot.send_message(
            user_id,
            "⚠️ You're not authorized! Contact @St2Master for access."
        )
        return False
    return True

async def clean_temp_files():
    """Clean temporary files"""
    temp_dir = "./temp"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)

# Bot handlers
@bot.on_message(filters.command(["start", "help"]))
async def start_handler(_, m: Message):
    await m.reply_text(
        "🎓 **Education Content Downloader Bot**\n\n"
        "✅ Supported Platforms:\n"
        "- Vision IAS\n- PhysicsWallah\n- Classplus\n- Allen Institute\n"
        "➡️ Use /master to start download process\n\n"
        "🔧 Maintained by: @St2Master"
    )

@bot.on_message(filters.command("master"))
async def master_handler(_, m: Message):
    """Main download handler"""
    try:
        if not await validate_user(m.from_user.id):
            return

        # Step 1: Get master file
        msg = await m.reply("📥 Send master TXT file or paste URLs")
        input_file = await bot.listen(m.chat.id, timeout=300)
        
        urls = []
        if input_file.document:
            file_path = await input_file.download()
            with open(file_path) as f:
                urls = [line.strip() for line in f if line.strip()]
            os.remove(file_path)
        else:
            urls = [input_file.text.strip()]
        
        await input_file.delete()
        await msg.edit(f"✅ Found {len(urls)} URLs\n📝 Send starting index (default: 1)")

        # Step 2: Get start index
        input_index = await bot.listen(m.chat.id, timeout=120)
        start_index = int(input_index.text) if input_index.text.isdigit() else 1
        await input_index.delete()

        # Step 3: Get batch info
        await msg.edit("📛 Enter batch name:")
        input_batch = await bot.listen(m.chat.id, timeout=120)
        batch_name = input_batch.text
        await input_batch.delete()

        # Step 4: Get resolution
        await msg.edit("🖥 Enter resolution (360/480/720):")
        input_res = await bot.listen(m.chat.id, timeout=120)
        resolution = input_res.text
        await input_res.delete()

        # Step 5: Get upload channel
        await msg.edit("📤 Send channel ID where to upload (/d for current chat):")
        input_channel = await bot.listen(m.chat.id, timeout=120)
        channel_id = m.chat.id if "/d" in input_channel.text else int(input_channel.text)
        await input_channel.delete()

        await clean_temp_files()
        await msg.delete()

        # Process URLs
        success_count = 0
        for idx, url in enumerate(urls[start_index-1:], start=start_index):
            try:
                result = await process_single_url(
                    url=url,
                    index=idx,
                    resolution=resolution,
                    batch_name=batch_name,
                    channel_id=channel_id
                )
                if result:
                    success_count += 1
                await asyncio.sleep(3)  # Rate limiting
            except Exception as e:
                logger.error(f"Failed processing URL {url}: {str(e)}")
                continue

        await bot.send_message(
            channel_id,
            f"✅ Batch Complete!\nSuccessfully downloaded {success_count}/{len(urls)} files"
        )

    except Exception as e:
        logger.error(f"Master handler error: {str(e)}")
        await m.reply(f"❌ Error: {str(e)}")

async def process_single_url(url: str, index: int, resolution: str, batch_name: str, channel_id: int):
    """Process individual URL"""
    try:
        # URL processing logic
        if "visionias" in url:
            async with ClientSession() as session:
                async with session.get(url, headers=VISIONIAS_HEADERS) as resp:
                    text = await resp.text()
                    url = re.search(r"(https://.*?\.m3u8)", text).group(1)
        
        elif "classplusapp.com" in url:
            if "your_special_token" in url:  # Replace with actual token
                pattern = re.compile(r'https://videos\.classplusapp\.com/(\w+)/(\w+)\.m3u8')
                match = pattern.match(url)
                if match:
                    new_url = f"https://videos.classplusapp.com/NEW_TOKEN/{match.group(2)}.m3u8"
                    async with ClientSession() as session:
                        async with session.get(new_url, headers=CLASSPLUS_HEADERS) as resp:
                            data = await resp.json()
                            url = data['url']
        
        # Download logic
        file_name = f"{index:03d}_{batch_name[:50]}"
        cmd = f'yt-dlp -f "best[height<={resolution}]" "{url}" -o "{file_name}.mp4"'
        
        # Show progress
        progress_msg = await bot.send_message(
            channel_id,
            f"⏬ Downloading {file_name}\nResolution: {resolution}p\nURL: {url[:50]}..."
        )
        
        # Execute download
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Wait for completion
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise Exception(f"Download failed: {stderr.decode()}")
        
        # Upload file
        await bot.send_video(
            chat_id=channel_id,
            video=f"{file_name}.mp4",
            caption=f"📚 {batch_name}\n🔢 #{index}\n🔄 Resolution: {resolution}p",
            thumb="thumbnail.jpg" if os.path.exists("thumbnail.jpg") else None
        )
        
        # Cleanup
        os.remove(f"{file_name}.mp4")
        await progress_msg.delete()
        return True

    except Exception as e:
        logger.error(f"Error processing {url}: {str(e)}")
        await bot.send_message(
            channel_id,
            f"❌ Failed to process {url}\nError: {str(e)[:200]}"
        )
        return False

@bot.on_message(filters.command("clean"))
async def clean_handler(_, m: Message):
    """Clean temporary files"""
    try:
        await clean_temp_files()
        shutil.rmtree("./downloads", ignore_errors=True)
        await m.reply("✅ Successfully cleaned all temporary files!")
    except Exception as e:
        await m.reply(f"❌ Clean failed: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting Education Downloader Bot...")
    bot.run()
