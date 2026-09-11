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
STATUS_TEXT = "ดูดวงกับพ่อหมอป๊อก | /ดูดวง"
FOOTER_TEXT = "ความเชื่อส่วนบุคคล โปรดใช้วิจารณญาณในการอ่าน"
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


# Authored symbolic readings; no external AI service or claim of certainty.
# name | upright outlook | upright action | reversed outlook | reversed action
_READING_ROWS = """
The Fool|คุณอาจได้ลองเส้นทางที่ไม่คุ้นเคย แม้ยังไม่รู้ผลทั้งหมด การเริ่มเล็ก ๆ จะทำให้เห็นทางต่อ|เลือกก้าวแรกที่ย้อนกลับได้ก่อน|การรีบกระโดดเข้าเรื่องใหม่อาจทำให้ต้องกลับมาแก้รายละเอียดที่ตกหล่น|เช็กข้อมูลและข้อจำกัดก่อนตกลง
The Magician|สิ่งที่คุณมีอยู่แล้วอาจเพียงพอให้แผนเริ่มเดินหน้า คนอื่นจะเห็นศักยภาพเมื่อคุณลงมือให้ดู|นำทักษะที่ถนัดมาแก้ปัญหาหนึ่งเรื่อง|คำพูดหรือแผนอาจดูดีเกินสิ่งที่ทำได้จริง ทำให้ความคาดหวังไม่ตรงกัน|ขอดูหลักฐานและกำหนดสิ่งที่จะทำให้ชัด
The High Priestess|คำตอบอาจยังไม่ปรากฏครบ การสังเกตรายละเอียดเงียบ ๆ จะมีประโยชน์กว่าการเร่งเอาคำตอบ|เว้นเวลาให้ตัวเองคิดก่อนตอบรับ|ข้อมูลที่คุณมองข้ามอาจทำให้ตีความสถานการณ์คลาดเคลื่อน|แยกสิ่งที่รู้จริงออกจากสิ่งที่คิดไปเอง
The Empress|สิ่งที่คุณใส่ใจต่อเนื่องอาจเริ่มเติบโต บรรยากาศที่เกื้อกูลจะช่วยให้แผนไปต่อได้|ดูแลทั้งสิ่งที่ทำและกำลังของตัวเอง|การดูแลทุกคนจนเกินกำลังอาจทำให้สิ่งที่คุณต้องการถูกเลื่อนออกไป|แบ่งเวลาและขอบเขตให้ตัวเองด้วย
The Emperor|สถานการณ์มีแนวโน้มจัดการได้ดีขึ้นเมื่อคุณกำหนดกติกาและความรับผิดชอบให้ชัด|วางแผนที่ทำตามได้จริง|การพยายามควบคุมทุกรายละเอียดอาจทำให้คนรอบตัวอึดอัดและงานติดขัด|ยอมให้มีวิธีทำที่ต่างจากของคุณ
The Hierophant|คำแนะนำจากผู้มีประสบการณ์อาจช่วยให้คุณหลีกเลี่ยงการลองผิดซ้ำเดิม|ถามเหตุผลเบื้องหลังแนวทางที่ได้รับ|กติกาเดิมอาจไม่เหมาะกับโจทย์ที่คุณเจอทั้งหมด คุณอาจต้องหาวิธีของตัวเอง|ปรับวิธีโดยไม่ละเลยความรับผิดชอบ
The Lovers|คุณอาจต้องเลือกสิ่งที่สอดคล้องกับคุณค่าของตัวเอง การคุยอย่างจริงใจช่วยให้ตัดสินใจร่วมกันได้|บอกความต้องการและฟังอีกฝ่ายให้ครบ|ความต้องการที่ไม่ตรงกันอาจทำให้คุณลังเลหรือสื่อสารสวนทางกัน|คุยเรื่องที่เห็นต่างก่อนให้คำมั่น
The Chariot|เรื่องที่ตั้งใจมีแนวโน้มเดินหน้าเมื่อคุณเลือกทิศทางเดียวและรักษาวินัย|กำหนดเป้าหมายหลักให้ชัด|หลายแรงดึงอาจทำให้คุณเสียทิศและเร่งโดยไม่รู้ว่าจะไปไหน|ลดเป้าหมายที่แข่งขันกันลง
Strength|สถานการณ์ตึงเครียดอาจคลี่คลายได้ด้วยความนิ่งและการตอบอย่างอ่อนโยน|ใช้ความอดทนแทนการเอาชนะทันที|ความไม่มั่นใจอาจทำให้คุณกดดันตัวเองมากกว่าสถานการณ์จริง|แบ่งเรื่องยากเป็นขั้นเล็ก ๆ
The Hermit|การถอยมาทบทวนอาจทำให้คุณเห็นคำตอบที่เสียงรอบตัวเคยกลบไว้|ให้เวลาตัวเองคิดอย่างมีจุดหมาย|การเก็บทุกอย่างไว้คนเดียวอาจทำให้มองไม่เห็นทางเลือกอื่น|ขอความเห็นจากคนที่ไว้ใจได้
Wheel of Fortune|จังหวะบางอย่างอาจเปลี่ยนและเปิดทางเลือกใหม่ ความยืดหยุ่นจะช่วยให้คุณรับมือได้|เตรียมแผนเผื่อความเปลี่ยนแปลง|สิ่งที่ควบคุมไม่ได้อาจทำให้กำหนดการสะดุด แต่คุณยังปรับวิธีตอบสนองได้|โฟกัสส่วนที่คุณจัดการได้
Justice|เรื่องที่ค้างอาจต้องตัดสินจากข้อเท็จจริงและข้อตกลงที่ชัดเจน|ตรวจรายละเอียดก่อนสรุป|การมองข้อมูลเพียงด้านเดียวอาจทำให้ตัดสินอย่างไม่เป็นธรรม|ฟังให้ครบก่อนตัดสินคนหรือเรื่อง
The Hanged Man|เรื่องอาจยังไม่เดินตามจังหวะที่หวัง การเปลี่ยนมุมมองช่วยให้เห็นทางที่เคยมองข้าม|ใช้ช่วงรอทบทวนวิธีเดิม|คุณอาจเสียเวลากับการรอที่ไม่มีเงื่อนไขจบชัดเจน|กำหนดว่าจะรอถึงเมื่อไรแล้วปรับแผน
Death|บทบาทหรือรูปแบบเดิมอาจถึงเวลาปิด เพื่อเปิดพื้นที่ให้วิธีใหม่ที่เหมาะกว่า|เลือกสิ่งที่ควรปล่อยอย่างมีสติ|การยื้อสิ่งที่หมดหน้าที่แล้วอาจทำให้คุณเดินต่อได้ยาก|เริ่มเปลี่ยนทีละส่วนที่พร้อม
Temperance|ความคืบหน้าอาจมาอย่างค่อยเป็นค่อยไป การประสานวิธีที่ต่างกันช่วยให้ลงตัว|รักษาจังหวะที่ทำต่อเนื่องได้|การทุ่มด้านหนึ่งมากเกินไปอาจทำให้ส่วนอื่นเสียสมดุล|ปรับตารางและความคาดหวังให้พอดี
The Devil|ความอยากหรือความผูกติดอาจมีอิทธิพลต่อการตัดสินใจมากกว่าที่คุณคิด|สังเกตสิ่งที่ทำให้รู้สึกว่าเลือกไม่ได้|คุณอาจเริ่มเห็นทางออกจากรูปแบบที่ทำให้รู้สึกติดอยู่|ตั้งขอบเขตหนึ่งข้อที่ทำได้จริง
The Tower|ข้อมูลหรือเหตุการณ์ที่ไม่คาดอาจทำให้ต้องปรับแผนเดิมอย่างรวดเร็ว|จัดการเรื่องจำเป็นก่อนและเผื่อทางเลือก|ปัญหาที่เลื่อนการจัดการไว้อาจยังรบกวนอยู่ แม้ภายนอกดูสงบ|แก้จุดเปราะบางทีละจุด
The Star|หลังช่วงที่ท้อ คุณอาจเริ่มเห็นเหตุผลที่จะลองอีกครั้ง ความคืบหน้าเล็ก ๆ ช่วยคืนความหวัง|ตั้งเป้าหมายเล็กที่วัดผลได้|การยังไม่เห็นผลอาจทำให้คุณหมดใจทั้งที่มีบางส่วนคืบหน้า|ทบทวนสิ่งที่ทำสำเร็จแล้วก่อนตัดสินตัวเอง
The Moon|สถานการณ์อาจยังคลุมเครือ ทำให้ความกังวลเติมช่องว่างแทนข้อมูลจริง|ถามให้ชัดแทนการเดา|เรื่องที่เคยสับสนอาจเริ่มแยกแยะได้เมื่อคุณตรวจสอบข้อมูล|ยืนยันสิ่งที่เข้าใจก่อนเดินหน้าต่อ
The Sun|คุณอาจได้เห็นผลลัพธ์ที่ทำให้มั่นใจขึ้น และการสื่อสารอย่างเปิดเผยช่วยลดความอึดอัด|ยอมรับความสำเร็จโดยไม่ละเลยรายละเอียด|สิ่งที่หวังอาจคืบหน้าช้ากว่าภาพที่วางไว้ แต่ยังมีส่วนดีให้ต่อยอด|ปรับความคาดหวังให้ตรงกับความคืบหน้า
Judgement|เรื่องเดิมอาจกลับมาให้คุณทบทวนและเลือกวิธีตอบที่ต่างไปจากครั้งก่อน|ใช้บทเรียนแทนการโทษตัวเอง|ความกลัวการตัดสินอาจทำให้คุณเลื่อนการตัดสินใจที่จำเป็น|แยกคำวิจารณ์ที่มีประโยชน์ออกจากแรงกดดัน
The World|งานหรือวงจรหนึ่งอาจใกล้ครบถ้วน คุณมีโอกาสเห็นภาพรวมของสิ่งที่ทำมา|ปิดรายละเอียดที่เหลือให้เรียบร้อย|เรื่องที่ดูใกล้เสร็จอาจยังมีจุดค้าง ทำให้คุณรู้สึกไปต่อไม่ได้|ระบุสิ่งที่ยังไม่จบให้เป็นรายการ
Ace of Wands|ไอเดียหรือแรงบันดาลใจใหม่อาจทำให้คุณอยากเริ่มลงมืออีกครั้ง|ทดลองทำต้นแบบเล็ก ๆ|ไฟเริ่มต้นอาจสะดุดเพราะยังไม่รู้ว่าจะเริ่มตรงไหน|เลือกสิ่งแรกที่ทำได้ภายในเวลาสั้น ๆ
2 of Wands|คุณอาจได้มองทางเลือกที่ไกลกว่าความคุ้นเคย แต่ยังต้องเลือกว่าจะต่อยอดทางใด|เปรียบเทียบทางเลือกด้วยเป้าหมายเดียวกัน|ความกลัวพลาดอาจทำให้คุณวนอยู่กับแผนโดยยังไม่เลือก|หาข้อมูลส่วนที่จำเป็นต่อการตัดสินใจ
3 of Wands|สิ่งที่เริ่มไว้มีแนวโน้มขยายออกไปเมื่อคุณประสานกับคนหรือโอกาสใหม่|เตรียมรับงานต่อจากขั้นที่เริ่มแล้ว|ความคืบหน้าอาจช้าจากการประสานงานหรือการคาดการณ์ที่กว้างเกินไป|ทบทวนกำหนดเวลาและผู้รับผิดชอบ
4 of Wands|คุณอาจมีจังหวะได้ฉลองหมุดหมายเล็ก ๆ หรือรู้สึกว่ามีคนร่วมทาง|ให้คุณค่ากับทีมและพื้นที่ที่ทำให้สบายใจ|ความคาดหวังของกลุ่มหรือคนใกล้ชิดอาจไม่ตรงกัน|ตกลงเรื่องร่วมกันก่อนจัดแผนใหญ่
5 of Wands|หลายความเห็นอาจชนกันจนคุณต้องใช้พลังกับการแข่งขันมากกว่าตัวงาน|กำหนดโจทย์ร่วมก่อนถกวิธี|ความขัดแย้งอาจเบาลง แต่เรื่องที่หลบเลี่ยงยังต้องพูดให้ชัด|ตกลงวิธีคุยโดยไม่โจมตีกัน
6 of Wands|ความพยายามอาจได้รับการยอมรับและช่วยให้คุณกล้าแสดงผลงานมากขึ้น|ให้เครดิตคนที่มีส่วนร่วมด้วย|การรอคำชมอาจทำให้คุณมองไม่เห็นคุณค่าของผลงานตัวเอง|ใช้เกณฑ์ที่ชัดเจนวัดความคืบหน้า
7 of Wands|คุณอาจต้องยืนยันจุดยืนท่ามกลางข้อเรียกร้องหลายด้าน|เลือกเรื่องที่ควรยืนหยัดจริง ๆ|การรับมือทุกข้อท้าทายอาจทำให้คุณเหนื่อยจนเสียหลัก|ลดการต่อสู้ที่ไม่จำเป็น
8 of Wands|ข่าวสารหรือความคืบหน้าอาจมาเร็ว ทำให้ต้องตอบและจัดลำดับอย่างทันจังหวะ|ยืนยันข้อมูลสำคัญก่อนส่งต่อ|การสื่อสารอาจล่าช้าหรือคลาดเคลื่อน ทำให้แผนต้องขยับ|ตรวจข้อความและกำหนดการซ้ำ
9 of Wands|คุณอาจใกล้ผ่านช่วงยาก แต่ประสบการณ์เดิมทำให้ยังระวังตัวมาก|พักเป็นช่วงและรักษาขอบเขต|ความเหนื่อยสะสมอาจทำให้เรื่องเล็กดูเป็นภาระใหญ่|ขอแบ่งหน้าที่ก่อนฝืนต่อ
10 of Wands|หน้าที่หลายอย่างอาจมารวมที่คุณจนความคืบหน้าแลกด้วยความหนักใจ|แบ่งงานและตัดสิ่งที่ไม่จำเป็น|คุณอาจเริ่มคืนภาระที่ไม่ใช่ของตัวเอง หรือจำเป็นต้องยอมรับว่ารับไม่ไหว|คุยเรื่องกำลังและความรับผิดชอบตรง ๆ
Page of Wands|ความอยากลองอาจพาคุณไปเจอเรื่องที่จุดประกายความสนใจ|เรียนรู้ผ่านการทดลองที่มีขอบเขต|ไอเดียมีมากแต่ยังขาดแผน ทำให้เริ่มหลายเรื่องแล้วค้าง|เลือกหนึ่งเรื่องมาทำให้จบก่อน
Knight of Wands|ความกล้าอาจพาให้เรื่องเดินหน้าเร็ว แต่ต้องมีคนหรือระบบช่วยเก็บรายละเอียด|เร่งในส่วนที่พร้อมและตรวจส่วนเสี่ยง|การตัดสินใจตามอารมณ์ชั่ววูบอาจทำให้ต้องกลับมาแก้|เว้นจังหวะก่อนรับปาก
Queen of Wands|ความมั่นใจและความเป็นตัวเองอาจช่วยให้คุณดึงคนมาร่วมมือได้|แสดงจุดแข็งโดยเปิดพื้นที่ให้ผู้อื่น|การเปรียบเทียบตัวเองกับคนอื่นอาจบั่นทอนความมั่นใจ|กลับมาโฟกัสสิ่งที่คุณควบคุมได้
King of Wands|คุณอาจอยู่ในจังหวะวางทิศทางและชวนคนร่วมทำให้เป็นจริง|สื่อสารภาพใหญ่พร้อมขั้นตอนถัดไป|การเร่งให้ทุกคนตามทันภาพในหัวอาจสร้างแรงกดดัน|รับฟังข้อจำกัดก่อนกำหนดเป้า
Ace of Cups|คุณอาจเปิดรับความรู้สึกใหม่หรือพบพื้นที่ที่ทำให้ใจอ่อนโยนขึ้น|สื่อสารความรู้สึกอย่างไม่เร่งรัด|ความรู้สึกที่เก็บไว้อาจทำให้คุณรับสิ่งดี ๆ ได้ไม่เต็มที่|ให้เวลาทำความเข้าใจความต้องการตัวเอง
2 of Cups|การรับฟังกันอาจนำไปสู่ความเข้าใจหรือข้อตกลงที่ทั้งสองฝ่ายพอใจ|ตรวจว่าความต้องการตรงกันจริงหรือไม่|ความใกล้ชิดอาจสะดุดเพราะการให้และรับไม่เท่ากัน|คุยขอบเขตและความคาดหวังให้ชัด
3 of Cups|แรงสนับสนุนจากเพื่อนหรือกลุ่มอาจช่วยให้คุณผ่านเรื่องที่หนักใจง่ายขึ้น|เลือกใช้เวลากับคนที่เกื้อกูล|ความเห็นของคนรอบข้างอาจทำให้คุณสับสนกับความรู้สึกตัวเอง|แยกเรื่องของคุณออกจากเสียงของกลุ่ม
4 of Cups|คุณอาจไม่รู้สึกสนใจกับทางเลือกที่มี แม้บางทางยังมีสิ่งที่มองข้าม|พักแล้วพิจารณาข้อเสนออีกครั้ง|คุณอาจเริ่มอยากกลับมามีส่วนร่วมหลังจากเก็บตัวหรือเบื่อหน่าย|เปิดรับทางเลือกทีละอย่าง
5 of Cups|ความผิดหวังอาจดึงสายตาคุณไปที่สิ่งที่เสีย จนลืมสิ่งที่ยังพอใช้ต่อได้|ยอมรับความรู้สึกแล้วมองสิ่งที่ยังเหลือ|คุณอาจเริ่มวางความเสียใจและเห็นทางเดินต่อที่เป็นไปได้|ให้โอกาสตัวเองเริ่มโดยไม่ต้องลืมทุกอย่าง
6 of Cups|คนหรือบรรยากาศคุ้นเคยอาจทำให้คุณกลับมาทบทวนสิ่งที่มีความหมาย|รับความอบอุ่นโดยมองปัจจุบันตามจริง|ภาพอดีตอาจทำให้คุณเปรียบเทียบปัจจุบันอย่างไม่เป็นธรรม|ถามว่าสิ่งเดิมยังเหมาะกับคุณตอนนี้ไหม
7 of Cups|ตัวเลือกที่ดูน่าสนใจหลายอย่างอาจทำให้คุณเลือกยากหรือคาดหวังเกินข้อมูล|แยกสิ่งที่ทำได้จริงออกจากภาพฝัน|เมื่อคุณตัดตัวเลือกที่ไม่ตรงเป้าออก เส้นทางอาจเริ่มชัดขึ้น|เลือกด้วยข้อเท็จจริงที่ตรวจสอบได้
8 of Cups|คุณอาจเริ่มรู้ว่าสิ่งที่คุ้นเคยไม่ตอบโจทย์ใจเท่าเดิม และอยากหาความหมายใหม่|ทบทวนสิ่งที่ขาดก่อนตัดสินใจเดินออก|ความลังเลอาจทำให้คุณอยู่ต่อทั้งที่ยังไม่รู้ว่ากำลังรออะไร|กำหนดเงื่อนไขที่ทำให้อยากอยู่หรือไป
9 of Cups|คุณอาจมีโอกาสพอใจกับสิ่งที่ทำสำเร็จหรือได้รับสิ่งเล็ก ๆ ที่ต้องการ|ฉลองอย่างพอดีและเห็นคุณค่าปัจจุบัน|สิ่งที่ได้มาอาจไม่เติมใจอย่างที่คาด ทำให้ต้องทบทวนความต้องการจริง|ถามตัวเองว่าอยากได้สิ่งนั้นเพราะอะไร
10 of Cups|การคุยเรื่องอนาคตร่วมกันอาจช่วยให้คุณเห็นภาพความสุขที่เป็นไปได้|สร้างข้อตกลงที่ทุกคนมีส่วนร่วม|ภาพความสุขที่คาดไว้อาจไม่ตรงความต้องการของทุกคน|เปิดพื้นที่ให้พูดเรื่องที่ยังไม่ลงตัว
Page of Cups|ข้อความหรือการแสดงความรู้สึกเล็ก ๆ อาจเปิดบทสนทนาที่ดี|ตอบด้วยความจริงใจโดยไม่ตีความไกล|คุณอาจตีความสัญญาณเล็ก ๆ ตามความหวังมากกว่าสิ่งที่เกิดขึ้นจริง|ถามให้ชัดและค่อย ๆ รู้จักกัน
Knight of Cups|คุณอาจได้รับคำชวนหรือแรงบันดาลใจที่ทำให้อยากเดินตามความรู้สึก|ดูการกระทำควบคู่กับคำพูด|คำพูดที่น่าประทับใจอาจยังไม่ตามด้วยความสม่ำเสมอ|ให้เวลาพิสูจน์ก่อนคาดหวังมาก
Queen of Cups|การรับฟังอย่างเข้าใจอาจช่วยให้คุณและคนใกล้ตัวพูดสิ่งที่เก็บไว้ได้|ดูแลใจตัวเองขณะรับฟังผู้อื่น|คุณอาจรับอารมณ์ของคนอื่นมามากจนแยกความต้องการตัวเองไม่ชัด|ตั้งขอบเขตการช่วยเหลือ
King of Cups|ความนิ่งทางอารมณ์อาจช่วยให้คุณพาเรื่องละเอียดอ่อนไปสู่การคุยที่มีเหตุผล|ยอมรับความรู้สึกโดยไม่ปล่อยให้ตัดสินแทนทั้งหมด|อารมณ์ที่กดไว้อาจแสดงออกอ้อม ๆ จนคนอื่นไม่เข้าใจ|บอกสิ่งที่รู้สึกอย่างตรงและสุภาพ
Ace of Swords|ข้อมูลหรือมุมมองใหม่อาจช่วยให้คุณตัดสินใจเรื่องที่ค้างได้ชัดขึ้น|ใช้ข้อเท็จจริงเป็นจุดเริ่มต้นของการคุย|ข้อสรุปอาจยังตั้งอยู่บนข้อมูลไม่ครบ ทำให้เข้าใจผิดได้|ตรวจแหล่งข้อมูลก่อนปักใจ
2 of Swords|คุณอาจกำลังเลื่อนการเลือกระหว่างสองทางเพราะไม่อยากเสียอย่างใดอย่างหนึ่ง|ระบุข้อมูลที่ยังขาดก่อนเลือก|เรื่องที่เลี่ยงไว้อาจเริ่มเรียกร้องให้คุณตัดสินใจ|จัดลำดับสิ่งสำคัญก่อนตอบ
3 of Swords|คำพูดหรือความจริงที่ไม่ตรงใจอาจทำให้ผิดหวัง แต่ช่วยให้เห็นสิ่งที่ต้องยอมรับ|ให้เวลาตัวเองก่อนตอบด้วยอารมณ์|คุณอาจเริ่มคุยหรือทำใจกับเรื่องที่เคยเจ็บได้มากขึ้น|ค่อย ๆ เยียวยาโดยไม่ฝืนให้อภัยทันที
4 of Swords|การพักจากการคิดวนอาจทำให้คุณกลับมาตัดสินใจได้เป็นระบบขึ้น|เว้นเวลาจากเรื่องนั้นอย่างตั้งใจ|คุณอาจอยากกลับไปลุยทั้งที่ยังไม่ได้พักพอ|กลับมาทีละขั้นแทนการเร่งเต็มกำลัง
5 of Swords|การพยายามชนะบทสนทนาอาจทำให้เสียความร่วมมือมากกว่าสิ่งที่ได้|เลือกเป้าหมายร่วมแทนการเอาชนะ|คุณอาจมีจังหวะยุติการโต้เถียง แต่ต้องตกลงว่าจะไม่กลับไปซ้ำแบบเดิม|คุยเงื่อนไขการเริ่มต้นใหม่
6 of Swords|คุณอาจค่อย ๆ ออกจากบรรยากาศที่ตึงเครียดไปสู่วิธีจัดการที่สงบขึ้น|พาบทเรียนไปต่อโดยไม่แบกทุกอย่าง|เรื่องค้างเดิมอาจตามมารบกวนแม้เปลี่ยนสถานที่หรือวิธีแล้ว|จัดการต้นเหตุที่ยังไม่ได้คุย
7 of Swords|การทำสิ่งต่าง ๆ โดยไม่ชี้แจงอาจสร้างช่องว่างของความไว้ใจ|รักษาความเป็นส่วนตัวพร้อมสื่อสารเรื่องที่เกี่ยวข้อง|สิ่งที่เคยเลี่ยงพูดอาจถึงเวลาต้องอธิบายตรง ๆ|ยอมรับข้อเท็จจริงและรับผิดชอบส่วนของตัวเอง
8 of Swords|คุณอาจรู้สึกว่าทางเลือกถูกจำกัด แต่บางข้อจำกัดยังสามารถตรวจสอบหรือขอความช่วยเหลือได้|แยกข้อจำกัดจริงออกจากความกลัว|คุณอาจเริ่มเห็นทางเลือกที่เคยมองไม่ออกและกล้าตัดสินใจมากขึ้น|เลือกก้าวเล็กที่ช่วยคืนอำนาจให้ตัวเอง
9 of Swords|ความกังวลอาจทำให้คุณคาดภาพแย่ล่วงหน้ามากกว่าสิ่งที่มีหลักฐาน|เขียนข้อเท็จจริงแยกจากสิ่งที่กลัว|การพูดสิ่งที่กังวลกับคนที่ไว้ใจอาจช่วยให้เห็นมุมอื่น|ขอแรงสนับสนุนแทนการแบกคนเดียว
10 of Swords|คุณอาจถึงจุดที่ต้องยอมจบวิธีเดิมที่ทำให้เสียแรงซ้ำ ๆ เพื่อจัดแผนใหม่|ดูแลตัวเองและเริ่มจากสิ่งจำเป็น|หลังเรื่องหนัก คุณอาจเริ่มตั้งหลักได้ แต่ยังไม่ต้องรีบกลับไปเหมือนเดิม|ฟื้นจังหวะของตัวเองทีละขั้น
Page of Swords|ความอยากรู้หรือข้อมูลใหม่อาจทำให้คุณตั้งคำถามที่ช่วยเปิดประเด็นสำคัญ|ถามเพื่อเข้าใจและตรวจสอบก่อนส่งต่อ|ข่าวที่ยังไม่ยืนยันอาจทำให้เกิดความเข้าใจผิด|งดสรุปจากข้อความสั้นหรือคำบอกต่อ
Knight of Swords|คุณอาจอยากแก้เรื่องให้จบเร็วและพร้อมพูดอย่างตรงไปตรงมา|เผื่อเวลาฟังผลกระทบต่อผู้อื่น|การรีบตอบหรือรีบตัดสินอาจทำให้รายละเอียดสำคัญหลุดไป|หยุดตรวจเป้าหมายก่อนลงมือ
Queen of Swords|คุณอาจต้องวางขอบเขตและพูดความจริงอย่างชัดเจนเพื่อให้เรื่องเดินต่อ|แยกข้อเท็จจริงออกจากการตำหนิ|ประสบการณ์ไม่ดีอาจทำให้คุณปิดใจหรือใช้คำพูดแข็งกว่าที่ตั้งใจ|บอกความต้องการโดยไม่เหมารวม
King of Swords|การใช้เหตุผลและเกณฑ์ที่ชัดอาจช่วยให้ตัดสินเรื่องซับซ้อนได้|อธิบายเหตุผลให้ผู้เกี่ยวข้องเข้าใจ|การยึดว่าตัวเองถูกอาจทำให้มองข้ามข้อมูลที่ขัดกับความคิด|เปิดรับหลักฐานใหม่ก่อนสรุป
Ace of Pentacles|โอกาสที่จับต้องได้อาจเริ่มเข้ามาในรูปของงาน ทรัพยากร หรือสิ่งที่ต่อยอดได้|ตรวจเงื่อนไขและเริ่มวางรากฐาน|โอกาสอาจยังไม่พร้อมใช้จริงเพราะขาดทรัพยากรหรือรายละเอียด|เช็กต้นทุนเวลาและสิ่งที่ต้องเตรียม
2 of Pentacles|คุณอาจต้องจัดสมดุลระหว่างหลายหน้าที่หรือรายจ่ายที่มาใกล้กัน|จัดลำดับตามความจำเป็น|การหมุนหลายเรื่องพร้อมกันอาจทำให้บางอย่างหลุดการดูแล|ลดสิ่งที่รับเพิ่มและทำแผนให้เห็นทั้งหมด
3 of Pentacles|ความร่วมมือกับคนที่มีทักษะต่างกันอาจทำให้ผลงานก้าวหน้าชัดขึ้น|ตกลงหน้าที่และมาตรฐานร่วมกัน|งานอาจสะดุดเพราะความคาดหวังหรือบทบาทของแต่ละคนไม่ตรงกัน|ตรวจงานร่วมก่อนทำต่อยาว ๆ
4 of Pentacles|คุณอาจพยายามรักษาสิ่งที่มีจนไม่กล้าเปิดรับทางเลือกใหม่ ความมั่นคงยังสำคัญแต่การยึดแน่นเกินไปอาจทำให้ติดอยู่|แยกสิ่งที่ต้องรักษาออกจากสิ่งที่ยืดหยุ่นได้|คุณอาจเริ่มคลายการควบคุม แต่ควรระวังการปล่อยทุกอย่างรวดเดียวเพราะความอึดอัด|กำหนดขอบเขตที่พอดีก่อนเปลี่ยน
5 of Pentacles|ความรู้สึกว่าทรัพยากรหรือแรงสนับสนุนไม่พออาจทำให้คุณมองทางเลือกแคบลง|สอบถามความช่วยเหลือที่เข้าถึงได้|คุณอาจเริ่มเห็นทางตั้งหลักหรือช่องทางรับแรงสนับสนุน|วางขั้นตอนเล็ก ๆ ที่ทำได้ต่อเนื่อง
6 of Pentacles|การช่วยเหลือหรือแบ่งทรัพยากรอาจเข้ามามีบทบาท แต่ควรให้และรับอย่างสมดุล|ตกลงเงื่อนไขให้ทั้งสองฝ่ายเข้าใจ|ความช่วยเหลือที่มีเงื่อนไขไม่ชัดอาจทำให้ฝ่ายหนึ่งรู้สึกเป็นหนี้บุญคุณ|คุยความคาดหวังก่อนรับปาก
7 of Pentacles|สิ่งที่ลงแรงอาจยังต้องใช้เวลา คุณมีจังหวะประเมินว่าจะดูแลต่อหรือปรับวิธี|วัดความคืบหน้าก่อนเพิ่มแรงลงไป|การรอโดยไม่ทบทวนอาจทำให้ใช้แรงกับทางที่ไม่ตอบเป้า|เช็กว่าผลที่ได้คุ้มกับสิ่งที่ลงไปหรือไม่
8 of Pentacles|ความชำนาญมีแนวโน้มเพิ่มจากการฝึกซ้ำและเก็บรายละเอียด ผลงานจะชัดกว่าการเร่งหาทางลัด|เลือกทักษะหนึ่งอย่างมาพัฒนาต่อเนื่อง|การทำซ้ำโดยไม่รับข้อเสนอแนะอาจทำให้ยังติดข้อผิดพลาดเดิม|ทบทวนคุณภาพก่อนเพิ่มปริมาณ
9 of Pentacles|คุณอาจเริ่มเห็นคุณค่าของสิ่งที่สร้างด้วยตัวเองและจัดชีวิตได้เป็นอิสระขึ้น|รักษาวินัยที่พาคุณมาถึงจุดนี้|การรักษาภาพว่าทุกอย่างพร้อมอาจกดดันคุณเกินความเป็นจริง|จัดสิ่งที่จำเป็นก่อนสิ่งที่ทำเพื่อภาพลักษณ์
10 of Pentacles|คุณอาจได้คิดเรื่องความมั่นคงระยะยาวและสิ่งที่ต้องดูแลร่วมกับครอบครัวหรือกลุ่ม|คุยแผนระยะยาวให้ผู้เกี่ยวข้องรับรู้|ความคาดหวังเรื่องทรัพยากรหรือหน้าที่ในครอบครัวอาจไม่ตรงกัน|แยกสิทธิ หน้าที่ และความสมัครใจให้ชัด
Page of Pentacles|โอกาสเรียนรู้ที่นำไปใช้จริงอาจช่วยให้คุณสร้างพื้นฐานใหม่|ตั้งตารางฝึกและติดตามผล|ความตั้งใจอาจยังไม่กลายเป็นกิจวัตร ทำให้แผนเรียนรู้ค้าง|เริ่มจากเป้าหมายที่เล็กพอจะทำทุกสัปดาห์
Knight of Pentacles|ความสม่ำเสมออาจพาให้เรื่องเดินหน้าแม้ไม่รวดเร็ว ความน่าเชื่อถือเกิดจากการทำตามที่บอก|รักษาจังหวะและตรวจรายละเอียด|กิจวัตรเดิมอาจกลายเป็นความซ้ำซากจนคุณหยุดพัฒนาวิธี|ปรับหนึ่งขั้นตอนที่กินแรงเกินจำเป็น
Queen of Pentacles|การจัดทรัพยากรอย่างใส่ใจอาจทำให้ทั้งตัวคุณและคนใกล้ตัวรู้สึกมั่นคงขึ้น|ดูแลความจำเป็นโดยไม่รับทุกอย่างไว้คนเดียว|การดูแลผู้อื่นมากเกินไปอาจทำให้เวลาและทรัพยากรของคุณตึง|กันส่วนที่จำเป็นสำหรับตัวเองไว้ก่อน
King of Pentacles|ประสบการณ์และการจัดการอย่างเป็นระบบอาจช่วยให้คุณรักษาผลลัพธ์ที่สร้างมา|คิดถึงความต่อเนื่องมากกว่าผลระยะสั้น|การวัดคุณค่าทุกอย่างด้วยผลประโยชน์อาจทำให้ความร่วมมือเสียสมดุล|คุยทั้งเป้าหมายและผลกระทบต่อคนรอบตัว
"""
READINGS = {}
for _row in _READING_ROWS.strip().splitlines():
    _name, _up, _ua, _rev, _ra = _row.split("|")
    READINGS[_name] = {"upright": (_up, _ua), "reversed": (_rev, _ra)}

