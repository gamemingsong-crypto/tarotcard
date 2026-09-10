# -*- coding: utf-8 -*-
"""พ่อหมอป๊อก — Discord tarot bot with the purple cat deck."""
import asyncio
import io
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from PIL import Image, ImageDraw

import tarot_data as tarot

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
GUILD_ID = os.getenv("GUILD_ID", "").strip()
STATUS_TEXT = "ดูดวงกับพ่อหมอป๊อก l /ดูดวง"
CACHE_PATH = BASE_DIR / "data" / "daily_cache.json"
ART_DIR = BASE_DIR / "assets" / "cat_tarot"
THAI_TZ = ZoneInfo("Asia/Bangkok")
PURPLE = discord.Color.from_rgb(155, 89, 182)
REVERSED_COLOR = discord.Color.from_rgb(115, 75, 160)
logger = logging.getLogger("tarotcard")

# Order matches sheet_01.png through sheet_13.png, six cards per sheet.
MAJOR_NAMES = [
    "The Fool", "The Magician", "The High Priestess", "The Empress",
    "The Emperor", "The Hierophant", "The Lovers", "The Chariot",
    "Strength", "The Hermit", "Wheel of Fortune", "Justice",
    "The Hanged Man", "Death", "Temperance", "The Devil", "The Tower",
    "The Star", "The Moon", "The Sun", "Judgement", "The World",
]
RANKS = ["Ace", "2", "3", "4", "5", "6", "7", "8", "9", "10",
         "Page", "Knight", "Queen", "King"]
CARD_NAMES = MAJOR_NAMES + [
    f"{rank} of {suit}"
    for suit in ("Wands", "Cups", "Swords", "Pentacles")
    for rank in RANKS
]
CARD_INDEX = {name: index for index, name in enumerate(CARD_NAMES)}


def load_cache():
    try:
        result = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}


