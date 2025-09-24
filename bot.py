import asyncio
import os
import time
from telethon import TelegramClient
from telethon.errors import FloodWaitError, MessageIdInvalidError

# --- Hardcoded values ---
api_id = 1464463
api_hash = 'ff8451462d91861a13ffd8a6bb72aa8b'
source_channel = -1002850581379
target_channel = -1003175105367

message_ids = list(range(7, 1600))  # adjust as needed
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

client = TelegramClient('userbot_session', api_id, api_hash)


async def process_message(client, source_entity, target_entity, msg_id):
    try:
        message = await client.get_messages(source_entity, ids=msg_id)
        if not message:
            print(f"[Msg {msg_id}] Skipped (missing)")
            return

        file_path = None

        # --- Download ---
        if message.media:
            log_msg = await client.send_message(target_entity, f"[Msg {msg_id}] Downloading 0%")
            start_time = time.time()
            last_update = 0

            async def download_progress(current, total):
                nonlocal last_update
                now = time.time()
                if now - last_update >= 1 or current == total:  # update every 1 second or on completion
                    elapsed = max(now - start_time, 0.001)
                    speed = current / elapsed / 1024  # KB/s
                    mb_done = current / (1024 * 1024)
                    mb_total = total / (1024 * 1024)
                    mb_left = mb_total - mb_done
                    percent = int(current / total * 100)
                    text = (f"[Msg {msg_id}] Downloading {percent}% | "
                            f"{mb_done:.2f}/{mb_total:.2f} MB | "
                            f"{speed:.2f} KB/s | {mb_left:.2f} MB left")
                    await log_msg.edit(text)
                    last_update = now

            file_path = os.path.join(DOWNLOAD_FOLDER, f"{msg_id}")
            file_path = await message.download_media(file=file_path, progress_callback=download_progress)
            await log_msg.delete()
            print(f"[Msg {msg_id}] ✅ Downloaded")

        # --- Upload ---
        if file_path:
            log_msg = await client.send_message(target_entity, f"[Msg {msg_id}] Uploading 0%")
            start_time = time.time()
            last_update = 0

            async def upload_progress(current, total):
                nonlocal last_update
                now = time.time()
                if now - last_update >= 1 or current == total:  # update every 1 second or on completion
                    elapsed = max(now - start_time, 0.001)
                    speed = current / elapsed / 1024  # KB/s
                    mb_done = current / (1024 * 1024)
                    mb_total = total / (1024 * 1024)
                    mb_left = mb_total - mb_done
                    percent = int(current / total * 100)
                    text = (f"[Msg {msg_id}] Uploading {percent}% | "
                            f"{mb_done:.2f}/{mb_total:.2f} MB | "
                            f"{speed:.2f} KB/s | {mb_left:.2f} MB left")
                    await log_msg.edit(text)
                    last_update = now

            await client.send_file(target_entity, file_path, caption=message.text, progress_callback=upload_progress)
            await log_msg.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
            print(f"[Msg {msg_id}] ✅ Uploaded")

        elif message.text:
            log_msg = await client.send_message(target_entity, f"[Msg {msg_id}] Sending text...")
            await client.send_message(target_entity, message.text)
            await log_msg.delete()
            print(f"[Msg {msg_id}] ✅ Text sent")

        print(f"[Msg {msg_id}] ✅ Completed")

    except FloodWaitError as e:
        print(f"[Msg {msg_id}] Flood wait {e.seconds}s")
        await asyncio.sleep(e.seconds)
        return await process_message(client, source_entity, target_entity, msg_id)
    except MessageIdInvalidError:
        print(f"[Msg {msg_id}] Invalid or deleted")
    except Exception as e:
        print(f"[Msg {msg_id}] Failed: {e}")


async def copy_messages(client):
    source_entity = await client.get_entity(source_channel)
    target_entity = await client.get_entity(target_channel)

    for msg_id in message_ids:
        await process_message(client, source_entity, target_entity, msg_id)
        await asyncio.sleep(1)  # small delay between messages to respect Telegram ToS


async def main():
    async with client:
        await copy_messages(client)


if __name__ == "__main__":
    asyncio.run(main())
