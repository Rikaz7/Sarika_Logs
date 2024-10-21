import nextcord
import os
import random
import json  # ใช้สำหรับบันทึกข้อมูลการ setup
from nextcord.ext import commands
from dotenv import load_dotenv
from myserver import server_on

# หา path ของไฟล์ .env ที่อยู่ในโฟลเดอร์ที่สูงกว่าโฟลเดอร์ปัจจุบัน
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ตัวแปรสำหรับเก็บข้อมูลการตั้งค่า
role_id = None  # จะตั้งค่าใหม่ผ่าน Modal
button_name = "ยืนยัน"  # ชื่อปุ่มเริ่มต้น
button_emoji = "✅"  # อีโมจิของปุ่ม
setup_data_file = "setup_data.json"  # ไฟล์สำหรับเก็บ message_id

# สร้าง captcha แบบสุ่ม
def generate_captcha():
    return random.randint(1000, 9999)

# โหลดข้อมูลการ setup จากไฟล์
def load_setup_data():
    if os.path.exists(setup_data_file):
        with open(setup_data_file, 'r') as f:
            return json.load(f)
    return None

# บันทึกข้อมูลการ setup ลงไฟล์
def save_setup_data(message_id):
    with open(setup_data_file, 'w') as f:
        json.dump({"message_id": message_id}, f)




# Modal สำหรับการตั้งค่าระบบ
class SetupModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(title='ตั้งค่าระบบ')

        # กำหนดให้กรอก Role ID, ชื่อปุ่ม, title, และ description
        self.role_id_input = nextcord.ui.TextInput(label='กรุณาใส่ Role ID ที่จะให้:', required=True)
        self.button_name_input = nextcord.ui.TextInput(label='ชื่อปุ่ม:', placeholder=button_name, required=True)
        self.title_input = nextcord.ui.TextInput(label='Title ของ Embed:', placeholder='ใส่หัวข้อของ Embed', required=True)
        self.description_input = nextcord.ui.TextInput(label='Description ของ Embed:', placeholder='ใส่คำอธิบายของ Embed', required=True, style=nextcord.TextInputStyle.paragraph)

        # เพิ่มช่องกรอกข้อมูลใน Modal
        self.add_item(self.role_id_input)
        self.add_item(self.button_name_input)
        self.add_item(self.title_input)
        self.add_item(self.description_input)

    async def callback(self, interaction: nextcord.Interaction):
        global role_id, button_name

        # เก็บข้อมูลที่ได้รับจากผู้ใช้
        role_id = int(self.role_id_input.value)
        button_name = self.button_name_input.value  # เก็บชื่อปุ่มใหม่
        embed_title = self.title_input.value  # เก็บ title ที่กรอก
        embed_description = self.description_input.value  # เก็บ description ที่กรอก

        # สร้าง Embed ใหม่จากข้อมูลที่กรอกมา
        embed = nextcord.Embed(
            title=embed_title,  # ใช้ title จากผู้ใช้
            description=embed_description  # ใช้ description จากผู้ใช้
        )

        # ส่งข้อความพร้อมกับ view ของปุ่มในห้องที่ผู้ใช้เรียกคำสั่ง setup
        sent_message = await interaction.channel.send(embed=embed, view=Button(button_name))  # ส่งชื่อปุ่มที่กรอก
        save_setup_data(sent_message.id)  # บันทึก message_id ของ embed


# Modal สำหรับการกรอก captcha
class CaptchaModal(nextcord.ui.Modal):
    def __init__(self, user, correct_captcha):
        super().__init__(title='⚙️RIKAZ SECURITY')
        self.correct_captcha = correct_captcha
        self.user = user

        self.captcha_display = nextcord.ui.TextInput(label=f'กรุณากรอกหมายเลขนี้ : {self.correct_captcha}', required=True)
        self.add_item(self.captcha_display)

    async def callback(self, interaction: nextcord.Interaction):
        if self.captcha_display.value == str(self.correct_captcha):
            role = nextcord.utils.get(interaction.guild.roles, id=role_id)
            if role not in interaction.user.roles:
                await interaction.user.add_roles(role)
                embed = nextcord.Embed(description=f"ยืนยันตัวตนสำเร็จและได้รับยศ {role.mention} เรียบร้อย", color=0x77dd77)
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("คุณมียศนี้อยู่แล้ว", ephemeral=True)
        else:
            new_captcha = generate_captcha()
            await interaction.followup.send("คุณกรอกหมายเลขยืนยันไม่ถูกต้อง กรุณายืนยันตัวตนใหม่อีกครั้งค่ะ", ephemeral=True)
            await interaction.followup.send_modal(CaptchaModal(self.user, new_captcha))

class Button(nextcord.ui.View):
    def __init__(self, button_name):
        super().__init__(timeout=None)
        self.button_name = button_name  # รับชื่อปุ่มจากที่กรอกมา
        self.custom_id = f"addrole_{generate_captcha()}"  # ใช้ custom_id แบบสุ่มเพื่อไม่ให้ซ้ำกัน

        # สร้างปุ่มและเพิ่มเข้าไปใน View
        button = nextcord.ui.Button(
            label=self.button_name, 
            style=nextcord.ButtonStyle.blurple, 
            custom_id=self.custom_id
        )
        button.callback = self.addrole  # กำหนดให้ปุ่มนี้เรียกใช้ฟังก์ชัน addrole
        self.add_item(button)

    async def addrole(self, interaction: nextcord.Interaction):
        # ตรวจสอบบทบาท
        role = nextcord.utils.get(interaction.guild.roles, id=role_id)
        if role in interaction.user.roles:
            embed = nextcord.Embed(description="คุณมียศอยู่แล้ว", color=0xff6961)
            await interaction.send(embed=embed, ephemeral=True)
        else:
            captcha = generate_captcha()
            await interaction.response.send_modal(CaptchaModal(interaction.user, captcha))

@bot.event
async def on_ready():
    await bot.sync_all_application_commands()  # ซิงค์คำสั่ง Slash Commands
    print(f"BOT NAME: {bot.user}")
    await bot.change_presence(status=nextcord.Status.online)

    # โหลดข้อมูลการ setup ที่บันทึกไว้
    setup_data = load_setup_data()
    if setup_data and setup_data.get("message_id"):
        # ดึงข้อความเดิมจาก message_id ที่บันทึกไว้
        guild = bot.guilds[0]  # ใช้ guild แรกที่บอทอยู่
        channel = guild.text_channels[0]  # ใช้ห้องแรกในเซิฟเวอร์
        message_id = setup_data["message_id"]
        try:
            message = await channel.fetch_message(message_id)
            # แก้ไขข้อความเดิมเพื่อเพิ่ม interaction ใหม่ให้กับปุ่มเดิม
            await message.edit(view=Button(button_name))
        except nextcord.NotFound:
            pass

# เปลี่ยนคำสั่ง setup เป็น Slash Command เพื่อให้ใช้งาน interaction
@bot.slash_command(name="setup", description="ตั้งค่าระบบสำหรับบอท")
async def setup(interaction: nextcord.Interaction):
    if interaction.user.guild_permissions.administrator:
        await interaction.response.send_modal(SetupModal())
    else:
        await interaction.response.send_message('คุณไม่มีสิทธิ์ใช้คำสั่งนี้', ephemeral=True)

# เริ่มบอท
server_on(  )

bot.run(os.getenv("TOKEN"))