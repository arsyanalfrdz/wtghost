import discord
from discord.ext import commands
from flask import Flask, render_template_string
import threading
import json
import os
import datetime
from dotenv import load_dotenv

# Muat variabel environment
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

DB_FILE = 'brangkas.json'

# ==========================================
# 1. SISTEM DATABASE SEDERHANA (JSON)
# ==========================================
def load_db():
    if not os.path.exists(DB_FILE):
        return {"balance": 0, "inventory": {}, "transactions": [], "authorized_users": []}
    with open(DB_FILE, 'r') as f:
        data = json.load(f)
        if "inventory" not in data: data["inventory"] = {}
        if "authorized_users" not in data: data["authorized_users"] = []
        return data

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def add_transaction(user, t_type, amount, item_name, reason, image_url=None):
    db = load_db()
    if t_type == "deposit_money":
        db["balance"] += amount
    elif t_type == "withdraw_money":
        db["balance"] -= amount
    elif t_type == "deposit_item":
        if item_name not in db["inventory"]:
            db["inventory"][item_name] = 0
        db["inventory"][item_name] += amount
    elif t_type == "withdraw_item":
        if item_name in db["inventory"]:
            db["inventory"][item_name] -= amount
            if db["inventory"][item_name] <= 0:
                del db["inventory"][item_name]
    elif t_type == "update_item":
        if amount <= 0:
            if item_name in db["inventory"]:
                del db["inventory"][item_name]
        else:
            db["inventory"][item_name] = amount

    transaction = {
        "user": user,
        "type": t_type,
        "amount": amount,
        "item_name": item_name,
        "reason": reason,
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "image_url": image_url
    }
    db["transactions"].insert(0, transaction) # Masukkan di urutan paling atas
    
    # Menyimpan seluruh riwayat transaksi (batas 50 dihapus)
    save_db(db)
    return db


# ==========================================
# 2. WEBSITE DASHBOARD (FLASK)
# ==========================================
app = Flask(__name__)