ENGLISH_RANKS = dict(zip(
    (str(n) for n in range(2, 11)),
    ("Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"),
))


def card_names(card):
    """Display full bilingual names without changing keys used for artwork/cache."""
    english = card["name_en"]
    thai = card["name_th"]
    if card.get("suit") == "Major" and "(" in thai:
        thai = thai.split("(", 1)[1].rsplit(")", 1)[0]
    if " of " in english:
        rank, suit = english.split(" of ", 1)
        english = f"{ENGLISH_RANKS.get(rank, rank)} of {suit}"
    return f"{thai} — {english}"


CATEGORY_LENS = {
    "การเงิน": "มองแนวโน้มนี้ผ่านการจัดรายรับรายจ่าย ทรัพยากร และข้อตกลง ไม่ใช่สัญญาณยืนยันผลลงทุน",
    "การงาน": "ในเรื่องงาน ให้เชื่อมแนวโน้มนี้กับหน้าที่ ทีม และขั้นตอนถัดไปที่คุณทำได้",
    "ความรัก": "ในเรื่องความรัก ให้เชื่อมแนวโน้มนี้กับการสื่อสารและขอบเขต ไพ่ไม่ได้ยืนยันความคิดของอีกฝ่าย",
}


def prediction(card, orientation, category="ภาพรวม", position="", period=""):
    outlook, advice = READINGS[card["name_en"]][orientation]
    if category == "สุขภาพ":
        # A symbolic reflection, never a diagnosis or prediction of illness/recovery.
        return ("ใช้ไพ่ใบนี้สะท้อนการดูแลตัวเองและขอบเขตในชีวิตประจำวัน "
                "ไม่ใช้สรุปภาวะสุขภาพหรือทำนายโรค", advice)
    if "อดีต" in position:
        frame = "มองย้อนถึงรูปแบบที่อาจมีอิทธิพลต่อเรื่องนี้: "
    elif "อุปสรรค" in position:
        frame = "จุดท้าทายคือการรับมือกับแนวโน้มต่อไปนี้ ไม่ให้ขัดขวางสิ่งที่คุณต้องการ: "
    elif "เป้าหมาย" in position or "ความหวัง" in position:
        frame = "ใช้แนวโน้มนี้สำรวจสิ่งที่คุณคาดหวังหรือกังวล ไม่ใช่ข้อสรุปว่าจะเกิดขึ้น: "
    elif "อิทธิพล" in position:
        frame = "พิจารณาว่าแนวโน้มนี้สะท้อนบรรยากาศรอบตัวอย่างไร: "
    elif "ตัวคุณเอง" in position:
        frame = "ใช้แนวโน้มนี้ทบทวนวิธีมองสถานการณ์ของคุณ: "
    elif "อนาคต" in position or "ผลลัพธ์" in position:
        frame = "หากเงื่อนไขเดิมดำเนินต่อ แนวโน้มที่ควรพิจารณาคือ: "
    else:
        frame = {"รายวัน": "ประเด็นให้ทบทวนในวันนี้: ",
                 "รายเดือน": "ประเด็นให้ทบทวนในเดือนนี้: "}.get(period, "")
    lens = CATEGORY_LENS.get(category, "")
    return frame + outlook + (f"\n{lens}" if lens else ""), advice


