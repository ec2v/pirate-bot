#!/usr/bin/env python3
"""
PIRATE SCRIPTS - BOT DISCORD v2.0
Versão ultra simplificada para Render
"""

import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import os
import string
import random
from datetime import datetime, timedelta
import sys

print("🚀 Iniciando imports...", flush=True)

# ============================================================
# CONFIGURAÇÕES
# ============================================================

OWNER_ID = 1460529634117550121
BOT_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()

if not BOT_TOKEN:
    print("❌ ERRO: DISCORD_TOKEN não definida!", file=sys.stderr, flush=True)
    sys.exit(1)

DATABASE_FILE = "/tmp/pirate_keys.db"
DEFAULT_COLOR = 0x4466FF

print(f"✅ Token carregado: {BOT_TOKEN[:15]}...", flush=True)
print(f"✅ Banco de dados: {DATABASE_FILE}", flush=True)

# ============================================================
# BANCO DE DADOS
# ============================================================

def init_database():
    """Inicializa o banco de dados."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                key_type TEXT NOT NULL DEFAULT 'plano',
                created_at TEXT NOT NULL,
                expiration TEXT,
                uses INTEGER DEFAULT 0,
                active INTEGER DEFAULT 1
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL
            )
        """)

        conn.commit()
        conn.close()
        print("✅ Banco de dados inicializado", flush=True)
        return True
    except Exception as e:
        print(f"❌ Erro ao inicializar banco: {e}", file=sys.stderr, flush=True)
        return False