def get_or_draw_card(user_id, period, category):
    today = datetime.now(THAI_TZ)
    stamp = today.strftime("%Y-%m-%d" if period == "รายวัน" else "%Y-%m")
    key = f"{user_id}:{period}:{category}:{stamp}"
    cache = load_cache()
    entry = cache.get(key)
    if isinstance(entry, dict):
        card = next((c for c in tarot.DECK
                     if c["name_en"] == entry.get("name_en")), None)
        if (card and entry.get("orientation") in ("upright", "reversed")
                and isinstance(entry.get("advice"), str)):
            return card, entry["orientation"], entry["advice"]
    card, orientation = tarot.draw_cards(1)[0]
    advice = tarot.get_advice(category, orientation)
    cache[key] = {"name_en": card["name_en"],
                  "orientation": orientation, "advice": advice}
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = CACHE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(cache, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    temporary.replace(CACHE_PATH)
    return card, orientation, advice


def render_cards(drawn):
    """Extract the selected cards, rotate reversed cards, and build one image."""
    columns = min(len(drawn), 5)
    rows = (len(drawn) + columns - 1) // columns
    card_w, card_h, gap, label_h = 400, 600, 16, 36
    canvas = Image.new("RGB", (columns * (card_w + gap) + gap,
                               rows * (card_h + gap + label_h) + gap), "#201528")
    for number, (card, orientation) in enumerate(drawn):
        index = CARD_INDEX[card["name_en"]]
        sheet_number, cell = divmod(index, 6)
        path = ART_DIR / f"sheet_{sheet_number + 1:02d}.png"
        with Image.open(path) as sheet:
            width, height = sheet.size
            col, row = cell % 3, cell // 3
            picture = sheet.crop((round(col * width / 3), round(row * height / 2),
                                  round((col + 1) * width / 3),
                                  round((row + 1) * height / 2))).convert("RGB")
        if orientation == "reversed":
            picture = picture.transpose(Image.Transpose.ROTATE_180)
        picture.thumbnail((card_w, card_h), Image.Resampling.LANCZOS)
        x = gap + (number % columns) * (card_w + gap)
        y = gap + (number // columns) * (card_h + gap + label_h)
        canvas.paste(picture, (x + (card_w - picture.width) // 2, y))
        label = Image.new("RGB", (36, 16), "#201528")
        ImageDraw.Draw(label).text((2, 1), str(number + 1), fill="#ead6ab")
        canvas.paste(label.resize((72, 32)), (x + card_w // 2 - 36, y + card_h))
    output = io.BytesIO()
    canvas.save(output, format="JPEG", quality=88)
    output.seek(0)
    return output


async def send_reading(interaction, embed, drawn):
    # Callers have already acknowledged the interaction with defer().
    try:
        picture = await asyncio.to_thread(render_cards, drawn)
    except (OSError, KeyError, ValueError):
        logger.exception("Unable to load tarot artwork")
        await interaction.followup.send(
            content="ยังโหลดรูปไพ่ไม่ได้ แต่คำทำนายยังใช้งานได้ครับ", embed=embed)
        return
    embed.set_image(url="attachment://tarot-cards.jpg")
    attachment = discord.File(picture, filename="tarot-cards.jpg")
    try:
        await interaction.followup.send(embed=embed, file=attachment)
    finally:
        attachment.close()
        picture.close()


class TarotBot(commands.Bot):
    async def setup_hook(self):
        # Sync once at startup, not on every reconnect.
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
        else:
            synced = await self.tree.sync()
        logger.info("Synced %s slash commands", len(synced))


bot = TarotBot(
    command_prefix="!",
    intents=discord.Intents.default(),
    status=discord.Status.online,
    activity=discord.CustomActivity(name=STATUS_TEXT),
    allowed_mentions=discord.AllowedMentions.none(),
)


@bot.event
async def on_ready():
    logger.info("Logged in as %s — พร้อมดูดวงแล้ว!", bot.user)


@bot.tree.command(name="ดูดวง", description="ดูดวงรายวันหรือรายเดือนกับพ่อหมอป๊อก")
@app_commands.describe(ช่วงเวลา="เลือกช่วงเวลา", หมวดหมู่="เลือกเรื่องที่อยากดู")
@app_commands.choices(
    ช่วงเวลา=[app_commands.Choice(name=x, value=x) for x in ("รายวัน", "รายเดือน")],
    หมวดหมู่=[app_commands.Choice(name=x, value=x)
             for x in ("ภาพรวม", "การเงิน", "การงาน", "ความรัก", "สุขภาพ")],
)
async def duang(interaction: discord.Interaction,
                ช่วงเวลา: app_commands.Choice[str],
                หมวดหมู่: app_commands.Choice[str]):
    await interaction.response.defer(thinking=True)
    period, category = ช่วงเวลา.value, หมวดหมู่.value
    card, orientation, advice = get_or_draw_card(interaction.user.id, period, category)
    text = tarot.get_category_text(card, orientation, category)
    emoji = tarot.CATEGORY_INFO.get(category, {}).get("emoji", "🔮")
    embed = discord.Embed(
        title=f"{emoji} ดวง{period} — {category}",
        description=(f"{card['emoji']} **{card['name_th']}** "
                     f"({tarot.orientation_label(orientation)})\n\n{text}"),
        color=PURPLE if orientation == "upright" else REVERSED_COLOR,
    )
    embed.add_field(name="💡 คำแนะนำ", value=advice, inline=False)
    embed.set_footer(text=f"สำหรับ {interaction.user.display_name} • เพื่อความบันเทิงเท่านั้น 🎴")
    await send_reading(interaction, embed, [(card, orientation)])


@bot.tree.command(name="เปิดไพ่", description="เปิดไพ่แมว 1, 3, 5 หรือ 10 ใบ")
@app_commands.describe(จำนวน="จำนวนไพ่", คำถาม="คำถามที่อยากถาม (ไม่บังคับ)")
@app_commands.choices(จำนวน=[
    app_commands.Choice(name="1 ใบ — คำตอบตรงๆ", value=1),
    app_commands.Choice(name="3 ใบ — อดีต/ปัจจุบัน/อนาคต", value=3),
    app_commands.Choice(name="5 ใบ — ภาพรวมสถานการณ์", value=5),
    app_commands.Choice(name="10 ใบ — Celtic Cross", value=10),
])
async def open_cards(interaction: discord.Interaction,
                     จำนวน: app_commands.Choice[int],
                     คำถาม: app_commands.Range[str, 1, 1000] = None):
    await interaction.response.defer(thinking=True)
    count = จำนวน.value
    drawn = tarot.draw_cards(count)
    desc = "🐈‍⬛ สับไพ่… ให้ไพ่แมวนำทางไปกับพ่อหมอป๊อก"
    if คำถาม:
        desc += f"\n\n**คำถาม:** {discord.utils.escape_markdown(คำถาม)}"
    embed = discord.Embed(title=f"🔮 เปิดไพ่ทาโร่ {count} ใบ", description=desc, color=PURPLE)
    for index, (position, (card, orientation)) in enumerate(
            zip(tarot.SPREAD_POSITIONS[count], drawn), 1):
        embed.add_field(
            name=(f"{index}. {position} — {card['name_th']} "
                  f"({tarot.orientation_label(orientation)})"),
            value=tarot.get_meaning(card, orientation), inline=False,
        )
    embed.set_footer(text=f"เปิดไพ่โดย {interaction.user.display_name} • เพื่อความบันเทิงเท่านั้น 🎴")
    await send_reading(interaction, embed, drawn)


@bot.tree.command(name="วิธีใช้", description="วิธีดูดวงกับพ่อหมอป๊อก")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🔮 ดูดวงกับพ่อหมอป๊อก", color=PURPLE)
    embed.add_field(name="/ดูดวง [ช่วงเวลา] [หมวดหมู่]",
                    value="ดูดวงรายวัน/รายเดือน ไพ่เดิมในรอบเวลาเดียวกัน พร้อมรูปไพ่แมว",
                    inline=False)
    embed.add_field(name="/เปิดไพ่ [จำนวน] [คำถาม]",
                    value="สุ่ม 1, 3, 5 หรือ 10 ใบ รูปเรียงตามเลขคำทำนาย ไพ่กลับหัวจะหมุนตามผลสุ่ม",
                    inline=False)
    embed.set_footer(text="เพื่อความบันเทิงเท่านั้น")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.error
async def on_command_error(interaction: discord.Interaction, error):
    logger.error("Slash command failed", exc_info=(type(error), error, error.__traceback__))
    message = "เกิดข้อผิดพลาดชั่วคราว ลองใหม่อีกครั้งนะครับ"
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not TOKEN:
        raise SystemExit("ไม่พบ DISCORD_TOKEN ในไฟล์ .env")
    if GUILD_ID and not GUILD_ID.isdigit():
        raise SystemExit("GUILD_ID ต้องเป็นตัวเลข หรือปล่อยว่าง")
    bot.run(TOKEN)
