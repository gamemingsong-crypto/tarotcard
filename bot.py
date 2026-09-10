# -*- coding: utf-8 -*-
"""
bot.py
บอทดูดวงไพ่ทาโร่สำหรับ Discord
คำสั่งหลัก:
  /ดวง       - ดูดวงรายวัน/รายเดือน แยกตามหมวด (ภาพรวม/การเงิน/การงาน/ความรัก/สุขภาพ)
  /เปิดไพ่    - สุ่มเปิดไพ่ 1 / 3 / 5 / 10 ใบ สำหรับถามคำถามอะไรก็ได้
  /วิธีใช้    - แสดงคำแนะนำการใช้งานบอท
"""

import os
import json
import random
from datetime import date

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

import tarot_data as tarot

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")  # ใส่ไว้ตอนทดสอบเพื่อให้ sync คำสั่งไวขึ้น (ไม่บังคับ)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE_PATH = os.path.join(DATA_DIR, "daily_cache.json")

COLOR_UPRIGHT = discord.Color.from_rgb(155, 89, 182)   # ม่วง
COLOR_REVERSED = discord.Color.from_rgb(230, 126, 34)  # ส้ม

INTRO_LINES = [
    "🔮 สับไพ่... จั่วไพ่... นี่คือสิ่งที่จักรวาลอยากบอกคุณวันนี้",
    "🃏 ไพ่ใบนี้เลือกคุณแล้ว...",
    "✨ ให้ไพ่นำทางสักครู่นะ...",
]


# ---------------------------------------------------------
# Cache สำหรับดวงรายวัน/รายเดือน (กันไม่ให้สุ่มใหม่ทุกครั้งที่เรียกซ้ำ)
# ---------------------------------------------------------
def load_cache() -> dict:
    if not os.path.exists(CACHE_PATH):
        return {}
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_cache(cache: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def period_key(period: str) -> str:
    today = date.today()
    if period == "รายวัน":
        return today.isoformat()
    return f"{today.year}-{today.month:02d}"  # รายเดือน


def get_or_draw_card(user_id: int, period: str, category: str):
    """คืนไพ่เดิมถ้าเคยจั่วไปแล้วในรอบเวลานั้น ไม่งั้นจั่วใหม่แล้วบันทึก"""
    cache = load_cache()
    key = f"{user_id}:{period}:{category}:{period_key(period)}"

    if key in cache:
        entry = cache[key]
        card = next((c for c in tarot.DECK if c["name_en"] == entry["name_en"]), None)
        if card:
            return card, entry["orientation"], entry["advice"]

    card, orientation = tarot.draw_cards(1)[0]
    advice = tarot.get_advice(category, orientation)
    cache[key] = {"name_en": card["name_en"], "orientation": orientation, "advice": advice}
    save_cache(cache)
    return card, orientation, advice


# ---------------------------------------------------------
# Discord bot setup
# ---------------------------------------------------------
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    try:
        if GUILD_ID:
            guild_obj = discord.Object(id=int(GUILD_ID))
            bot.tree.copy_global_to(guild=guild_obj)
            synced = await bot.tree.sync(guild=guild_obj)
        else:
            synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"⚠️ Sync error: {e}")
    print(f"✅ Logged in as {bot.user} — พร้อมดูดวงแล้ว!")


# ---------------------------------------------------------
# /ดวง — ดวงรายวัน/รายเดือน แยกตามหมวด
# ---------------------------------------------------------
@bot.tree.command(name="ดวง", description="ดูดวงรายวันหรือรายเดือน แยกตามหมวดที่สนใจ")
@app_commands.describe(ช่วงเวลา="เลือกดวงรายวันหรือรายเดือน", หมวดหมู่="หมวดที่อยากดู")
@app_commands.choices(
    ช่วงเวลา=[
        app_commands.Choice(name="รายวัน", value="รายวัน"),
        app_commands.Choice(name="รายเดือน", value="รายเดือน"),
    ],
    หมวดหมู่=[
        app_commands.Choice(name="ภาพรวม", value="ภาพรวม"),
        app_commands.Choice(name="การเงิน", value="การเงิน"),
        app_commands.Choice(name="การงาน", value="การงาน"),
        app_commands.Choice(name="ความรัก", value="ความรัก"),
        app_commands.Choice(name="สุขภาพ", value="สุขภาพ"),
    ],
)
async def duang(interaction: discord.Interaction,
                 ช่วงเวลา: app_commands.Choice[str],
                 หมวดหมู่: app_commands.Choice[str]):
    period = ช่วงเวลา.value
    category = หมวดหมู่.value

    card, orientation, advice = get_or_draw_card(interaction.user.id, period, category)
    text = tarot.get_category_text(card, orientation, category)
    cat_emoji = tarot.CATEGORY_INFO.get(category, {}).get("emoji", "🔮")

    embed = discord.Embed(
        title=f"{cat_emoji} ดวง{period} — {category}",
        description=f"{card['emoji']} **{card['name_th']}** ({tarot.orientation_label(orientation)})\n\n{text}",
        color=COLOR_UPRIGHT if orientation == "upright" else COLOR_REVERSED,
    )
    embed.add_field(name="💡 คำแนะนำ", value=advice, inline=False)
    embed.set_footer(text=f"สำหรับ {interaction.user.display_name} • เพื่อความบันเทิงเท่านั้น 🎴")

    await interaction.response.send_message(embed=embed)


