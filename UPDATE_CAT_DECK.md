# พ่อหมอป๊อก — ไพ่แมวม่วงดำ

ชุดอัปเดตสำหรับ repository gamemingsong-crypto/tarotcard

## มีอะไรเปลี่ยน

- สถานะ Discord: ดูดวงกับพ่อหมอป๊อก l /ดูดวง
- คำสั่งหลักเปลี่ยนจาก /ดวง เป็น /ดูดวง
- คง /เปิดไพ่ (1, 3, 5, 10 ใบ) และ /วิธีใช้
- แนบรูปไพ่ตรงกับผลสุ่ม; ไพ่กลับหัวหมุนภาพ 180 องศา
- รูปหลายใบเรียงซ้ายไปขวา บนลงล่าง พร้อมเลขตามคำทำนาย
- ใช้ไฟล์ภาพในเครื่อง ไม่ต้องเรียกบริการสร้างภาพเมื่อมีคนใช้บอท
- คงฐานคำทำนาย tarot_data.py เดิม และแคช data/daily_cache.json
- นับวัน/เดือนด้วยเวลาประเทศไทย

## ไฟล์ที่ต้องอัปขึ้น GitHub

แตก ZIP และวางเนื้อหาข้างในลงที่ราก repository โดยตรง:

- bot.py
- requirements.txt
- .gitignore
- assets/cat_tarot/sheet_01.png ถึง sheet_13.png
- UPDATE_CAT_DECK.md

tarot_data.py ใน ZIP คือไฟล์เดิมจาก repository แนบไว้เพื่อให้แพ็กเกจครบ
ห้ามอัปโหลด .env, .venv หรือ data ของ VPS ขึ้น GitHub
ไม่ต้องเปลี่ยนโทเคนใน .env

ภาพแต่ละแผ่นมี 6 ใบ จัด 3 คอลัมน์ x 2 แถว บอทตัดเฉพาะใบที่สุ่มได้ให้อัตโนมัติ
อย่าเปลี่ยนชื่อไฟล์ ลำดับ หรือเลย์เอาต์ของแผ่นภาพ

ลำดับภาพ: Major Arcana 0–21, Wands 14 ใบ, Cups 14 ใบ, Swords 14 ใบ,
Pentacles 14 ใบ; แต่ละชุดย่อยเรียง Ace, 2–10, Page, Knight, Queen, King

## อัปเดต VPS หลัง commit ไฟล์ลง GitHub แล้ว

ใช้ Terminal ของ Admin และออกจาก nano ก่อน (Ctrl+O, Enter, Ctrl+X)

```bash
cd ~/tarotcard
git stash push -m "before-cat-deck-update" -- bot.py requirements.txt
git pull --ff-only
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m py_compile bot.py tarot_data.py
pm2 restart tarotcard
pm2 logs tarotcard --lines 30
```

รันทีละคำสั่ง หากพบ error ให้หยุดแก้ก่อนคำสั่งถัดไป
คำสั่ง stash เก็บการแก้ไข bot.py และ requirements.txt บน VPS ไว้ก่อนดึงไฟล์ใหม่
ไม่ต้องนำ stash กลับมาทับเวอร์ชันใหม่

เมื่อ log ขึ้น Logged in as ให้ Ctrl+C ออกจาก log แล้ว:

```bash
pm2 save
```

ทดสอบ /ดูดวง และ /เปิดไพ่ ใน Discord
บอทต้องมีสิทธิ์ View Channel, Send Messages, Embed Links, Attach Files ในห้องนั้น
ถ้าขึ้นข้อความว่ายังโหลดรูปไม่ได้ ให้เช็กว่า assets/cat_tarot มีครบ 13 ไฟล์

## สิ่งที่ตรวจแล้ว

ทดสอบในเครื่องโดยไม่ใช้ Discord token: โหลดคำสั่งและตัวเลือก, จับคู่ชื่อไพ่,
การใช้แคชซ้ำ, การแนบรูป 1/3/5/10 ใบ, ภาพกลับหัว, และการส่งข้อความทดแทนเมื่อไม่มีรูป
ยังไม่ได้ทดสอบเชื่อมต่อ Discord จริงหรือเปลี่ยนไฟล์บน VPS

## เอกสารอ้างอิง

การแนบไฟล์ใน Embed:
https://discordpy.readthedocs.io/en/stable/faq.html#how-do-i-use-a-local-image-file-for-an-embed-image
สถานะบอท:
https://docs.discord.com/developers/events/gateway-events#activity-object

ภาพประกอบชุดแมวเป็นภาพสร้างใหม่ด้วย image_gen ไม่ใช้ภาพไพ่จากแหล่งภายนอก