def text_box(text):
    """Native Discord shaded box without syntax highlighting."""
    clean = str(text).replace(chr(96), "ˋ").strip()
    return "```\n" + clean + "\n```"


def add_reading_fields(pages, name, value):
    """Keep each private message below Discord's embed/field text limits."""
    if len(name) > 256 or len(value) > 1024:
        raise ValueError("Reading field exceeds Discord limits")
    page = pages[-1]
    if len(page.fields) >= 5 or len(page) + len(name) + len(value) > 5500:
        page = discord.Embed(title="🔮 คำทำนาย (ต่อ)", color=PURPLE)
        page.set_footer(text=FOOTER_TEXT)
        pages.append(page)
    page.add_field(name=name, value=value, inline=False)

_MINOR_KEYWORDS = {
    "Wands": [
        ("แรงบันดาลใจ การเริ่มลงมือ", "ไฟที่สะดุด ยังไม่พร้อมเริ่ม"),
        ("การวางแผนและมองทางเลือก", "ลังเล กลัวออกจากความคุ้นเคย"),
        ("การขยายตัวและมองไกล", "การขยายแผนที่ล่าช้า"),
        ("หมุดหมาย การเฉลิมฉลอง พื้นที่มั่นคง", "ความไม่ลงตัวในกลุ่มหรือบ้าน"),
        ("การแข่งขัน ความคิดเห็นที่ชนกัน", "ลดการปะทะหรือเลี่ยงความขัดแย้ง"),
        ("การยอมรับและชัยชนะ", "ขาดการยอมรับหรือยึดติดคำชม"),
        ("ยืนหยัดและปกป้องจุดยืน", "แรงต้านมากเกินกำลัง"),
        ("ข่าวสารและความคืบหน้ารวดเร็ว", "ล่าช้า สื่อสารคลาดเคลื่อน"),
        ("ความอึด การระวังตัวหลังผ่านเรื่องยาก", "เหนื่อยล้า การตั้งรับมากเกินไป"),
        ("ภาระ ความรับผิดชอบที่หนัก", "แบ่งภาระหรือถึงขีดจำกัด"),
        ("อยากทดลองและสำรวจ", "ไอเดียที่ยังไม่เป็นรูปธรรม"),
        ("กล้าลุย พลังและความกระตือรือร้น", "หุนหัน ขาดความต่อเนื่อง"),
        ("ความมั่นใจและเสน่ห์ในการนำ", "เปรียบเทียบตัวเอง ขาดความมั่นใจ"),
        ("วิสัยทัศน์และการนำไปลงมือ", "เร่งรัด ใช้อำนาจเกินพอดี"),
    ],
    "Cups": [
        ("เปิดใจและความรู้สึกใหม่", "ปิดกั้นหรือเก็บความรู้สึก"),
        ("ความสัมพันธ์และการแลกเปลี่ยนที่สมดุล", "ความสัมพันธ์ที่ไม่ลงรอย"),
        ("มิตรภาพและแรงสนับสนุนจากกลุ่ม", "แรงกดดันหรือความขัดแย้งในกลุ่ม"),
        ("เบื่อหน่าย ไม่เปิดรับทางเลือก", "เริ่มกลับมาเปิดรับและมีส่วนร่วม"),
        ("ผิดหวัง มองสิ่งที่สูญเสีย", "ค่อย ๆ ยอมรับและเดินต่อ"),
        ("ความทรงจำและความผูกพันเดิม", "ยึดติดอดีตหรือถึงเวลาปล่อย"),
        ("ทางเลือกมาก ภาพฝันที่ต้องตรวจสอบ", "เริ่มเลือกได้ชัดและอยู่กับความจริง"),
        ("เดินออกเพื่อค้นหาความหมายใหม่", "ลังเลที่จะจากสิ่งคุ้นเคย"),
        ("ความพึงพอใจและความปรารถนา", "ได้สิ่งที่หวังแต่ยังไม่อิ่มใจ"),
        ("ความสุขร่วมกันและความกลมกลืน", "ความคาดหวังในบ้านหรือความสัมพันธ์ไม่ตรงกัน"),
        ("ข้อความจากใจ ความอ่อนโยน", "อารมณ์อ่อนไหวหรือคาดหวังเกินจริง"),
        ("คำชวนและการเดินตามความรู้สึก", "อุดมคติหรือคำพูดที่ยังขาดการกระทำ"),
        ("ความเข้าใจและการรับฟัง", "รับอารมณ์ผู้อื่นจนขาดขอบเขต"),
        ("ความนิ่งและการจัดการอารมณ์", "กดอารมณ์หรือใช้อารมณ์ควบคุม"),
    ],
    "Swords": [
        ("ความชัดเจนและความจริง", "ข้อมูลไม่ครบ ความคิดสับสน"),
        ("ทางเลือกที่ยังไม่ตัดสินใจ", "แรงกดดันให้เผชิญสิ่งที่เลี่ยง"),
        ("ความเสียใจและความจริงที่เจ็บ", "การค่อย ๆ เยียวยาความรู้สึก"),
        ("พักและทบทวน", "อยากกลับมาลงมือหรือพักไม่พอ"),
        ("ความขัดแย้ง ชนะโดยมีสิ่งต้องเสีย", "ยุติการปะทะและหาทางคืนดี"),
        ("การเปลี่ยนผ่านไปสู่ความสงบ", "เรื่องค้างที่ยังขัดขวางการไปต่อ"),
        ("กลยุทธ์ ความลับ การหลบเลี่ยง", "การเปิดเผยหรือเผชิญความจริง"),
        ("ความรู้สึกถูกจำกัดและติดอยู่", "เริ่มเห็นทางเลือกและเป็นอิสระ"),
        ("ความกังวลและคิดวน", "ขอความช่วยเหลือและคลายความคิดวน"),
        ("จุดสิ้นสุดที่ยากและการยอมจบ", "การเริ่มตั้งหลักหลังเรื่องหนัก"),
        ("อยากรู้ ตั้งคำถาม ตรวจสอบ", "ข่าวลือหรือสื่อสารโดยไม่ตรวจสอบ"),
        ("มุ่งมั่นและลงมืออย่างรวดเร็ว", "รีบร้อนจนพลาดรายละเอียด"),
        ("ขอบเขตและการสื่อสารตรงไปตรงมา", "ตัดสินแข็งหรือปิดใจจากอดีต"),
        ("เหตุผล ความชัดเจน และหลักเกณฑ์", "ยึดความคิดตัวเองหรือใช้เหตุผลกดผู้อื่น"),
    ],
    "Pentacles": [
        ("โอกาสและรากฐานที่จับต้องได้", "โอกาสที่ยังขาดความพร้อม"),
        ("การจัดสมดุลหลายภาระ", "จัดการหลายเรื่องจนเสียสมดุล"),
        ("ทักษะและความร่วมมือ", "บทบาทและมาตรฐานไม่ตรงกัน"),
        ("รักษาความมั่นคง ควบคุมและยึดไว้", "คลายการยึดติดหรือควบคุมไม่อยู่"),
        ("ความขาดแคลนและรู้สึกไร้แรงสนับสนุน", "เริ่มตั้งหลักและรับความช่วยเหลือ"),
        ("ให้และรับทรัพยากรอย่างสมดุล", "ความช่วยเหลือที่ไม่เท่าเทียม"),
        ("อดทนและประเมินผลที่ลงทุนลงแรง", "รอโดยไม่คุ้มหรือขาดการทบทวน"),
        ("ฝึกฝน ความชำนาญ ใส่ใจรายละเอียด", "ทำซ้ำโดยไม่พัฒนาหรือละเลยคุณภาพ"),
        ("พึ่งตนเองและชื่นชมสิ่งที่สร้าง", "กดดันจากภาพลักษณ์หรือขาดอิสระ"),
        ("ความมั่นคงระยะยาวและครอบครัว", "ความไม่ลงตัวของทรัพยากรในครอบครัว"),
        ("เรียนรู้และวางพื้นฐาน", "ผัดผ่อนหรือขาดแผนเรียนรู้"),
        ("สม่ำเสมอ รอบคอบ เชื่อถือได้", "ติดกิจวัตรหรือหยุดพัฒนา"),
        ("ดูแลและจัดทรัพยากรอย่างใส่ใจ", "ดูแลผู้อื่นจนลืมความจำเป็นของตน"),
        ("บริหารและรักษาความมั่นคง", "ยึดผลประโยชน์หรือควบคุมมากเกินไป"),
    ],
}