# Template HTML dengan tema Dark/Badside
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Brankas WT GHOST - Rumah Kita RP</title>
    <style>
        body {
            background-color: #121212;
            color: #ffffff;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: #1e1e1e;
            padding: 20px;
            border-radius: 10px;
            border-top: 5px solid #d32f2f;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        }
        h1 {
            text-align: center;
            color: #d32f2f;
            text-transform: uppercase;
            letter-spacing: 2px;
        }
    .flex-container {
        display: flex;
        gap: 20px;
        margin-bottom: 20px;
    }
    .box {
        background-color: #2c2c2c;
        padding: 20px;
        border-radius: 8px;
        flex: 1;
    }
    .balance-amount {
        font-size: 40px;
        font-weight: bold;
        color: #4caf50;
        text-align: center;
        margin-top: 10px;
    }
    .inventory-list {
        list-style: none;
        padding: 0;
        margin: 10px 0 0 0;
    }
    .inventory-list li {
        background-color: #333;
        padding: 10px;
        margin-bottom: 5px;
        border-radius: 5px;
        display: flex;
        justify-content: space-between;
    }
    .item-name { font-weight: bold; color: #ff9800; }
    .item-qty { background: #d32f2f; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #333;
        }
        th {
            background-color: #333;
            color: #d32f2f;
        }
        .deposit { color: #4caf50; font-weight: bold; }
        .withdraw { color: #f44336; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🩸 Brankas WT GHOST Rumah Kita RP 🩸</h1>
        
        <div class="flex-container">
            <div class="box">
                <div style="text-align:center; font-size:18px;">TOTAL SALDO SAAT INI</div>
                <div class="balance-amount">$ {{ "{:,}".format(data.balance) }}</div>
            </div>
            
            <div class="box">
                <div style="text-align:center; font-size:18px; margin-bottom:10px;">📦 INVENTORY BARANG</div>
                {% if data.inventory %}
                    <ul class="inventory-list">
                    {% for item, qty in data.inventory.items() %}
                        <li><span class="item-name">{{ item }}</span> <span class="item-qty">{{ qty }}x</span></li>
                    {% endfor %}
                    </ul>
                {% else %}
                    <div style="text-align:center; color:#aaa; margin-top:20px;">Brankas barang kosong.</div>
                {% endif %}
            </div>
        </div>

        <h2>📜 Riwayat Transaksi</h2>
        <input type="text" id="searchInput" onkeyup="searchTable()" placeholder="🔍 Cari riwayat (nama, barang, tipe, atau keterangan...)" style="width: 100%; box-sizing: border-box; padding: 12px; margin-bottom: 15px; background: #333; color: #fff; border: 1px solid #555; border-radius: 5px; font-size: 16px;">
        
        <table id="transactionTable">
            <thead>
                <tr>
                    <th>Tanggal & Waktu</th>
                    <th>Anggota</th>
                    <th>Tipe</th>
                    <th>Detail</th>
                    <th>Keterangan</th>
                    <th>Gambar</th>
                </tr>
            </thead>
            <tbody>
                {% for t in data.transactions %}
                <tr>
                    <td>{{ t.date }}</td>
                    <td>{{ t.user }}</td>
                    {% if 'deposit' in t.type %}
                        <td class="deposit">MASUK</td>
                    {% elif 'withdraw' in t.type %}
                        <td class="withdraw">KELUAR</td>
                    {% else %}
                        <td style="color:#2196f3; font-weight:bold;">UPDATE</td>
                    {% endif %}
                    <td>
                        {% if 'money' in t.type %}
                            <span style="color:#4caf50; font-weight:bold;">$ {{ "{:,}".format(t.amount) }}</span>
                        {% elif t.type == 'update_item' %}
                            <span style="color:#2196f3; font-weight:bold;">Set &rarr; {{ t.amount }}x {{ t.item_name }}</span>
                        {% else %}
                            <span style="color:#ff9800; font-weight:bold;">{{ t.amount }}x {{ t.item_name }}</span>
                        {% endif %}
                    </td>
                    <td>{{ t.reason }}</td>
                    <td>
                        {% if t.image_url %}
                            <a href="{{ t.image_url }}" target="_blank">
                                <img src="{{ t.image_url }}" alt="Img" style="max-height: 40px; border-radius: 4px;">
                            </a>
                        {% else %}
                            -
                        {% endif %}
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="6" style="text-align:center;">Belum ada riwayat transaksi.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <script>
    function searchTable() {
        let input = document.getElementById("searchInput");
        let filter = input.value.toLowerCase();
        let table = document.getElementById("transactionTable");
        let tr = table.getElementsByTagName("tr");
        
        for (let i = 1; i < tr.length; i++) {
            tr[i].style.display = "none";
            let td = tr[i].getElementsByTagName("td");
            for (let j = 0; j < td.length; j++) {
                if (td[j]) {
                    let txtValue = td[j].textContent || td[j].innerText;
                    if (txtValue.toLowerCase().indexOf(filter) > -1) {
                        tr[i].style.display = "";
                        break;
                    }
                }
            }
        }
    }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    data = load_db()
    return render_template_string(HTML_TEMPLATE, data=data)

def run_flask():
    # Menjalankan Flask di thread terpisah agar tidak memblokir Discord Bot
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)


# ==========================================
# 3. DISCORD BOT COMMANDS
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def checkaccess(ctx):
    if ctx.author.guild_permissions.administrator:
        return True
    db = load_db()
    return ctx.author.id in db.get("authorized_users", [])

@bot.event
async def on_ready():
    print(f"✅ Bot Brankas login sebagai {bot.user}")
    print(f"🌐 Website berjalan di 116.206.196.110:5000")

@bot.command()
@commands.has_permissions(administrator=True)
async def addakses(ctx, member: discord.Member):
    """(Admin) Memberikan akses brankas kepada member."""
    db = load_db()
    if member.id not in db["authorized_users"]:
        db["authorized_users"].append(member.id)
        save_db(db)
        await ctx.send(f"✅ {member.mention} sekarang diizinkan mengakses brankas (deposit/withdraw).")
    else:
        await ctx.send(f"ℹ️ {member.mention} sudah memiliki akses.")

@bot.command()
@commands.has_permissions(administrator=True)
async def removeakses(ctx, member: discord.Member):
    """(Admin) Mencabut akses brankas dari member."""
    db = load_db()
    if member.id in db["authorized_users"]:
        db["authorized_users"].remove(member.id)
        save_db(db)
        await ctx.send(f"✅ Akses brankas untuk {member.mention} telah dicabut.")
    else:
        await ctx.send(f"ℹ️ {member.mention} memang tidak memiliki akses.")

@bot.command()
async def cekakses(ctx):
    """Melihat daftar anggota yang memiliki akses ke brankas."""
    db = load_db()
    authorized = db.get("authorized_users", [])
    
    if not authorized:
        embed = discord.Embed(title="🔐 Daftar Akses Brankas", description="Belum ada anggota khusus yang diberi akses (Saat ini hanya Administrator).", color=discord.Color.orange())
        return await ctx.send(embed=embed)
        
    mentions = [f"• <@{user_id}>" for user_id in authorized]
    mentions_str = "\n".join(mentions)
    
    # Batasi panjang string jika daftar terlalu panjang
    if len(mentions_str) > 2000:
        mentions_str = mentions_str[:1900] + "\n*...dan lainnya*"
        
    embed = discord.Embed(title="🔐 Daftar Akses Brankas", description=f"Anggota non-admin yang memiliki izin deposit & withdraw:\n\n{mentions_str}", color=discord.Color.blue())
    await ctx.send(embed=embed)

@bot.command()
async def deposit(ctx, amount: int, *, reason: str):
    """Menyimpan uang ke dalam brankas. Contoh: !deposit 50000 Setoran hasil patungan"""
    if not checkaccess(ctx):
        return await ctx.send("❌ Kamu tidak memiliki izin untuk mengakses brankas.")
    if amount <= 0:
        return await ctx.send("❌ Jumlah uang harus lebih dari $0!")

    image_url = ctx.message.attachments[0].url if ctx.message.attachments else None
    db = add_transaction(ctx.author.name, "deposit_money", amount, None, reason, image_url)
    new_balance = db["balance"]
    
    embed = discord.Embed(title="📥 DEPOSIT BERHASIL", color=discord.Color.green())
    embed.add_field(name="Jumlah", value=f"${amount:,}", inline=True)
    embed.add_field(name="Oleh", value=ctx.author.mention, inline=True)
    embed.add_field(name="Keterangan", value=reason, inline=False)
    embed.add_field(name="Saldo Brankas", value=f"**${new_balance:,}**", inline=False)
    embed.set_footer(text="Data telah disinkronisasi ke Website Brankas.")
    
    if image_url:
        embed.set_image(url=image_url)
    
    await ctx.send(embed=embed)

@bot.command()
async def withdraw(ctx, amount: int, *, reason: str):
    """Menarik uang dari brankas. Contoh: !withdraw 10000 Beli peluru"""
    if not checkaccess(ctx):
        return await ctx.send("❌ Kamu tidak memiliki izin untuk mengakses brankas.")
    db = load_db()
    
    if amount <= 0:
        return await ctx.send("❌ Jumlah tarikan harus lebih dari $0!")
    if amount > db["balance"]:
        return await ctx.send(f"❌ Saldo brankas tidak cukup! (Saldo saat ini: **${db['balance']:,}**)")

    image_url = ctx.message.attachments[0].url if ctx.message.attachments else None
    db = add_transaction(ctx.author.name, "withdraw_money", amount, None, reason, image_url)
    new_balance = db["balance"]
    
    embed = discord.Embed(title="📤 WITHDRAW BERHASIL", color=discord.Color.red())
    embed.add_field(name="Jumlah", value=f"${amount:,}", inline=True)
    embed.add_field(name="Oleh", value=ctx.author.mention, inline=True)
    embed.add_field(name="Keterangan", value=reason, inline=False)
    embed.add_field(name="Sisa Saldo Brankas", value=f"**${new_balance:,}**", inline=False)
    embed.set_footer(text="Data telah disinkronisasi ke Website Brankas.")
    
    if image_url:
        embed.set_image(url=image_url)
    
    await ctx.send(embed=embed)

@bot.command()
async def putitem(ctx, *, details: str):
    """Menyimpan barang (Bisa lebih dari 1). Contoh: !putitem 5 AK-47, 10 Vest | Hasil rampok"""
    if not checkaccess(ctx):
        return await ctx.send("❌ Kamu tidak memiliki izin untuk mengakses brankas.")

    if "|" in details:
        items_str, reason = details.split("|", 1)
        reason = reason.strip()
    else:
        items_str = details
        reason = "Tidak ada keterangan"

    image_url = ctx.message.attachments[0].url if ctx.message.attachments else None
    items_list = items_str.split(",")
    success_items = []

    for item_entry in items_list:
        item_entry = item_entry.strip()
        if not item_entry: continue
        
        parts = item_entry.split(maxsplit=1)
        if len(parts) < 2:
            await ctx.send(f"⚠️ Format salah pada: `{item_entry}`. Diabaikan. (Contoh: 5 AK-47)")
            continue
            
        amount_str, item_name = parts
        if not amount_str.isdigit() or int(amount_str) <= 0:
            await ctx.send(f"⚠️ Jumlah harus berupa angka > 0 pada: `{item_entry}`. Diabaikan.")
            continue
            
        amount = int(amount_str)
        item_name = item_name.strip()

        db = add_transaction(ctx.author.name, "deposit_item", amount, item_name, reason, image_url)
        current_qty = db["inventory"][item_name]
        success_items.append(f"**{item_name}** ({amount}x) - Total Brankas: {current_qty}x")

    if not success_items:
        return await ctx.send("❌ Tidak ada barang valid yang berhasil dimasukkan!")

    embed = discord.Embed(title="📦 DEPOSIT BARANG BERHASIL", color=discord.Color.green())
    embed.add_field(name="Barang Dimasukkan", value="\n".join(success_items), inline=False)
    embed.add_field(name="Oleh", value=ctx.author.mention, inline=True)
    embed.add_field(name="Keterangan", value=reason, inline=False)
    
    if image_url:
        embed.set_image(url=image_url)
    
    await ctx.send(embed=embed)

@bot.command()
async def takeitem(ctx, *, details: str):
    """Mengambil barang (Bisa lebih dari 1). Contoh: !takeitem 2 AK-47, 5 Vest | Buat perang"""
    if not checkaccess(ctx):
        return await ctx.send("❌ Kamu tidak memiliki izin untuk mengakses brankas.")

    if "|" in details:
        items_str, reason = details.split("|", 1)
        reason = reason.strip()
    else:
        items_str = details
        reason = "Tidak ada keterangan"

    image_url = ctx.message.attachments[0].url if ctx.message.attachments else None
    items_list = items_str.split(",")
    success_items = []

    for item_entry in items_list:
        item_entry = item_entry.strip()
        if not item_entry: continue
        
        parts = item_entry.split(maxsplit=1)
        if len(parts) < 2:
            await ctx.send(f"⚠️ Format salah pada: `{item_entry}`. Diabaikan. (Contoh: 2 AK-47)")
            continue
            
        amount_str, item_name = parts
        if not amount_str.isdigit() or int(amount_str) <= 0:
            await ctx.send(f"⚠️ Jumlah harus berupa angka > 0 pada: `{item_entry}`. Diabaikan.")
            continue
            
        amount = int(amount_str)
        item_name = item_name.strip()

        db = load_db()
        current_stock = db["inventory"].get(item_name, 0)
        if amount > current_stock:
            await ctx.send(f"❌ Stok tidak cukup untuk `{item_name}`! (Sisa: **{current_stock}x**). Diabaikan.")
            continue

        db = add_transaction(ctx.author.name, "withdraw_item", amount, item_name, reason, image_url)
        sisa_qty = db["inventory"].get(item_name, 0)
        success_items.append(f"**{item_name}** ({amount}x) - Sisa Brankas: {sisa_qty}x")

    if not success_items:
        return await ctx.send("❌ Tidak ada barang valid yang berhasil ditarik!")

    embed = discord.Embed(title="📤 WITHDRAW BARANG BERHASIL", color=discord.Color.red())
    embed.add_field(name="Barang Ditarik", value="\n".join(success_items), inline=False)
    embed.add_field(name="Oleh", value=ctx.author.mention, inline=True)
    embed.add_field(name="Keterangan", value=reason, inline=False)

    if image_url:
        embed.set_image(url=image_url)

    await ctx.send(embed=embed)

@bot.command()
async def updateitem(ctx):
    """Melihat informasi seluruh stok barang yang ada di dalam database."""
    db = load_db()
    inventory = db.get("inventory", {})

    if not inventory:
        embed = discord.Embed(title="📦 UPDATE STOK BARANG", description="*Brankas barang saat ini kosong.*", color=discord.Color.blue())
        return await ctx.send(embed=embed)

    embed = discord.Embed(title="📦 UPDATE STOK BARANG", color=discord.Color.blue())
    
    items_list = [f"• **{item}**: {qty}x" for item, qty in inventory.items()]
    items_str = "\n".join(items_list)
    
    # Mencegah error limit karakter pada Embed Field (maks. 1024 karakter)
    if len(items_str) > 1024:
        items_str = items_str[:1000] + "\n*...dan lainnya*"

    embed.add_field(name="Daftar Stok Saat Ini", value=items_str, inline=False)
    embed.set_footer(text="Data diambil langsung dari database brankas.")

    await ctx.send(embed=embed)

@bot.command()
async def ceksaldo(ctx):
    """Melihat informasi saldo saat ini dan link website."""
    db = load_db()
    embed = discord.Embed(
        title="🩸 BRANGKAS WT GHOST RUMAH KITA RP 🩸", 
        description="Pantau kas kita secara transparan.",
        color=discord.Color.dark_red()
    )
    embed.add_field(name="Total Uang", value=f"**${db['balance']:,}**", inline=False)
    
    # Ganti tulisan IP_VPS_KAMU dengan alamat IP dari VPS atau Domain kamu
    embed.add_field(name="🌐 Dashboard Website", value="[Klik di sini untuk lihat riwayat lengkap](116.206.196.110:5000)", inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def bantuan(ctx):
    """Menampilkan daftar semua perintah bot brankas."""
    embed = discord.Embed(title="📜 Bantuan Perintah Brankas Badside", color=discord.Color.dark_red())
    
    embed.add_field(
        name="🔐 Hak Akses", 
        value="`!addakses @user` - Memberi izin akses ke anggota (Admin)\n`!removeakses @user` - Mencabut izin akses (Admin)\n`!cekakses` - Melihat daftar anggota berizin", 
        inline=False
    )
    embed.add_field(
        name="💵 Brankas Uang", 
        value="`!deposit <jumlah> <alasan>` - Menyimpan uang\n`!withdraw <jumlah> <alasan>` - Menarik uang\n`!ceksaldo` - Cek total saldo uang saat ini", 
        inline=False
    )
    embed.add_field(
        name="📦 Brankas Barang", 
        value="`!putitem <jumlah> <barang> | <alasan>` - Menyimpan barang\n`!takeitem <jumlah> <barang> | <alasan>` - Menarik barang\n`!updateitem` - Melihat seluruh sisa stok barang", 
        inline=False
    )
    
    embed.set_footer(text="Catatan: Gunakan koma (,) untuk input >1 barang sekaligus. (Misal: !putitem 5 AK-47, 10 Vest | Rampok)")
    await ctx.send(embed=embed)

# ==========================================
# 4. MENJALANKAN BOT DAN WEBSITE
# ==========================================
if __name__ == '__main__':
    if not TOKEN or TOKEN == "":
        print("❌ ERROR: Token Discord belum diatur di file .env!")
    else:
        # Jalankan Flask Server di background (Thread baru)
        server_thread = threading.Thread(target=run_flask)
        server_thread.daemon = True
        server_thread.start()

        # Jalankan Discord Bot
        bot.run(TOKEN)
