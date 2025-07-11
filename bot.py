import os
import httpx
import dotenv
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pymongo import MongoClient

dotenv.load_dotenv()

Bot = Client(
    "Pixeldrain-Bot",
    bot_token=os.environ["7535633647:AAGQbBaw4ndDVcAvglQg0xOCdwp2PJkpksQ"],
    api_id=int(os.environ["16770898"]),
    api_hash=os.environ["0fc19aa428dcceaaad4c502daf8df3ba"]
)

PIXELDRAIN_API_KEY = os.environ["073a5020-6292-47b0-9066-4cb7eba5ea39"]

START_TEXT = """Hello {},
Ready to share some media? Send a file to get a Pixeldrain stream link, or drop a Pixeldrain media ID or link to get the scoop on your file!"""

UNAUTH_TEXT = """Sorry, you are not authorized to use this bot. Please contact the bot owner for access."""

BUTTON1 = InlineKeyboardButton(text="𝘗𝘳𝘫𝘬𝘵:𝘚𝘪𝘥.", url="https://burhanverse.t.me")
BUTTON2 = InlineKeyboardButton(text="Contact Owner", url="https://aqxzaxbot.t.me")

MONGODB_URI = os.environ["mongodb+srv://Skfilter:Skfilter@skfilter.kmk96t1.mongodb.net/?retryWrites=true&w=majority"]
client = MongoClient(mongodb+srv://Skfilter:Skfilter@skfilter.kmk96t1.mongodb.net/?retryWrites=true&w=majority
)
db = client['pixeldrain_bot']
authorized_users_col = db['514177149']

# Function to check if the user is authorized
def is_authorized(user_id):
    return authorized_users_col.find_one({"user_id": user_id}) is not None

# Filter to check if the user is authorized
def authorized_user_filter(_, __, message: Message):
    return is_authorized(message.from_user.id)
    
# Handler for /start command
@Bot.on_message(filters.private & filters.command("start"))
async def start(bot, message):
    if authorized_user_filter(None, None, message):
        await message.reply_text(
            text=START_TEXT.format(message.from_user.mention),
            disable_web_page_preview=True,
            quote=True,
            reply_markup=InlineKeyboardMarkup([
            [BUTTON1, BUTTON2]
            ])
        )
    else:
        await message.reply_text(
            text=UNAUTH_TEXT,
            disable_web_page_preview=True,
            quote=True,
            reply_markup=InlineKeyboardMarkup([
            [BUTTON1, BUTTON2]
            ])
        )

# Update user information in the database
def update_user_info(user_id, username):
    authorized_users_col.update_one(
        {"user_id": user_id},
        {"$set": {"username": username}},
        upsert=True
    )

# Function to update username field in the database
async def update_username(bot, user_id):
    user_info = await bot.get_users(user_id)
    username = user_info.username or "No username"
    update_user_info(user_id, username)

# Handler for /auth command (only for the bot owner)
@Bot.on_message(filters.command("auth"))
async def auth(bot, message: Message):
    owner_id = int(os.environ["OWNER_ID"])
    if message.from_user.id == owner_id:
        try:
            if message.reply_to_message:
                user = message.reply_to_message.from_user
            else:
                user_id = int(message.command[1])
                user = await bot.get_users(user_id)
            
            user_id = user.id
            username = user.username or "No username"

            if not is_authorized(user_id):
                authorized_users_col.insert_one({"user_id": user_id, "username": username})
                await message.reply_text(f"User {user_id} (@{username}) has been authorized.")
            else:
                await update_username(bot, user_id)
                await message.reply_text(f"User {user_id} (@{username}) is already authorized.")
        except (IndexError, ValueError):
            await message.reply_text("Usage: /auth <user_id> or reply to a user's message with /auth")
    else:
        await message.reply_text("You are not authorized to use this command.")

# Handler for /auths command (only for the bot owner)
@Bot.on_message(filters.command("auths"))
async def auths(bot, message: Message):
    owner_id = int(os.environ["OWNER_ID"])
    if message.from_user.id == owner_id:
        authorized_users = authorized_users_col.find()
        text = "**Authorized Users:**\n"
        for user in authorized_users:
            user_id = user["user_id"]
            username = user.get("username", "No username")
            if username == "No username":
                await update_username(bot, user_id)
                user_info = await bot.get_users(user_id)
                username = user_info.username or "No username"
            text += f"[{user_id}](tg://user?id={user_id}) (@{username})\n"
        await message.reply_text(text, disable_web_page_preview=True)
    else:
        await message.reply_text("You are not authorized to use this command.")

# Handler for /unauth command (only for the bot owner)
@Bot.on_message(filters.command("unauth"))
async def unauth(bot, message: Message):
    owner_id = int(os.environ["OWNER_ID"])
    if message.from_user.id == owner_id:
        try:
            if message.reply_to_message:
                user_id = message.reply_to_message.from_user.id
            else:
                user_id = int(message.command[1])

            user_info = await bot.get_users(user_id)
            username = user_info.username or "No username"

            result = authorized_users_col.delete_one({"user_id": user_id})
            if result.deleted_count:
                await message.reply_text(f"User {user_id} (@{username}) has been unauthorized.")
            else:
                await message.reply_text(f"User {user_id} is not found.")
        except (IndexError, ValueError):
            await message.reply_text("Usage: /unauth <user_id> or reply to a user's message with /unauth")
    else:
        await message.reply_text("You are not authorized to use this command.")

def get_id(text):
    if text.startswith("http"):
        if text.endswith("/"):
            id = text.split("/")[-2]
        else:
            id = text.split("/")[-1]
    elif "/" not in text:
        id = text
    else:
        return None
    return id