# ---------------------------------------------------------
# /เปิดไพ่ — สุ่มเปิดไพ่ 1 / 3 / 5 / 10 ใบ
# ---------------------------------------------------------
@bot.tree.command(name="เปิดไพ่", description="สุ่มเปิดไพ่ทาโร่ 1, 3, 5 หรือ 10 ใบ เพื่อถามคำถามอะไรก็ได้")
@app_commands.describe(จำนวน="จำนวนไพ่ที่ต้องการเปิด", คำถาม="คำถามที่อยากถามไพ่ (ไม่บังคับ)")
@app_commands.choices(
    จำนวน=[
        app_commands.Choice(name="1 ใบ — คำตอบตรงๆ", value=1),
        app_commands.Choice(name="3 ใบ — อดีต/ปัจจุบัน/อนาคต", value=3),
        app_commands.Choice(name="5 ใบ — ภาพรวมสถานการณ์", value=5),
        app_commands.Choice(name="10 ใบ — Celtic Cross (ละเอียดสุด)", value=10),
    ]
)
async def open_cards(interaction: discord.Interaction,
                      จำนวน: app_commands.Choice[int],
                      คำถาม: str = None):
    count = จำนวน.value
    positions = tarot.SPREAD_POSITIONS[count]
    drawn = tarot.draw_cards(count)

    intro = random.choice(INTRO_LINES)
    desc = intro
    if คำถาม:
        desc += f"\n\n**คำถาม:** {คำถาม}"

    embed = discord.Embed(
        title=f"🔮 เปิดไพ่ทาโร่ {count} ใบ",
        description=desc,
        color=discord.Color.from_rgb(142, 68, 173),
    )

    for pos, (card, orientation) in zip(positions, drawn):
        meaning = tarot.get_meaning(card, orientation)
        field_name = f"{card['emoji']} {pos} — {card['name_th']} ({tarot.orientation_label(orientation)})"
        embed.add_field(name=field_name, value=meaning, inline=False)

    embed.set_footer(text=f"เปิดไพ่โดย {interaction.user.display_name} • เพื่อความบันเทิงเท่านั้น 🎴")
    await interaction.response.send_message(embed=embed)


# ---------------------------------------------------------
# /วิธีใช้ — คำแนะนำการใช้งาน
# ---------------------------------------------------------
@bot.tree.command(name="วิธีใช้", description="แสดงวิธีใช้งานบอทดูดวงไพ่ทาโร่")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🔮 วิธีใช้บอทดูดวงไพ่ทาโร่",
        color=discord.Color.from_rgb(52, 152, 219),
    )
    embed.add_field(
        name="/ดวง [ช่วงเวลา] [หมวดหมู่]",
        value="ดูดวงรายวันหรือรายเดือน เลือกได้ว่าจะดูภาพรวม การเงิน การงาน ความรัก หรือสุขภาพ\n"
              "(ดวงเดิมจะไม่เปลี่ยนถ้าเรียกซ้ำในวัน/เดือนเดียวกัน)",
        inline=False,
    )
    embed.add_field(
        name="/เปิดไพ่ [จำนวน] [คำถาม]",
        value="สุ่มเปิดไพ่ 1, 3, 5 หรือ 10 ใบ เพื่อถามคำถามอะไรก็ได้ ทุกครั้งที่เรียกจะสุ่มใหม่เสมอ",
        inline=False,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("❌ ไม่พบ DISCORD_TOKEN — โปรดตั้งค่าในไฟล์ .env ก่อนรันบอท")
    bot.run(TOKEN)
