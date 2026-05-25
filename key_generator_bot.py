"""
PIRATE SCRIPTS - BOT DISCORD v2.0
Versão otimizada para Render
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import os
import string
import random
from datetime import datetime, timedelta
import sys

# ============================================================
# CONFIGURAÇÕES
# ============================================================

OWNER_ID = 1460529634117550121
BOT_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()

if not BOT_TOKEN:
    print("❌ ERRO: DISCORD_TOKEN não definida!", file=sys.stderr)
    sys.exit(1)

DATABASE_FILE = "/tmp/pirate_keys.db"

# Cores
DEFAULT_COLOR = 0x4466FF
SUCCESS_COLOR = 0x00CC66
ERROR_COLOR = 0xFF3333
WARNING_COLOR = 0xFFAA00

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
                prefix TEXT DEFAULT 'PIRATE',
                created_at TEXT NOT NULL,
                expiration TEXT,
                uses INTEGER DEFAULT 0,
                active INTEGER DEFAULT 1,
                created_by TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                username TEXT,
                added_at TEXT NOT NULL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        defaults = [
            ("color", str(DEFAULT_COLOR)),
            ("banner_url", "https://files.manuscdn.com/user_upload_by_module/session_file/310519663693040824/BUQsYbGzBioWOJaK.png"),
            ("logo_url", "https://files.manuscdn.com/user_upload_by_module/session_file/310519663693040824/LkVCffyUPzuIouwX.png"),
            ("status", "Gerando Chaves - Pirate Scripts 🔒"),
        ]
        for k, v in defaults:
            c.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES (?, ?)", (k, v))

        conn.commit()
        conn.close()
        print("✅ Banco de dados inicializado", flush=True)
    except Exception as e:
        print(f"❌ Erro ao inicializar banco: {e}", file=sys.stderr, flush=True)
        raise

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

def generate_plano_key(prefix="PIRATE", valor=30, unidade="dias"):
    """Gera key plano."""
    unidade_map = {"anual": "A", "mensal": "M", "diario": "D", "dias": "D", "horas": "H"}
    sufixo = unidade_map.get(unidade, "D")
    prefix = prefix.upper() or "PIRATE"
    suffix = generate_random_suffix(5)
    return f"{prefix}-{valor}{sufixo}-{suffix}"

def generate_premium_key(name):
    """Gera key premium."""
    import re
    clean = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
    return clean or "premium"

def calculate_expiration(valor, unidade):
    """Calcula expiração."""
    now = datetime.now()
    if unidade in ["anual", "ano"]:
        return now + timedelta(days=valor * 365)
    elif unidade in ["mensal", "mes"]:
        return now + timedelta(days=valor * 30)
    elif unidade in ["horas", "hora"]:
        return now + timedelta(hours=valor)
    else:
        return now + timedelta(days=valor)

# ============================================================
# BOT DISCORD
# ============================================================

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ============================================================
# VIEWS
# ============================================================

class PainelSelect(discord.ui.Select):
    """Menu de seleção do painel."""

    def __init__(self):
        options = [
            discord.SelectOption(label="Dashboard", description="Visualize as keys", emoji="📊", value="dashboard"),
            discord.SelectOption(label="Gerador", description="Gere novas keys", emoji="🔑", value="gerador"),
            discord.SelectOption(label="Permissões", description="Gerencie acesso", emoji="🛡️", value="permissoes"),
            discord.SelectOption(label="Visual", description="Aparência do bot", emoji="🎨", value="visual"),
        ]
        super().__init__(placeholder="Selecione uma seção...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if not has_permission(interaction.user.id):
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
            return

        choice = self.values[0]

        if choice == "dashboard":
            await show_dashboard(interaction)
        elif choice == "gerador":
            await show_gerador(interaction)
        elif choice == "permissoes":
            await show_permissoes(interaction)
        elif choice == "visual":
            await show_visual(interaction)


class PainelView(discord.ui.View):
    """View do painel."""
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(PainelSelect())


# ============================================================
# DASHBOARD
# ============================================================

async def show_dashboard(interaction: discord.Interaction):
    """Mostra dashboard."""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM keys ORDER BY created_at DESC LIMIT 10")
        keys = c.fetchall()
        conn.close()

        embed = discord.Embed(
            title="📊 Dashboard",
            description="Suas keys ativas",
            color=DEFAULT_COLOR,
            timestamp=datetime.now()
        )

        if keys:
            for k in keys:
                embed.add_field(
                    name=f"🔑 {k['key']}",
                    value=f"Tipo: {k['key_type']} | Usos: {k['uses']}",
                    inline=False
                )
        else:
            embed.add_field(name="Nenhuma key", value="Crie uma nova key!", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        print(f"Erro no dashboard: {e}", flush=True)
        await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)


# ============================================================
# GERADOR
# ============================================================

class GerarPlanoModal(discord.ui.Modal, title="🔑 Gerar Key Plano"):
    prefixo = discord.ui.TextInput(label="Prefixo", placeholder="PIRATE", required=False, max_length=20)
    quantidade = discord.ui.TextInput(label="Quantidade (1-10)", placeholder="1", required=True, max_length=2)
    valor = discord.ui.TextInput(label="Valor", placeholder="30", required=True, max_length=5)
    unidade = discord.ui.TextInput(label="Unidade: diario/mensal/anual", placeholder="diario", required=True, max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            prefix = self.prefixo.value or "PIRATE"
            qtd = int(self.quantidade.value)
            val = int(self.valor.value)
            unit = self.unidade.value.lower()

            if qtd < 1 or qtd > 10:
                await interaction.response.send_message("❌ Quantidade deve ser 1-10", ephemeral=True)
                return

            expiration = calculate_expiration(val, unit)
            conn = get_db()
            c = conn.cursor()
            keys_geradas = []

            for _ in range(qtd):
                new_key = generate_plano_key(prefix, val, unit)
                c.execute(
                    "INSERT INTO keys (key, key_type, prefix, created_at, expiration, uses, active, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (new_key, "plano", prefix, datetime.now().isoformat(), expiration.isoformat(), 0, 1, str(interaction.user.id))
                )
                keys_geradas.append(new_key)

            conn.commit()
            conn.close()

            embed = discord.Embed(title="✅ Keys Geradas!", color=SUCCESS_COLOR)
            embed.add_field(name="🔑 Keys", value="\n".join([f"`{k}`" for k in keys_geradas]), inline=False)
            embed.add_field(name="Validade", value=f"{val} {unit}", inline=True)

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)


class GerarPremiumModal(discord.ui.Modal, title="👑 Gerar Key Premium"):
    nome = discord.ui.TextInput(label="Nome da key", placeholder="piratepremium", required=True, max_length=50)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            new_key = generate_premium_key(self.nome.value)
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT id FROM keys WHERE key = ?", (new_key,))
            if c.fetchone():
                conn.close()
                await interaction.response.send_message(f"❌ Key `{new_key}` já existe!", ephemeral=True)
                return

            c.execute(
                "INSERT INTO keys (key, key_type, prefix, created_at, expiration, uses, active, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (new_key, "premium", "PREMIUM", datetime.now().isoformat(), None, 0, 1, str(interaction.user.id))
            )
            conn.commit()
            conn.close()

            embed = discord.Embed(title="👑 Key Premium Criada!", color=0xFFD700)
            embed.add_field(name="🔑 Key", value=f"`{new_key}`", inline=False)
            embed.add_field(name="Validade", value="Permanente", inline=True)

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)


class GeradorView(discord.ui.View):
    """View do gerador."""
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="🔑 Key Plano", style=discord.ButtonStyle.primary)
    async def gen_plano(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GerarPlanoModal())

    @discord.ui.button(label="👑 Key Premium", style=discord.ButtonStyle.success)
    async def gen_premium(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GerarPremiumModal())


async def show_gerador(interaction: discord.Interaction):
    """Mostra gerador."""
    embed = discord.Embed(
        title="🔑 Gerador de Keys",
        description="Escolha o tipo de key",
        color=DEFAULT_COLOR
    )
    await interaction.response.send_message(embed=embed, view=GeradorView(), ephemeral=True)


# ============================================================
# PERMISSÕES
# ============================================================

async def show_permissoes(interaction: discord.Interaction):
    """Mostra permissões."""
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ Apenas o dono!", ephemeral=True)
        return

    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM permissions")
        perms = c.fetchall()
        conn.close()

        embed = discord.Embed(title="🛡️ Permissões", color=DEFAULT_COLOR)
        if perms:
            embed.add_field(
                name="Usuários",
                value="\n".join([f"• <@{p['user_id']}>" for p in perms]),
                inline=False
            )
        else:
            embed.add_field(name="Usuários", value="Nenhum", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)


# ============================================================
# VISUAL
# ============================================================

async def show_visual(interaction: discord.Interaction):
    """Mostra visual."""
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ Apenas o dono!", ephemeral=True)
        return

    embed = discord.Embed(
        title="🎨 Configurações Visuais",
        description="Personalize o bot",
        color=DEFAULT_COLOR
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ============================================================
# PAINEL PRINCIPAL
# ============================================================

async def show_main_panel(interaction: discord.Interaction):
    """Mostra painel principal."""
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
        embed.set_footer(text="Pirate Scripts v2.0")

        await interaction.response.send_message(embed=embed, view=PainelView(), ephemeral=True)
    except Exception as e:
        print(f"Erro no painel: {e}", flush=True)
        await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)


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
    activity = discord.Activity(type=discord.ActivityType.playing, name="Gerando Chaves - Pirate Scripts 🔒")
    await bot.change_presence(activity=activity)
    print("🏴‍☠️ Bot pronto!", flush=True)


# ============================================================
# COMANDOS
# ============================================================

@bot.tree.command(name="painel", description="Abre o painel de controle")
async def painel(interaction: discord.Interaction):
    """Comando painel."""
    if not has_permission(interaction.user.id):
        await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
        return
    await show_main_panel(interaction)


@bot.tree.command(name="status_bot", description="Status do sistema")
async def status_bot(interaction: discord.Interaction):
    """Status do bot."""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as total FROM keys")
        total = c.fetchone()["total"]
        conn.close()

        embed = discord.Embed(title="📡 Status", color=SUCCESS_COLOR)
        embed.add_field(name="🤖 Bot", value="✅ Online", inline=True)
        embed.add_field(name="🗄️ Banco", value="✅ OK", inline=True)
        embed.add_field(name="📦 Keys", value=str(total), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    try:
        print("🚀 Iniciando Pirate Scripts Bot v2.0...", flush=True)
        init_database()
        print(f"🔑 Token: {BOT_TOKEN[:20]}...", flush=True)
        bot.run(BOT_TOKEN)
    except Exception as e:
        print(f"❌ ERRO CRÍTICO: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