def format_size(size):
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.2f} KB"
    else:
        return f"{size / (1024 * 1024):.2f} MB"

def format_date(date_str):
    date, time = date_str.split("T")
    time = time.split(".")[0]
    return f"{date} {time}"

async def send_data(id, message):
    # pixeldrain data
    try:
        response = requests.get(f"https://pixeldra.in/api/file/{id}/info")
        data = response.json() if response.status_code == 200 else None
    except Exception as e:
        data = None
        print(f"Error: {e}")

    if data:
        text = (
            f"**File Name:** `{data['name']}`\n"
            f"**Upload Date:** `{format_date(data['date_upload'])}`\n"
            f"**File Size:** `{format_size(data['size'])}`\n"
            f"**File Type:** `{data['mime_type']}`\n\n"
            f"\u00A9 [𝘗𝘳𝘫𝘬𝘵:𝘚𝘪𝘥.](https://burhanverse.t.me)"
        )
    else:
        text = "Failed to retrieve file information."

    reply_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="Open Link",
                    url=f"https://pixeldra.in/u/{id}"
                ),
                InlineKeyboardButton(
                    text="Direct Link",
                    url=f"https://pixeldra.in/api/file/{id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Share Link",
                    url=f"https://telegram.me/share/url?url=https://pixeldra.in/u/{id}"
                )
            ],
            [BUTTON2]
        ]
    )

    await message.edit_text(
        text=text,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

# Handler for authorized users to get pixeldrain info
@Bot.on_message(filters.private & filters.text & filters.create(authorized_user_filter))
async def info(bot, update):
    try:
        id = get_id(update.text)
        if id is None:
            return
    except:
        return

    message = await update.reply_text(
        text="`Processing...`",
        quote=True,
        disable_web_page_preview=True
    )
    await send_data(id, message)

# Handler for authorized users to upload media in private chats
@Bot.on_message(filters.private & filters.media & filters.create(authorized_user_filter))
async def media_filter(bot, update):
    await handle_media(bot, update)

async def handle_media(bot, update):
    logs = []
    message = await update.reply_text(
        text="`Processing...`",
        quote=True,
        disable_web_page_preview=True
    )

    try:
        # Download the media
        try:
            await message.edit_text(
                text="`Downloading...`",
                disable_web_page_preview=True
            )
        except:
            pass

        media = await update.download()
        logs.append("Downloaded Successfully")

        # Rename file to include user ID
        user_id = update.from_user.id
        dir_name, file_name = os.path.split(media)
        file_base, file_extension = os.path.splitext(file_name)
        renamed_file = os.path.join(dir_name, f"{file_base}_{user_id}{file_extension}")
        os.rename(media, renamed_file)
        logs.append("Renamed file successfully")

        # Upload the file
        try:
            await message.edit_text(
                text="`Downloaded Successfully, Now Uploading...`",
                disable_web_page_preview=True
            )
        except:
            pass

        # Call the chunked upload function
        response_data, upload_logs = await upload_file_stream(renamed_file, PIXELDRAIN_API_KEY)
        logs.extend(upload_logs)  # Append logs from the upload function

        if "error" in response_data:
            await message.edit_text(
                text=f"Error :- `{response_data['error']}`" + "\n\n" + '\n'.join(logs),
                disable_web_page_preview=True
            )
        else:
            await message.edit_text(
                text="`Uploaded Successfully!`",
                disable_web_page_preview=True
            )
            await send_data(response_data["id"], message)

    except Exception as error:
        await message.edit_text(
            text=f"Error :- `{error}`" + "\n\n" + '\n'.join(logs),
            disable_web_page_preview=True
        )


async def upload_file_stream(file_path, pixeldrain_api_key, chunk_size=10 * 1024 * 1024):  # 10 MB chunks
    logs = []
    try:
        # Use HTTPX for asynchronous HTTP requests
        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as file:
                # Stream file in chunks
                file_data = {"file": (os.path.basename(file_path), file, "application/octet-stream")}
                response = await client.post(
                    "https://pixeldrain.com/api/file",
                    files=file_data,
                    auth=("", pixeldrain_api_key)
                )
                response.raise_for_status()  # Check for HTTP errors

        logs.append("Uploaded Successfully")
        os.remove(file_path)  # Delete the file after successful upload
        logs.append("Removed media")

        response_data = response.json()
        return response_data, logs

    except httpx.RequestError as e:
        logs.append(f"HTTPX Request error: {str(e)}")
        return {"error": str(e)}, logs
    except Exception as e:
        logs.append(f"Unexpected error: {str(e)}")
        return {"error": str(e)}, logs
        
# Handler for unauthorized users attempting to use the bot
@Bot.on_message(filters.private & ~filters.command("start"))
async def unauthorized_user_handler(bot, message):
    if not authorized_user_filter(None, None, message):
        await message.reply_text(
            text=UNAUTH_TEXT,
            disable_web_page_preview=True,
            quote=True,
            reply_markup=InlineKeyboardMarkup([
            [BUTTON1, BUTTON2]
            ])
        )

# Handler for authorized users to use /pdup as reply to a file in groups
@Bot.on_message(filters.group & filters.reply & filters.command("pdup") & filters.create(authorized_user_filter))
async def group_upload_command(bot, message):
    replied_message = message.reply_to_message
    if replied_message and (replied_message.photo or replied_message.document or replied_message.video or replied_message.audio):
        await handle_media(bot, replied_message)
    else:
        await message.reply_text("Please reply to a valid media message with /pdup to upload.")

Bot.run()
        
