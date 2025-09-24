import asyncio
import os
import time
from telethon import TelegramClient
from telethon.errors import FloodWaitError, MessageIdInvalidError
from tqdm import tqdm

api_id = 1464463
api_hash = 'ff8451462d91861a13ffd8a6bb72aa8b'

source_channel = -1002850581379
target_channel = -1003175105367
message_ids = list(range(7, 20))  # test small first
DOWNLOAD_FOLDER = "downloads"

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

client = TelegramClient(
    'userbot_session',
    api_id,
    api_hash,
    connection_retries=None,
    request_retries=10,
    timeout=60
)

# Pretty tqdm progress bar
class ProgressBar:
    def __init__(self, msg_id, action, total=0):
        self.msg_id = msg_id
        self.bar = tqdm(
            total=total,
            desc=f"[Msg {msg_id}] {action}",
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            leave=True,
            position=0,
            dynamic_ncols=True,
        )
        self.total = total

    def __call__(self, current, total):
        if self.total != total:
            self.bar.total = total
            self.total = total
        self.bar.n = current
        self.bar.refresh()

    def close(self):
        self.bar.close()

async def process_message(client, source_entity, target_entity, msg_id):
    try:
        message = await client.get_messages(source_entity, ids=msg_id)
        if message is None:
            print(f"[Msg {msg_id}] Skipped (missing)")
            return

        file_path = None

        # --- Download ---
        if message.media:
            pb = ProgressBar(msg_id, "Downloading")
            start = time.time()
            file_path = os.path.join(DOWNLOAD_FOLDER, f"{msg_id}")
            file_path = await message.download_media(file=file_path, progress_callback=pb)
            elapsed = time.time() - start
            pb.close()
            print(f"[Msg {msg_id}] ✅ Downloaded in {elapsed:.2f}s")

        # --- Upload ---
        if file_path:
            pb = ProgressBar(msg_id, "Uploading")
            start = time.time()
            await client.send_file(target_entity, file_path, caption=message.text, progress_callback=pb)
            elapsed = time.time() - start
            pb.close()
            print(f"[Msg {msg_id}] ✅ Uploaded in {elapsed:.2f}s")
            if os.path.exists(file_path):
                os.remove(file_path)

        elif message.text:
            await client.send_message(target_entity, message.text)
            print(f"[Msg {msg_id}] ✅ Text sent")

        print(f"[Msg {msg_id}] 🎉 Completed")

    except FloodWaitError as e:
        print(f"[Msg {msg_id}] ⏳ Flood wait {e.seconds}s")
        await asyncio.sleep(e.seconds)
        return await process_message(client, source_entity, target_entity, msg_id)

    except MessageIdInvalidError:
        print(f"[Msg {msg_id}] ❌ Invalid or deleted")
    except Exception as e:
        print(f"[Msg {msg_id}] ❌ Failed: {e}")

async def copy_messages(client):
    source_entity = await client.get_entity(source_channel)
    target_entity = await client.get_entity(target_channel)

    print("✅ Channels resolved")
    for msg_id in message_ids:
        await process_message(client, source_entity, target_entity, msg_id)
        # optional delay
        await asyncio.sleep(1)

async def main():
    async with client:
        await copy_messages(client)

if __name__ == "__main__":
    asyncio.run(main())