def card_meaning(card, orientation):
    if card.get("suit") in _MINOR_KEYWORDS:
        rank = card["name_en"].split(" of ", 1)[0]
        return _MINOR_KEYWORDS[card["suit"]][RANKS.index(rank)][orientation == "reversed"]
    return tarot.get_meaning(card, orientation)


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
        if not path.is_file():
            path = BASE_DIR / path.name  # Also support sheets uploaded to the repo root.
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


async def send_reading(interaction, embeds, drawn):
    """Every success, continuation, and missing-art response stays private."""
    pages = [embeds] if isinstance(embeds, discord.Embed) else embeds
    try:
        picture = await asyncio.to_thread(render_cards, drawn)
    except (OSError, KeyError, ValueError):
        logger.exception("Unable to load tarot artwork")
        await interaction.followup.send(
            content="ยังโหลดรูปไพ่ไม่ได้ แต่คำทำนายยังใช้งานได้ครับ",
            embed=pages[0], ephemeral=True)
    else:
        pages[0].set_image(url="attachment://tarot-cards.jpg")
        attachment = discord.File(picture, filename="tarot-cards.jpg")
        try:
            await interaction.followup.send(
                embed=pages[0], file=attachment, ephemeral=True)
        finally:
            attachment.close()
            picture.close()
    for page in pages[1:]:
        await interaction.followup.send(embed=page, ephemeral=True)