def get_db():
    """Retorna conexão com o banco."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def has_permission(user_id: int) -> bool:
    """Verifica permissão do usuário."""
    if user_id == OWNER_ID:
        return True
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM permissions WHERE user_id = ?", (str(user_id),))
        result = c.fetchone()
        conn.close()
        return result is not None
    except:
        return False

# ============================================================
# FUNÇÕES DE GERAÇÃO
# ============================================================

def generate_random_suffix(length=5):
    """Gera sufixo aleatório."""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))

def generate_plano_key(prefix="PIRATE", valor=30, unidade="D"):
    """Gera key plano."""
    suffix = generate_random_suffix(5)
    return f"{prefix.upper()}-{valor}{unidade.upper()}-{suffix}"

def generate_premium_key(name):
    """Gera key premium."""
    import re
    clean = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
    return clean or "premium"

# ============================================================
# BOT DISCORD
# ============================================================

print("🤖 Criando bot Discord...", flush=True)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ============================================================
# EVENTOS
# ============================================================

@bot.event
async def on_ready():
    """Evento de pronto."""
    print(f"✅ Bot conectado como {bot.user}", flush=True)
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos sincronizados!", flush=True)
    except Exception as e:
        print(f"⚠️ Erro ao sincronizar: {e}", flush=True)

    # Atualizar status
    activity = discord.Activity(
        type=discord.ActivityType.playing,
        name="Gerando Chaves - Pirate Scripts 🔒"
    )
    await bot.change_presence(activity=activity)
    print("🏴‍☠️ Bot pronto e online!", flush=True)

# ============================================================
# COMANDOS
# ============================================================

@bot.tree.command(name="painel", description="Abre o painel de controle")
async def painel(interaction: discord.Interaction):
    """Comando painel."""
    if not has_permission(interaction.user.id):
        await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
        return

    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as total FROM keys")
        total = c.fetchone()["total"]
        conn.close()

        embed = discord.Embed(
            title="🏴‍☠️ Pirate Scripts — Painel de Controle",
            description="Bem-vindo ao painel central",
            color=DEFAULT_COLOR,
            timestamp=datetime.now()
        )
        embed.add_field(name="📦 Total de Keys", value=str(total), inline=True)
        embed.add_field(name="🔐 Status", value="✅ Online", inline=True)
        embed.set_footer(text="Pirate Scripts v2.0")

        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        print(f"Erro no painel: {e}", flush=True)
        await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)


@bot.tree.command(name="gerar_plano", description="Gera uma key plano")
@app_commands.describe(
    prefixo="Prefixo da key (padrão: PIRATE)",
    valor="Quantidade de dias/meses/anos",
    unidade="D (dias), M (meses), A (anos), H (horas)"
)
async def gerar_plano(
    interaction: discord.Interaction,
    valor: int,
    unidade: str = "D",
    prefixo: str = "PIRATE"
):
    """Gera key plano."""
    if not has_permission(interaction.user.id):
        await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
        return

    try:
        new_key = generate_plano_key(prefixo, valor, unidade)
        
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO keys (key, key_type, created_at, uses, active) VALUES (?, ?, ?, ?, ?)",
            (new_key, "plano", datetime.now().isoformat(), 0, 1)
        )
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="✅ Key Plano Gerada!",
            color=0x00CC66,
            timestamp=datetime.now()
        )
        embed.add_field(name="🔑 Key", value=f"`{new_key}`", inline=False)
        embed.add_field(name="⏱️ Validade", value=f"{valor} {unidade}", inline=True)
        embed.add_field(name="📝 Tipo", value="Plano", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        print(f"Erro ao gerar key: {e}", flush=True)
        await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)


@bot.tree.command(name="gerar_premium", description="Gera uma key premium")
@app_commands.describe(nome="Nome da key premium")
async def gerar_premium(interaction: discord.Interaction, nome: str):
    """Gera key premium."""
    if not has_permission(interaction.user.id):
        await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
        return

    try:
        new_key = generate_premium_key(nome)
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute("SELECT id FROM keys WHERE key = ?", (new_key,))
        if c.fetchone():
            conn.close()
            await interaction.response.send_message(f"❌ Key `{new_key}` já existe!", ephemeral=True)
            return

        c.execute(
            "INSERT INTO keys (key, key_type, created_at, uses, active) VALUES (?, ?, ?, ?, ?)",
            (new_key, "premium", datetime.now().isoformat(), 0, 1)
        )
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="👑 Key Premium Gerada!",
            color=0xFFD700,
            timestamp=datetime.now()
        )
        embed.add_field(name="🔑 Key", value=f"`{new_key}`", inline=False)
        embed.add_field(name="⏱️ Validade", value="Permanente", inline=True)
        embed.add_field(name="📝 Tipo", value="Premium", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        print(f"Erro ao gerar key premium: {e}", flush=True)
        await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)


@bot.tree.command(name="listar_keys", description="Lista todas as keys")
async def listar_keys(interaction: discord.Interaction):
    """Lista todas as keys."""
    if not has_permission(interaction.user.id):
        await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
        return

    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM keys ORDER BY created_at DESC LIMIT 20")
        keys = c.fetchall()
        conn.close()

        embed = discord.Embed(
            title="📋 Suas Keys",
            color=DEFAULT_COLOR,
            timestamp=datetime.now()
        )

        if keys:
            for k in keys:
                status = "✅ Ativa" if k["active"] else "❌ Inativa"
                embed.add_field(
                    name=f"🔑 {k['key']}",
                    value=f"Tipo: {k['key_type']} | Usos: {k['uses']} | {status}",
                    inline=False
                )
        else:
            embed.add_field(name="Nenhuma key", value="Crie uma nova key!", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        print(f"Erro ao listar keys: {e}", flush=True)
        await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)


@bot.tree.command(name="status", description="Status do bot")
async def status(interaction: discord.Interaction):
    """Status do bot."""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as total FROM keys")
        total = c.fetchone()["total"]
        conn.close()

        embed = discord.Embed(title="📡 Status do Bot", color=0x00CC66)
        embed.add_field(name="🤖 Bot", value="✅ Online", inline=True)
        embed.add_field(name="🗄️ Banco", value="✅ OK", inline=True)
        embed.add_field(name="📦 Keys", value=str(total), inline=True)
        embed.set_footer(text="Pirate Scripts v2.0")

        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        print(f"Erro no status: {e}", flush=True)
        await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    try:
        print("=" * 60, flush=True)
        print("🏴‍☠️  PIRATE SCRIPTS - BOT DISCORD v2.0", flush=True)
        print("=" * 60, flush=True)
        
        if not init_database():
            sys.exit(1)

        print(f"🔑 Token: {BOT_TOKEN[:20]}...", flush=True)
        print("🚀 Conectando ao Discord...", flush=True)
        print("=" * 60, flush=True)
        
        bot.run(BOT_TOKEN)
    except KeyboardInterrupt:
        print("\n⏹️  Bot interrompido pelo usuário", flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"❌ ERRO CRÍTICO: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
