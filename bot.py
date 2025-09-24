import asyncio
import os
from telethon import TelegramClient
from telethon.errors import FloodWaitError, MessageIdInvalidError
from tqdm.asyncio import tqdm

# --- Configuration ---
api_id = 1464463
api_hash = 'ff8451462d91861a13ffd8a6bb72aa8b'
source_channel = -1002850581379
target_channel = -1003175105367

message_ids = list(range(7, 1600))  # adjust as needed
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

client = TelegramClient('userbot_session', api_id, api_hash)

# --- Delay between messages (seconds) ---
BASE_DELAY = 2
RETRY_LIMIT = 3


async def process_message(client, source_entity, target_entity, msg_id):
    retries = 0

    while retries < RETRY_LIMIT:
        try:
            message = await client.get_messages(source_entity, ids=msg_id)
            if not message:
                print(f"[Msg {msg_id}] Skipped (missing)")
                return

            file_path = None

            # --- Download media if present ---
            if message.media:
                file_path = os.path.join(DOWNLOAD_FOLDER, f"{msg_id}")

                async def download_progress(current, total):
                    pbar.total = total
                    pbar.n = current
                    pbar.refresh()

                with tqdm(total=0, desc=f"[Msg {msg_id}] Downloading", unit="B", unit_scale=True, leave=False) as pbar:
                    callback = lambda cur, tot: asyncio.create_task(download_progress(cur, tot))
                    file_path = await message.download_media(file=file_path, progress_callback=callback)

                print(f"[Msg {msg_id}] ✅ Downloaded")

            # --- Upload media if downloaded ---
            if file_path:
                async def upload_progress(current, total):
                    pbar.total = total
                    pbar.n = current
                    pbar.refresh()

                caption = message.text or message.caption
                with tqdm(total=0, desc=f"[Msg {msg_id}] Uploading", unit="B", unit_scale=True, leave=False) as pbar:
                    callback = lambda cur, tot: asyncio.create_task(upload_progress(cur, tot))
                    await client.send_file(target_entity, file_path, caption=caption, progress_callback=callback)

                # --- Delete file after upload ---
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"[Msg {msg_id}] ✅ File deleted after upload")
                    except Exception as e:
                        print(f"[Msg {msg_id}] ❌ Failed to delete file: {e}")

                print(f"[Msg {msg_id}] ✅ Uploaded")

            # --- Text-only messages ---
            elif message.text:
                await client.send_message(target_entity, message.text)
                print(f"[Msg {msg_id}] ✅ Text sent")

            print(f"[Msg {msg_id}] ✅ Completed")
            return  # Success, exit retry loop

        except FloodWaitError as e:
            print(f"[Msg {msg_id}] Flood wait {e.seconds}s, sleeping...")
            await asyncio.sleep(e.seconds + 1)
            retries += 1
        except MessageIdInvalidError:
            print(f"[Msg {msg_id}] Invalid or deleted")
            return
        except Exception as e:
            print(f"[Msg {msg_id}] Failed: {e}")
            return

    print(f"[Msg {msg_id}] Skipped after {RETRY_LIMIT} retries due to FloodWait")


async def copy_messages(client):
    source_entity = await client.get_entity(source_channel)
    target_entity = await client.get_entity(target_channel)

    for msg_id in message_ids:
        await process_message(client, source_entity, target_entity, msg_id)
        await asyncio.sleep(BASE_DELAY)  # Delay between messages


async def main():
    async with client:
        await copy_messages(client)


if __name__ == "__main__":
    asyncio.run(main())