SET2_DONATE_CHANNEL_ID = 1511062155640963072
SET2_GIF_URL = (
    "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExbXhld3R3dnZoc294"
    "YnJubW55N2wwYWh0ZG5ic2x6eDIxNGRkaWtqbCZlcD12MV9pbnRlcm5hbF9naWZf"
    "YnlfaWQmY3Q9Zw/EdZ3R2o7WBuoQuB27z/giphy.gif"
)


def build_set2_embed() -> discord.Embed:
    embed = discord.Embed(
        title="ดูดวงกับพ่อหมอป๊อก 🔮",
        description=(
            "**หมวดหมู่**     : ภาพรวม · การเงิน · การงาน · ความรัก · สุขภาพ\n"
            "**สถานะ**       : กำลังเปิดให้ดูดวงฟรี ไม่มีค่าใช้จ่าย"
        ),
        color=PURPLE,
    )
    embed.set_image(url=SET2_GIF_URL)
    embed.add_field(
        name="\u200b",
        value=f"**สนับสนุน Server ง่ายๆ**\nได้ที่ห้อง <#{SET2_DONATE_CHANNEL_ID}> ข้างล่างเลย",
        inline=False,
    )
    embed.set_footer(text=FOOTER_TEXT)
    return embed


def build_help_embed() -> discord.Embed:
    embed = discord.Embed(title="🔮 ดูดวงกับพ่อหมอป๊อก", color=PURPLE)
    embed.add_field(
        name="/ดูดวง [ช่วงเวลา] [หมวดหมู่]",
        value=(
            "เลือก **รายวัน / รายเดือน** และเลือก 5 หมวดหมู่: "
            "**ภาพรวม, การเงิน, การงาน, ความรัก, สุขภาพ**"
        ),
        inline=False,
    )
    embed.add_field(
        name="/เปิดไพ่ [จำนวน] [คำถาม]",
        value="เลือก **1 / 3 / 5 / 10 ใบ** พร้อมคำทำนายตามตำแหน่งและทิศทางไพ่",
        inline=False,
    )
    embed.add_field(
        name="/วิธีใช้",
        value=(
            "คำทำนายตีความจากข้อความที่เตรียมไว้ตามไพ่และตำแหน่ง "
            "ไม่ได้ใช้ AI วิเคราะห์คำถามอิสระ และไม่ยืนยันเหตุการณ์ในอนาคต"
        ),
        inline=False,
    )
    embed.set_footer(text=FOOTER_TEXT)
    return embed


