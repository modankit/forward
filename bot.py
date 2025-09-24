import asyncio
import os
import time
from telethon import TelegramClient
from telethon.errors import FloodWaitError, MessageIdInvalidError

# --- Configuration ---
api_id = 1464463
api_hash = 'ff8451462d91861a13ffd8a6bb72aa8b'
source_channel = -1002850581379
target_channel = -1003175105367
progress_message_id = 69  # existing message to show progress

message_ids = list(range(7, 1600))
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

client = TelegramClient('userbot_session', api_id, api_hash)

BATCH_SIZE = 5
BASE_DELAY = 2
RETRY_LIMIT = 3
MAX_PROGRESS_LINES = 10  # show only last 20 messages in progress message

progress_status = {}  # msg_id -> status dict


def format_progress_line(msg_id, info):
    """Return a detailed, separated progress block for a message"""
    status = info.get("status", "Pending")
    done = info.get("done", 0)
    total = info.get("total", 0)
    speed = info.get("speed", 0.0)

    # Choose emoji
    if status.startswith("Downloading") or status.startswith("Uploading"):
        emoji = "⏳"
    elif status == "Done":
        emoji = "✅"
    elif status == "Text ready":
        emoji = "📝"
    else:
        emoji = "⚠️"

    # Detailed block for downloading/uploading
    if status in ["Downloading", "Uploading"]:
        bar_length = 20
        percent = int(done / total * 100) if total else 0
        filled = int(bar_length * percent / 100)
        bar = f"[{'█'*filled}{'░'*(bar_length-filled)}]"
        line = (f"📦 Msg ID: {msg_id}\n"
                f"{emoji} Status: {status}\n"
                f"📊 Progress: {bar}\n"
                f"💾 Size: {done/1024/1024:5.2f}/{total/1024/1024:5.2f} MB\n"
                f"⚡ Speed: {speed:6.1f} KB/s\n"
                "────────────────────────────")
    else:
        # Single-line for Done/Text/Skipped
        line = f"{emoji} Msg ID: {msg_id} | {status}\n────────────────────────────"

    return line


async def download_message(client, source_entity, msg_id):
    retries = 0
    while retries < RETRY_LIMIT:
        try:
            message = await client.get_messages(source_entity, ids=msg_id)
            if not message:
                progress_status[msg_id] = {"status": "Skipped"}
                return None

            file_path = None
            caption = message.text or message.caption
            is_text = False

            if message.media:
                file_path = os.path.join(DOWNLOAD_FOLDER, f"{msg_id}")
                start_time = time.time()

                async def download_progress(current, total):
                    now = time.time()
                    elapsed = max(now - start_time, 0.001)
                    speed = current / elapsed / 1024
                    progress_status[msg_id] = {
                        "status": "Downloading",
                        "done": current,
                        "total": total,
                        "speed": speed
                    }

                file_path = await message.download_media(file=file_path, progress_callback=download_progress)
                progress_status[msg_id] = {"status": "Done", "done": 0, "total": 0, "speed": 0}
            elif message.text:
                is_text = True
                progress_status[msg_id] = {"status": "Text ready", "done": 0, "total": 0, "speed": 0}

            return (msg_id, file_path, caption, is_text)

        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 1)
            retries += 1
        except MessageIdInvalidError:
            progress_status[msg_id] = {"status": "Skipped"}
            return None
        except Exception as e:
            progress_status[msg_id] = {"status": "Error"}
            return None
    progress_status[msg_id] = {"status": "Skipped"}
    return None


async def upload_messages_in_order(client, target_entity, messages):
    for msg_id, file_path, caption, is_text in messages:
        try:
            if file_path:
                start_time = time.time()

                async def upload_progress(current, total):
                    now = time.time()
                    elapsed = max(now - start_time, 0.001)
                    speed = current / elapsed / 1024
                    progress_status[msg_id] = {
                        "status": "Uploading",
                        "done": current,
                        "total": total,
                        "speed": speed
                    }

                await client.send_file(target_entity, file_path, caption=caption, progress_callback=upload_progress)
                if os.path.exists(file_path):
                    os.remove(file_path)
                progress_status[msg_id] = {"status": "Done", "done": 0, "total": 0, "speed": 0}
            elif is_text:
                await client.send_message(target_entity, caption)
                progress_status[msg_id] = {"status": "Text ready", "done": 0, "total": 0, "speed": 0}

            await asyncio.sleep(BASE_DELAY)

        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 1)
        except Exception as e:
            progress_status[msg_id] = {"status": "Error"}


async def update_progress_message(client, target_entity):
    while True:
        sorted_items = sorted(progress_status.items())
        lines_to_show = sorted_items[-MAX_PROGRESS_LINES:]
        lines = [format_progress_line(msg_id, info) for msg_id, info in lines_to_show]

        overall = f"📊 Processed {len(progress_status)}/{len(message_ids)} messages\n"
        try:
            await client.edit_message(target_entity, progress_message_id, overall + "\n".join(lines))
        except:
            pass
        await asyncio.sleep(5)


async def main():
    source_entity = await client.get_entity(source_channel)
    target_entity = await client.get_entity(target_channel)

    progress_task = asyncio.create_task(update_progress_message(client, target_entity))

    for i in range(0, len(message_ids), BATCH_SIZE):
        batch_ids = message_ids[i:i + BATCH_SIZE]

        download_tasks = [asyncio.create_task(download_message(client, source_entity, msg_id))
                          for msg_id in batch_ids]
        downloaded = await asyncio.gather(*download_tasks)
        downloaded = [m for m in downloaded if m is not None]

        await upload_messages_in_order(client, target_entity, downloaded)

    progress_task.cancel()
    await client.edit_message(target_entity, progress_message_id, "✅ All messages processed")


if __name__ == "__main__":
    async def main_wrapper():
        async with client:
            await main()

    asyncio.run(main_wrapper())