async def send_duang_result(interaction: discord.Interaction, period: str, category: str):
    await interaction.response.defer(thinking=True, ephemeral=True)
    card, orientation, _ = get_or_draw_card(interaction.user.id, period, category)
    outlook, advice = prediction(card, orientation, category=category, period=period)
    emoji = tarot.CATEGORY_INFO.get(category, {}).get("emoji", "🔮")
    embed = discord.Embed(
        title=f"{emoji} ดวง{period} — {category}",
        description=f"{card['emoji']} **{card_names(card)} ({tarot.orientation_label(orientation)})**",
        color=PURPLE if orientation == "upright" else REVERSED_COLOR,
    )
    embed.add_field(name="📖 ความหมายไพ่", value=text_box(card_meaning(card, orientation)), inline=False)
    embed.add_field(name="🔮 คำทำนาย", value=text_box(outlook), inline=False)
    embed.add_field(name="💡 คำแนะนำ", value=text_box(advice), inline=False)
    embed.set_footer(text=FOOTER_TEXT)
    await send_reading(interaction, embed, [(card, orientation)])


async def send_open_cards_result(
    interaction: discord.Interaction,
    count: int,
    question: str | None = None,
):
    await interaction.response.defer(thinking=True, ephemeral=True)
    drawn = tarot.draw_cards(count)
    desc = "🐈‍⬛ สับไพ่… ให้ไพ่แมวนำทางไปกับพ่อหมอป๊อก"
    if question:
        desc += f"\n\n**คำถาม:** {discord.utils.escape_markdown(question)}"
    embed = discord.Embed(title=f"🔮 เปิดไพ่ทาโร่ {count} ใบ", description=desc, color=PURPLE)
    embed.set_footer(text=FOOTER_TEXT)
    pages = [embed]
    for index, (position, (card, orientation)) in enumerate(
        zip(tarot.SPREAD_POSITIONS[count], drawn), 1
    ):
        outlook, advice = prediction(card, orientation, position=position)
        add_reading_fields(
            pages,
            name=f"{index}. {position} — {card_names(card)} ({tarot.orientation_label(orientation)})",
            value=(
                f"📖 **ความหมายไพ่**\n{text_box(card_meaning(card, orientation))}\n"
                f"🔮 **คำทำนาย**\n{text_box(outlook)}\n"
                f"💡 **คำแนะนำ**\n{text_box(advice)}"
            ),
        )
    await send_reading(interaction, pages, drawn)


class DuangPickerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.select(
        placeholder="เลือกช่วงเวลา",
        options=[
            discord.SelectOption(label="รายวัน", value="รายวัน", emoji="📅"),
            discord.SelectOption(label="รายเดือน", value="รายเดือน", emoji="🗓️"),
        ],
    )
    async def period_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        period = select.values[0]
        await interaction.response.edit_message(
            content=f"🔮 ช่วงเวลา: **{period}**\nเลือกหมวดหมู่ที่ต้องการดูได้เลย",
            view=CategoryPickerView(period),
        )


class CategoryPickerView(discord.ui.View):
    def __init__(self, period: str):
        super().__init__(timeout=120)
        self.period = period

    @discord.ui.select(
        placeholder="เลือกหมวดหมู่",
        options=[
            discord.SelectOption(label="ภาพรวม", value="ภาพรวม", emoji="🔮"),
            discord.SelectOption(label="การเงิน", value="การเงิน", emoji="💰"),
            discord.SelectOption(label="การงาน", value="การงาน", emoji="💼"),
            discord.SelectOption(label="ความรัก", value="ความรัก", emoji="❤️"),
            discord.SelectOption(label="สุขภาพ", value="สุขภาพ", emoji="🌿"),
        ],
    )
    async def category_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await send_duang_result(interaction, self.period, select.values[0])


class OpenCardsPickerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.select(
        placeholder="เลือกจำนวนไพ่",
        options=[
            discord.SelectOption(label="1 ใบ", value="1", description="คำตอบตรงๆ", emoji="🃏"),
            discord.SelectOption(label="3 ใบ", value="3", description="อดีต / ปัจจุบัน / อนาคต", emoji="🔮"),
            discord.SelectOption(label="5 ใบ", value="5", description="ภาพรวมสถานการณ์", emoji="🖐️"),
            discord.SelectOption(label="10 ใบ", value="10", description="Celtic Cross", emoji="✨"),
        ],
    )
    async def count_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await send_open_cards_result(interaction, int(select.values[0]))


class Set2View(discord.ui.View):
    """Persistent interactive buttons only."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="/ดูดวง",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="set2:duang",
    )
    async def duang_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🔮 เลือกช่วงเวลาที่ต้องการดูดวง",
            view=DuangPickerView(),
            ephemeral=True,
        )

    @discord.ui.button(
        label="เปิดไพ่",
        emoji="🔮",
        style=discord.ButtonStyle.danger,
        custom_id="set2:open_cards",
    )
    async def open_cards_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🃏 เลือกจำนวนไพ่ที่ต้องการเปิด",
            view=OpenCardsPickerView(),
            ephemeral=True,
        )

    @discord.ui.button(
        label="วิธีใช้งาน",
        emoji="📖",
        style=discord.ButtonStyle.secondary,
        custom_id="set2:help",
    )
    async def help_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            embed=build_help_embed(),
            ephemeral=True,
        )


class Set2MessageView(Set2View):
    """The posted message gets an extra Donate link button."""

    def __init__(self, donate_url: str):
        super().__init__()
        self.add_item(
            discord.ui.Button(
                label="Donate ↗",
                emoji="🎁",
                style=discord.ButtonStyle.link,
                url=donate_url,
            )
        )


class TarotBot(commands.Bot):
    async def setup_hook(self):
        # Persistent view contains only buttons with custom_id.
        self.add_view(Set2View())

        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
        else:
            synced = await self.tree.sync()
        logger.info("Synced %s slash commands", len(synced))


intents = discord.Intents.default()
intents.message_content = True

bot = TarotBot(
    command_prefix="!",
    intents=intents,
    status=discord.Status.online,
    activity=discord.CustomActivity(name=STATUS_TEXT),
    allowed_mentions=discord.AllowedMentions.none(),
)


@bot.event
async def on_ready():
    logger.info("Logged in as %s — พร้อมดูดวงแล้ว!", bot.user)


@bot.command(name="set2")
@commands.guild_only()
@commands.has_guild_permissions(manage_guild=True)
async def set2(ctx: commands.Context):
    donate_url = f"https://discord.com/channels/{ctx.guild.id}/{SET2_DONATE_CHANNEL_ID}"
    await ctx.send(
        embed=build_set2_embed(),
        view=Set2MessageView(donate_url),
    )


@set2.error
async def set2_error(ctx: commands.Context, error: Exception):
    if isinstance(error, commands.MissingPermissions):
        await ctx.reply("คำสั่งนี้ต้องมีสิทธิ์ **Manage Server** ก่อนครับ", mention_author=False)
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.reply("ใช้คำสั่งนี้ภายในเซิร์ฟเวอร์เท่านั้นครับ", mention_author=False)
    else:
        logger.exception("!set2 failed", exc_info=error)
        await ctx.reply("เกิดข้อผิดพลาดในการส่ง Embed ครับ", mention_author=False)


@bot.tree.command(name="ดูดวง", description="ดูดวงรายวันหรือรายเดือนกับพ่อหมอป๊อก")
@app_commands.describe(ช่วงเวลา="เลือกช่วงเวลา", หมวดหมู่="เลือกเรื่องที่อยากดู")
@app_commands.choices(
    ช่วงเวลา=[app_commands.Choice(name=x, value=x) for x in ("รายวัน", "รายเดือน")],
    หมวดหมู่=[app_commands.Choice(name=x, value=x) for x in ("ภาพรวม", "การเงิน", "การงาน", "ความรัก", "สุขภาพ")],
)
async def duang(interaction: discord.Interaction, ช่วงเวลา: app_commands.Choice[str], หมวดหมู่: app_commands.Choice[str]):
    await send_duang_result(interaction, ช่วงเวลา.value, หมวดหมู่.value)


@bot.tree.command(name="เปิดไพ่", description="เปิดไพ่แมว 1, 3, 5 หรือ 10 ใบ")
@app_commands.describe(จำนวน="จำนวนไพ่", คำถาม="คำถามที่อยากถาม (ไม่บังคับ)")
@app_commands.choices(
    จำนวน=[
        app_commands.Choice(name="1 ใบ — คำตอบตรงๆ", value=1),
        app_commands.Choice(name="3 ใบ — อดีต/ปัจจุบัน/อนาคต", value=3),
        app_commands.Choice(name="5 ใบ — ภาพรวมสถานการณ์", value=5),
        app_commands.Choice(name="10 ใบ — Celtic Cross", value=10),
    ]
)
async def open_cards(interaction: discord.Interaction, จำนวน: app_commands.Choice[int], คำถาม: app_commands.Range[str, 1, 1000] = None):
    await send_open_cards_result(interaction, จำนวน.value, คำถาม)


@bot.tree.command(name="วิธีใช้", description="วิธีดูดวงกับพ่อหมอป๊อก")
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message(
        embed=build_help_embed(),
        ephemeral=True,
    )


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
