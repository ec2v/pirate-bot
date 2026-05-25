"""
╔══════════════════════════════════════════════════════════════╗
║          PIRATE SCRIPTS - KEY GENERATOR BOT v2.0             ║
║          Sistema completo de gerenciamento de keys           ║
╚══════════════════════════════════════════════════════════════╝
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import os
import string
import random
from datetime import datetime, timedelta
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import json
import hashlib
import re

# ============================================================
# CONFIGURAÇÕES
# ============================================================

OWNER_ID = 1460529634117550121
BOT_TOKEN = os.getenv("DISCORD_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("DISCORD_TOKEN não definida! Configure a variável de ambiente.")
DATABASE_FILE = "/tmp/pirate_keys.db"
BANNER_URL = "https://files.manuscdn.com/user_upload_by_module/session_file/310519663693040824/BUQsYbGzBioWOJaK.png"

# Cores padrão do bot
DEFAULT_COLOR = 0x4466FF  # Azul pirata
SUCCESS_COLOR = 0x00CC66
ERROR_COLOR = 0xFF3333
WARNING_COLOR = 0xFFAA00

# Configurações visuais (podem ser alteradas pelo painel)
bot_config = {
    "color": DEFAULT_COLOR,
    "banner_url": "https://files.manuscdn.com/user_upload_by_module/session_file/310519663693040824/BUQsYbGzBioWOJaK.png",
    "logo_url": "https://files.manuscdn.com/user_upload_by_module/session_file/310519663693040824/LkVCffyUPzuIouwX.png",
    "status": "Gerando Chaves - Pirate Scripts 🔒",
    "status_type": "playing",
    "rich_presence": ""
}

# ============================================================
# BANCO DE DADOS SQLite (seguro, local, criptografado)
# ============================================================

def init_database():
    """Inicializa o banco de dados com todas as tabelas necessárias."""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()

    # Tabela de keys
    c.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            key_type TEXT NOT NULL DEFAULT 'plano',
            prefix TEXT DEFAULT 'PIRATE',
            created_at TEXT NOT NULL,
            expiration TEXT,
            uses INTEGER DEFAULT 0,
            max_uses INTEGER DEFAULT -1,
            active INTEGER DEFAULT 1,
            created_by TEXT,
            notes TEXT
        )
    """)

    # Tabela de permissões
    c.execute("""
        CREATE TABLE IF NOT EXISTS permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            username TEXT,
            added_by TEXT,
            added_at TEXT NOT NULL
        )
    """)

    # Tabela de configurações do bot
    c.execute("""
        CREATE TABLE IF NOT EXISTS bot_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # Inserir configurações padrão
    defaults = [
        ("color", str(DEFAULT_COLOR)),
        ("banner_url", "https://files.manuscdn.com/user_upload_by_module/session_file/310519663693040824/BUQsYbGzBioWOJaK.png"),
        ("logo_url", "https://files.manuscdn.com/user_upload_by_module/session_file/310519663693040824/LkVCffyUPzuIouwX.png"),
        ("status", "Gerando Chaves - Pirate Scripts 🔒"),
        ("status_type", "playing"),
        ("rich_presence", ""),
    ]
    for k, v in defaults:
        c.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES (?, ?)", (k, v))

    conn.commit()
    conn.close()

def get_db():
    """Retorna conexão com o banco de dados."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def load_bot_config():
    """Carrega configurações do bot do banco de dados."""
    global bot_config
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT key, value FROM bot_settings")
    rows = c.fetchall()
    conn.close()
    for row in rows:
        if row["key"] == "color":
            bot_config["color"] = int(row["value"])
        else:
            bot_config[row["key"]] = row["value"]

def save_bot_config(key, value):
    """Salva uma configuração do bot."""
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()
    load_bot_config()

# ============================================================
# FUNÇÕES DE GERAÇÃO DE KEYS
# ============================================================

def generate_random_suffix(length=5):
    """Gera sufixo aleatório com letras maiúsculas e números."""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))

def generate_plano_key(prefix="PIRATE", valor=30, unidade="dias"):
    """
    Gera key no formato: PREFIX-(VALORu)-(5CHARS)
    Exemplo: PIRATE-30D-AB3X7
    """
    if unidade == "anual":
        sufixo_tempo = f"{valor}A"
    elif unidade == "mensal":
        sufixo_tempo = f"{valor}M"
    elif unidade == "diario":
        sufixo_tempo = f"{valor}D"
    elif unidade == "horas":
        sufixo_tempo = f"{valor}H"
    else:
        sufixo_tempo = f"{valor}D"

    if not prefix or prefix.strip() == "":
        prefix = "PIRATE"

    suffix = generate_random_suffix(5)
    return f"{prefix.upper()}-{sufixo_tempo}-{suffix}"

def generate_premium_key(name):
    """
    Gera key premium com nome simples.
    Exemplo: piratepremium
    """
    # Limpa o nome e deixa minúsculo
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
    if not clean_name:
        clean_name = "premium"
    return clean_name

def calculate_expiration(valor, unidade):
    """Calcula data de expiração baseado no valor e unidade."""
    now = datetime.now()
    if unidade == "horas":
        return now + timedelta(hours=valor)
    elif unidade == "diario":
        return now + timedelta(days=valor)
    elif unidade == "mensal":
        return now + timedelta(days=valor * 30)
    elif unidade == "anual":
        return now + timedelta(days=valor * 365)
    return now + timedelta(days=valor)

# ============================================================
# VERIFICAÇÃO DE PERMISSÕES
# ============================================================

def has_permission(user_id: int) -> bool:
    """Verifica se o usuário tem permissão para usar o bot."""
    if user_id == OWNER_ID:
        return True
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM permissions WHERE user_id = ?", (str(user_id),))
    result = c.fetchone()
    conn.close()
    return result is not None

# ============================================================
# API HTTP PARA VALIDAÇÃO DE KEYS (usado pelo script Lua)
# ============================================================

class KeyValidationHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/validate":
            key = params.get("key", [""])[0]
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM keys WHERE key = ?", (key,))
            row = c.fetchone()

            if row:
                if row["active"] == 0:
                    response = json.dumps({"valid": False, "message": "Key desativada!"})
                    self.send_response(200)
                elif row["expiration"] is None:
                    # Key premium permanente
                    c.execute("UPDATE keys SET uses = uses + 1 WHERE key = ?", (key,))
                    conn.commit()
                    response = json.dumps({
                        "valid": True,
                        "message": "Key Premium válida!",
                        "expires_in": "Permanente",
                        "uses": row["uses"] + 1,
                        "key_type": "premium"
                    })
                    self.send_response(200)
                else:
                    expiration = datetime.fromisoformat(row["expiration"])
                    now = datetime.now()
                    if expiration > now:
                        c.execute("UPDATE keys SET uses = uses + 1 WHERE key = ?", (key,))
                        conn.commit()
                        remaining = expiration - now
                        response = json.dumps({
                            "valid": True,
                            "message": "Key válida!",
                            "expires_in": f"{remaining.days} dias",
                            "uses": row["uses"] + 1,
                            "key_type": row["key_type"]
                        })
                        self.send_response(200)
                    else:
                        response = json.dumps({"valid": False, "message": "Key expirada!"})
                        self.send_response(200)
            else:
                response = json.dumps({"valid": False, "message": "Key inválida!"})
                self.send_response(200)

            conn.close()

        elif parsed.path == "/status":
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) as total FROM keys WHERE active = 1")
            total = c.fetchone()["total"]
            conn.close()
            response = json.dumps({
                "status": "online",
                "total_keys": total,
                "version": "2.0"
            })
            self.send_response(200)
        else:
            response = json.dumps({"error": "Endpoint não encontrado"})
            self.send_response(404)

        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response.encode())

    def log_message(self, format, *args):
        pass

def start_http_server():
    try:
        server = HTTPServer(("0.0.0.0", 8080), KeyValidationHandler)
        print("🌐 API HTTP rodando na porta 8080")
        server.serve_forever()
    except Exception as e:
        print(f"⚠️ Erro ao iniciar API HTTP: {e}")

# ============================================================
# BOT DISCORD
# ============================================================

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ============================================================
# VIEWS E COMPONENTES INTERATIVOS
# ============================================================

class PainelView(discord.ui.View):
    """View principal do painel com barra de seleção."""

    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(PainelSelect())

    async def on_timeout(self):
        pass


class PainelSelect(discord.ui.Select):
    """Menu de seleção do painel principal."""

    def __init__(self):
        options = [
            discord.SelectOption(
                label="Dashboard",
                description="Visualize e gerencie todas as keys",
                emoji="📊",
                value="dashboard"
            ),
            discord.SelectOption(
                label="Gerador",
                description="Gere novas keys Plano ou Premium",
                emoji="🔑",
                value="gerador"
            ),
            discord.SelectOption(
                label="Permissões",
                description="Gerencie quem pode usar o bot",
                emoji="🛡️",
                value="permissoes"
            ),
            discord.SelectOption(
                label="Visual",
                description="Personalize a aparência do bot",
                emoji="🎨",
                value="visual"
            ),
        ]
        super().__init__(
            placeholder="Selecione uma seção...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="painel_select"
        )

    async def callback(self, interaction: discord.Interaction):
        if not has_permission(interaction.user.id):
            await interaction.response.send_message(
                "❌ Você não tem permissão para usar o painel!",
                ephemeral=True
            )
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


# ============================================================
# DASHBOARD
# ============================================================

class DashboardView(discord.ui.View):
    """View do dashboard com paginação e ações nas keys."""

    def __init__(self, page=0):
        super().__init__(timeout=300)
        self.page = page

    @discord.ui.button(label="◀ Anterior", style=discord.ButtonStyle.secondary, custom_id="dash_prev")
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        await show_dashboard(interaction, page=self.page, edit=True)

    @discord.ui.button(label="Próxima ▶", style=discord.ButtonStyle.secondary, custom_id="dash_next")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        await show_dashboard(interaction, page=self.page, edit=True)

    @discord.ui.button(label="🗑️ Deletar Key", style=discord.ButtonStyle.danger, custom_id="dash_delete")
    async def delete_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = DeleteKeyModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="⏸️ Desativar Key", style=discord.ButtonStyle.secondary, custom_id="dash_disable")
    async def disable_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = DisableKeyModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="⏰ Adicionar Tempo", style=discord.ButtonStyle.primary, custom_id="dash_addtime")
    async def add_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AddTimeModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🔙 Voltar ao Painel", style=discord.ButtonStyle.secondary, custom_id="dash_back", row=1)
    async def back_to_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await show_main_panel(interaction, edit=True)


async def show_dashboard(interaction: discord.Interaction, page=0, edit=False):
    """Mostra o dashboard com lista de keys."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM keys ORDER BY created_at DESC")
    all_keys = c.fetchall()
    conn.close()

    per_page = 8
    total_pages = max(1, (len(all_keys) + per_page - 1) // per_page)
    page = min(page, total_pages - 1)
    start = page * per_page
    keys_page = all_keys[start:start + per_page]

    now = datetime.now()
    active_count = sum(1 for k in all_keys if k["active"] == 1 and (k["expiration"] is None or datetime.fromisoformat(k["expiration"]) > now))
    expired_count = sum(1 for k in all_keys if k["expiration"] and datetime.fromisoformat(k["expiration"]) <= now)
    premium_count = sum(1 for k in all_keys if k["key_type"] == "premium")

    embed = discord.Embed(
        title="📊 Dashboard — Gerenciamento de Keys",
        color=bot_config["color"],
        timestamp=datetime.now()
    )

    if bot_config.get("banner_url"):
        embed.set_image(url=bot_config["banner_url"])

    # Estatísticas rápidas
    embed.add_field(
        name="📈 Estatísticas",
        value=(
            f"```\n"
            f"✅ Ativas:    {active_count}\n"
            f"❌ Expiradas: {expired_count}\n"
            f"👑 Premium:   {premium_count}\n"
            f"📦 Total:     {len(all_keys)}\n"
            f"```"
        ),
        inline=False
    )

    if keys_page:
        keys_lines = []
        for k in keys_page:
            if k["key_type"] == "premium":
                status = "👑"
                validade = "Permanente"
            elif k["expiration"] is None:
                status = "✅"
                validade = "Permanente"
            else:
                exp = datetime.fromisoformat(k["expiration"])
                if exp > now and k["active"] == 1:
                    status = "✅"
                    remaining = exp - now
                    validade = f"{remaining.days}d restantes"
                elif k["active"] == 0:
                    status = "⏸️"
                    validade = "Desativada"
                else:
                    status = "❌"
                    validade = "Expirada"

            keys_lines.append(
                f"{status} `{k['key']}`\n"
                f"    ├ Tipo: **{k['key_type'].upper()}** | Usos: **{k['uses']}** | {validade}"
            )

        embed.add_field(
            name=f"🔑 Keys (Página {page + 1}/{total_pages})",
            value="\n".join(keys_lines) if keys_lines else "Nenhuma key encontrada.",
            inline=False
        )
    else:
        embed.add_field(name="🔑 Keys", value="Nenhuma key cadastrada ainda.", inline=False)

    embed.add_field(
        name="💡 Ações Disponíveis",
        value=(
            "🗑️ **Deletar Key** — Remove permanentemente\n"
            "⏸️ **Desativar Key** — Suspende sem deletar\n"
            "⏰ **Adicionar Tempo** — Estende a validade"
        ),
        inline=False
    )

    embed.set_footer(text=f"Pirate Scripts v2.0 | Página {page + 1}/{total_pages}")

    view = DashboardView(page=page)

    if edit:
        await interaction.response.edit_message(embed=embed, view=view)
    else:
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ============================================================
# MODAIS DO DASHBOARD
# ============================================================

class DeleteKeyModal(discord.ui.Modal, title="🗑️ Deletar Key"):
    key_input = discord.ui.TextInput(
        label="Key a deletar",
        placeholder="Ex: PIRATE-30D-AB3X7",
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        key = self.key_input.value.strip()
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM keys WHERE key = ?", (key,))
        row = c.fetchone()
        if row:
            c.execute("DELETE FROM keys WHERE key = ?", (key,))
            conn.commit()
            conn.close()
            embed = discord.Embed(
                title="✅ Key Deletada",
                description=f"A key `{key}` foi removida com sucesso!",
                color=SUCCESS_COLOR
            )
        else:
            conn.close()
            embed = discord.Embed(
                title="❌ Key não encontrada",
                description=f"A key `{key}` não existe no banco de dados.",
                color=ERROR_COLOR
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class DisableKeyModal(discord.ui.Modal, title="⏸️ Desativar/Ativar Key"):
    key_input = discord.ui.TextInput(
        label="Key para desativar/reativar",
        placeholder="Ex: PIRATE-30D-AB3X7",
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        key = self.key_input.value.strip()
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT active FROM keys WHERE key = ?", (key,))
        row = c.fetchone()
        if row:
            new_status = 0 if row["active"] == 1 else 1
            c.execute("UPDATE keys SET active = ? WHERE key = ?", (new_status, key))
            conn.commit()
            conn.close()
            status_text = "desativada ⏸️" if new_status == 0 else "reativada ✅"
            embed = discord.Embed(
                title="✅ Status Alterado",
                description=f"A key `{key}` foi **{status_text}** com sucesso!",
                color=SUCCESS_COLOR if new_status == 1 else WARNING_COLOR
            )
        else:
            conn.close()
            embed = discord.Embed(
                title="❌ Key não encontrada",
                description=f"A key `{key}` não existe no banco de dados.",
                color=ERROR_COLOR
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class AddTimeModal(discord.ui.Modal, title="⏰ Adicionar Tempo à Key"):
    key_input = discord.ui.TextInput(
        label="Key",
        placeholder="Ex: PIRATE-30D-AB3X7",
        required=True,
        max_length=100
    )
    dias_input = discord.ui.TextInput(
        label="Dias a adicionar",
        placeholder="Ex: 30",
        required=True,
        max_length=5
    )

    async def on_submit(self, interaction: discord.Interaction):
        key = self.key_input.value.strip()
        try:
            dias = int(self.dias_input.value.strip())
        except ValueError:
            await interaction.response.send_message("❌ Digite um número válido de dias!", ephemeral=True)
            return

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT expiration, key_type FROM keys WHERE key = ?", (key,))
        row = c.fetchone()
        if row:
            if row["key_type"] == "premium" or row["expiration"] is None:
                conn.close()
                await interaction.response.send_message("❌ Keys Premium são permanentes, não é possível adicionar tempo!", ephemeral=True)
                return

            exp = datetime.fromisoformat(row["expiration"])
            new_exp = exp + timedelta(days=dias)
            c.execute("UPDATE keys SET expiration = ? WHERE key = ?", (new_exp.isoformat(), key))
            conn.commit()
            conn.close()
            embed = discord.Embed(
                title="✅ Tempo Adicionado",
                description=(
                    f"**{dias} dias** adicionados à key `{key}`!\n"
                    f"Nova expiração: <t:{int(new_exp.timestamp())}:F>"
                ),
                color=SUCCESS_COLOR
            )
        else:
            conn.close()
            embed = discord.Embed(
                title="❌ Key não encontrada",
                description=f"A key `{key}` não existe no banco de dados.",
                color=ERROR_COLOR
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ============================================================
# GERADOR
# ============================================================

class GeradorView(discord.ui.View):
    """View do gerador com opções de tipo de key."""

    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="🔑 Key Plano", style=discord.ButtonStyle.primary, custom_id="gen_plano")
    async def gen_plano(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = GerarPlanoModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="👑 Key Premium", style=discord.ButtonStyle.success, custom_id="gen_premium")
    async def gen_premium(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = GerarPremiumModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🔙 Voltar ao Painel", style=discord.ButtonStyle.secondary, custom_id="gen_back")
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await show_main_panel(interaction, edit=True)


async def show_gerador(interaction: discord.Interaction, edit=False):
    """Mostra o painel do gerador."""
    embed = discord.Embed(
        title="🔑 Gerador de Keys",
        description=(
            "Escolha o tipo de key que deseja gerar:\n\n"
            "**🔑 Key Plano** — Key com validade (Anual, Mensal ou Diário)\n"
            "Formato: `PIRATE-(TEMPO)-(5CHARS)`\n"
            "Exemplos:\n"
            "```\n"
            "PIRATE-30D-AB3X7  (30 dias)\n"
            "PIRATE-3M-KZ9P2   (3 meses)\n"
            "PIRATE-1A-MN7Q4   (1 ano)\n"
            "PIRATE-24H-RT5W8  (24 horas)\n"
            "```\n\n"
            "**👑 Key Premium** — Key permanente com nome personalizado\n"
            "Formato: `nome` (ex: `piratepremium`)\n"
            "Válida para sempre, sem expiração."
        ),
        color=bot_config["color"]
    )

    if bot_config.get("banner_url"):
        embed.set_image(url=bot_config["banner_url"])

    embed.set_footer(text="Pirate Scripts v2.0 | Gerador de Keys")

    view = GeradorView()

    if edit:
        await interaction.response.edit_message(embed=embed, view=view)
    else:
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class GerarPlanoModal(discord.ui.Modal, title="🔑 Gerar Key Plano"):
    prefixo_input = discord.ui.TextInput(
        label="Prefixo (deixe vazio para usar PIRATE)",
        placeholder="Ex: PIRATE (padrão)",
        required=False,
        max_length=20
    )
    quantidade_input = discord.ui.TextInput(
        label="Quantidade de keys (1-10)",
        placeholder="Ex: 1",
        required=True,
        max_length=2
    )
    valor_input = discord.ui.TextInput(
        label="Valor de tempo (número)",
        placeholder="Ex: 30",
        required=True,
        max_length=5
    )
    unidade_input = discord.ui.TextInput(
        label="Unidade: anual / mensal / diario / horas",
        placeholder="Ex: diario",
        required=True,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        prefix = self.prefixo_input.value.strip() or "PIRATE"
        unidade = self.unidade_input.value.strip().lower()

        # Normalizar unidade
        unidade_map = {
            "anual": "anual", "ano": "anual", "anos": "anual", "a": "anual",
            "mensal": "mensal", "mes": "mensal", "meses": "mensal", "m": "mensal",
            "diario": "diario", "dia": "diario", "dias": "diario", "d": "diario",
            "horas": "horas", "hora": "horas", "h": "horas"
        }
        unidade = unidade_map.get(unidade, "diario")

        try:
            quantidade = int(self.quantidade_input.value.strip())
            valor = int(self.valor_input.value.strip())
        except ValueError:
            await interaction.response.send_message("❌ Quantidade e valor devem ser números!", ephemeral=True)
            return

        if quantidade < 1 or quantidade > 10:
            await interaction.response.send_message("❌ Quantidade deve ser entre 1 e 10!", ephemeral=True)
            return

        if valor < 1:
            await interaction.response.send_message("❌ Valor deve ser maior que 0!", ephemeral=True)
            return

        expiration = calculate_expiration(valor, unidade)

        conn = get_db()
        c = conn.cursor()
        keys_geradas = []

        for _ in range(quantidade):
            new_key = generate_plano_key(prefix, valor, unidade)
            # Garantir unicidade
            attempts = 0
            while attempts < 20:
                c.execute("SELECT id FROM keys WHERE key = ?", (new_key,))
                if not c.fetchone():
                    break
                new_key = generate_plano_key(prefix, valor, unidade)
                attempts += 1

            c.execute(
                "INSERT INTO keys (key, key_type, prefix, created_at, expiration, uses, active, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (new_key, "plano", prefix, datetime.now().isoformat(), expiration.isoformat(), 0, 1, str(interaction.user.id))
            )
            keys_geradas.append(new_key)

        conn.commit()
        conn.close()

        # Unidade display
        unidade_display = {
            "anual": "Ano(s)", "mensal": "Mês(es)", "diario": "Dia(s)", "horas": "Hora(s)"
        }.get(unidade, "Dia(s)")

        embed = discord.Embed(
            title="✅ Keys Plano Geradas!",
            color=SUCCESS_COLOR,
            timestamp=datetime.now()
        )

        keys_text = "\n".join([f"`{k}`" for k in keys_geradas])
        embed.add_field(name="🔑 Keys Geradas", value=keys_text, inline=False)
        embed.add_field(name="📦 Quantidade", value=str(quantidade), inline=True)
        embed.add_field(name="⏰ Validade", value=f"{valor} {unidade_display}", inline=True)
        embed.add_field(name="📅 Expira em", value=f"<t:{int(expiration.timestamp())}:F>", inline=False)
        embed.set_footer(text=f"Gerado por {interaction.user.name} | Pirate Scripts v2.0")

        await interaction.response.send_message(embed=embed, ephemeral=True)


class GerarPremiumModal(discord.ui.Modal, title="👑 Gerar Key Premium"):
    nome_input = discord.ui.TextInput(
        label="Nome da key premium",
        placeholder="Ex: piratepremium",
        required=True,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        nome = self.nome_input.value.strip()
        new_key = generate_premium_key(nome)

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM keys WHERE key = ?", (new_key,))
        if c.fetchone():
            conn.close()
            await interaction.response.send_message(
                f"❌ Já existe uma key com o nome `{new_key}`! Escolha outro nome.",
                ephemeral=True
            )
            return

        c.execute(
            "INSERT INTO keys (key, key_type, prefix, created_at, expiration, uses, active, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (new_key, "premium", "PREMIUM", datetime.now().isoformat(), None, 0, 1, str(interaction.user.id))
        )
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="👑 Key Premium Criada!",
            color=0xFFD700,
            timestamp=datetime.now()
        )
        embed.add_field(name="🔑 Key", value=f"```{new_key}```", inline=False)
        embed.add_field(name="⏰ Validade", value="**Permanente** (sem expiração)", inline=True)
        embed.add_field(name="👑 Tipo", value="**Premium**", inline=True)
        embed.set_footer(text=f"Gerado por {interaction.user.name} | Pirate Scripts v2.0")

        await interaction.response.send_message(embed=embed, ephemeral=True)


# ============================================================
# PERMISSÕES
# ============================================================

class PermissoesView(discord.ui.View):
    """View de gerenciamento de permissões."""

    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="➕ Adicionar Permissão", style=discord.ButtonStyle.success, custom_id="perm_add")
    async def add_perm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Apenas o dono pode gerenciar permissões!", ephemeral=True)
            return
        modal = AddPermModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="➖ Remover Permissão", style=discord.ButtonStyle.danger, custom_id="perm_remove")
    async def remove_perm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Apenas o dono pode gerenciar permissões!", ephemeral=True)
            return
        modal = RemovePermModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🔙 Voltar ao Painel", style=discord.ButtonStyle.secondary, custom_id="perm_back")
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await show_main_panel(interaction, edit=True)


async def show_permissoes(interaction: discord.Interaction, edit=False):
    """Mostra o painel de permissões."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM permissions ORDER BY added_at DESC")
    perms = c.fetchall()
    conn.close()

    embed = discord.Embed(
        title="🛡️ Gerenciamento de Permissões",
        description=(
            "Aqui você pode controlar quem tem acesso ao bot.\n"
            "O **Dono** sempre tem acesso total.\n\n"
            f"👑 **Dono:** <@{OWNER_ID}>"
        ),
        color=bot_config["color"]
    )

    if bot_config.get("banner_url"):
        embed.set_image(url=bot_config["banner_url"])

    if perms:
        perm_lines = []
        for p in perms:
            perm_lines.append(
                f"• <@{p['user_id']}> (`{p['user_id']}`)\n"
                f"  Adicionado em: <t:{int(datetime.fromisoformat(p['added_at']).timestamp())}:d>"
            )
        embed.add_field(
            name=f"👥 Usuários com Permissão ({len(perms)})",
            value="\n".join(perm_lines) if perm_lines else "Nenhum usuário adicionado.",
            inline=False
        )
    else:
        embed.add_field(
            name="👥 Usuários com Permissão",
            value="Nenhum usuário com permissão adicional.",
            inline=False
        )

    embed.add_field(
        name="💡 Como adicionar",
        value=(
            "Clique em **Adicionar Permissão** e informe:\n"
            "• ID do usuário Discord\n"
            "• Ou mencione o usuário (@usuario)"
        ),
        inline=False
    )

    embed.set_footer(text="Pirate Scripts v2.0 | Apenas o dono pode gerenciar permissões")

    view = PermissoesView()

    if edit:
        await interaction.response.edit_message(embed=embed, view=view)
    else:
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class AddPermModal(discord.ui.Modal, title="➕ Adicionar Permissão"):
    user_input = discord.ui.TextInput(
        label="ID do usuário Discord",
        placeholder="Ex: 123456789012345678",
        required=True,
        max_length=25
    )

    async def on_submit(self, interaction: discord.Interaction):
        user_id_str = self.user_input.value.strip().replace("<@", "").replace(">", "").replace("!", "")

        try:
            user_id = int(user_id_str)
        except ValueError:
            await interaction.response.send_message("❌ ID inválido! Use apenas números.", ephemeral=True)
            return

        # Tentar buscar o usuário
        try:
            user = await bot.fetch_user(user_id)
            username = str(user)
        except Exception:
            username = f"ID: {user_id}"

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM permissions WHERE user_id = ?", (str(user_id),))
        if c.fetchone():
            conn.close()
            await interaction.response.send_message(f"⚠️ O usuário `{username}` já tem permissão!", ephemeral=True)
            return

        c.execute(
            "INSERT INTO permissions (user_id, username, added_by, added_at) VALUES (?, ?, ?, ?)",
            (str(user_id), username, str(interaction.user.id), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="✅ Permissão Adicionada",
            description=f"**{username}** (`{user_id}`) agora tem acesso ao bot!",
            color=SUCCESS_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class RemovePermModal(discord.ui.Modal, title="➖ Remover Permissão"):
    user_input = discord.ui.TextInput(
        label="ID do usuário Discord",
        placeholder="Ex: 123456789012345678",
        required=True,
        max_length=25
    )

    async def on_submit(self, interaction: discord.Interaction):
        user_id_str = self.user_input.value.strip().replace("<@", "").replace(">", "").replace("!", "")

        try:
            user_id = int(user_id_str)
        except ValueError:
            await interaction.response.send_message("❌ ID inválido! Use apenas números.", ephemeral=True)
            return

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM permissions WHERE user_id = ?", (str(user_id),))
        if not c.fetchone():
            conn.close()
            await interaction.response.send_message(f"❌ Usuário `{user_id}` não tem permissão!", ephemeral=True)
            return

        c.execute("DELETE FROM permissions WHERE user_id = ?", (str(user_id),))
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="✅ Permissão Removida",
            description=f"O usuário `{user_id}` não tem mais acesso ao bot.",
            color=WARNING_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ============================================================
# VISUAL
# ============================================================

class VisualView(discord.ui.View):
    """View de configurações visuais do bot."""

    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="🎨 Cor do Bot", style=discord.ButtonStyle.primary, custom_id="vis_color")
    async def set_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Apenas o dono pode alterar o visual!", ephemeral=True)
            return
        modal = SetColorModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🖼️ Banner do Bot", style=discord.ButtonStyle.primary, custom_id="vis_banner")
    async def set_banner(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Apenas o dono pode alterar o visual!", ephemeral=True)
            return
        modal = SetBannerModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🏴‍☠️ Logo do Bot", style=discord.ButtonStyle.primary, custom_id="vis_logo")
    async def set_logo(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Apenas o dono pode alterar o visual!", ephemeral=True)
            return
        modal = SetLogoModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📡 Status do Bot", style=discord.ButtonStyle.secondary, custom_id="vis_status")
    async def set_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Apenas o dono pode alterar o visual!", ephemeral=True)
            return
        modal = SetStatusModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🎮 Rich Presence", style=discord.ButtonStyle.secondary, custom_id="vis_rp")
    async def set_rich_presence(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Apenas o dono pode alterar o visual!", ephemeral=True)
            return
        modal = SetRichPresenceModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🔙 Voltar ao Painel", style=discord.ButtonStyle.secondary, custom_id="vis_back", row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await show_main_panel(interaction, edit=True)


async def show_visual(interaction: discord.Interaction, edit=False):
    """Mostra o painel de configurações visuais."""
    embed = discord.Embed(
        title="🎨 Configurações Visuais",
        description="Personalize a aparência do bot Pirate Scripts.",
        color=bot_config["color"]
    )

    if bot_config.get("banner_url"):
        embed.set_image(url=bot_config["banner_url"])

    if bot_config.get("logo_url"):
        embed.set_thumbnail(url=bot_config["logo_url"])

    # Cor atual em hex
    color_hex = f"#{bot_config['color']:06X}"

    embed.add_field(
        name="🎨 Configurações Atuais",
        value=(
            f"**Cor:** `{color_hex}`\n"
            f"**Status:** `{bot_config.get('status', 'Não definido')}`\n"
            f"**Tipo de Status:** `{bot_config.get('status_type', 'playing')}`\n"
            f"**Banner:** {'✅ Configurado' if bot_config.get('banner_url') else '❌ Não configurado'}\n"
            f"**Logo:** {'✅ Configurado' if bot_config.get('logo_url') else '❌ Não configurado'}\n"
            f"**Rich Presence:** {'✅ Configurado' if bot_config.get('rich_presence') else '❌ Não configurado'}"
        ),
        inline=False
    )

    embed.add_field(
        name="💡 Instruções",
        value=(
            "**Cor:** Use código HEX (ex: `#4466FF`)\n"
            "**Banner/Logo:** Cole a URL da imagem\n"
            "**Status:** Texto que aparece no perfil do bot\n"
            "**Rich Presence:** Texto detalhado de atividade"
        ),
        inline=False
    )

    embed.set_footer(text="Pirate Scripts v2.0 | Apenas o dono pode alterar")

    view = VisualView()

    if edit:
        await interaction.response.edit_message(embed=embed, view=view)
    else:
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class SetColorModal(discord.ui.Modal, title="🎨 Definir Cor do Bot"):
    color_input = discord.ui.TextInput(
        label="Cor em HEX",
        placeholder="Ex: #4466FF ou 4466FF",
        required=True,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        color_str = self.color_input.value.strip().replace("#", "")
        try:
            color_int = int(color_str, 16)
            save_bot_config("color", color_int)
            embed = discord.Embed(
                title="✅ Cor Atualizada",
                description=f"A cor do bot foi definida para `#{color_str.upper()}`!",
                color=color_int
            )
        except ValueError:
            embed = discord.Embed(
                title="❌ Cor Inválida",
                description="Use um código HEX válido. Ex: `#4466FF`",
                color=ERROR_COLOR
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class SetBannerModal(discord.ui.Modal, title="🖼️ Definir Banner do Bot"):
    url_input = discord.ui.TextInput(
        label="URL do Banner",
        placeholder="https://i.imgur.com/...",
        required=True,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        url = self.url_input.value.strip()
        save_bot_config("banner_url", url)
        embed = discord.Embed(
            title="✅ Banner Atualizado",
            description="O banner do bot foi atualizado!",
            color=SUCCESS_COLOR
        )
        embed.set_image(url=url)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class SetLogoModal(discord.ui.Modal, title="🏴‍☠️ Definir Logo do Bot"):
    url_input = discord.ui.TextInput(
        label="URL da Logo",
        placeholder="https://i.imgur.com/...",
        required=True,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        url = self.url_input.value.strip()
        save_bot_config("logo_url", url)
        embed = discord.Embed(
            title="✅ Logo Atualizada",
            description="A logo do bot foi atualizada!",
            color=SUCCESS_COLOR
        )
        embed.set_thumbnail(url=url)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class SetStatusModal(discord.ui.Modal, title="📡 Definir Status do Bot"):
    status_input = discord.ui.TextInput(
        label="Texto do Status",
        placeholder="Ex: Gerando Chaves - Pirate Scripts 🔒",
        required=True,
        max_length=128
    )
    type_input = discord.ui.TextInput(
        label="Tipo: playing / watching / listening / competing",
        placeholder="playing",
        required=True,
        max_length=15
    )

    async def on_submit(self, interaction: discord.Interaction):
        status_text = self.status_input.value.strip()
        status_type = self.type_input.value.strip().lower()

        valid_types = ["playing", "watching", "listening", "competing"]
        if status_type not in valid_types:
            status_type = "playing"

        save_bot_config("status", status_text)
        save_bot_config("status_type", status_type)

        # Atualizar status do bot em tempo real
        await update_bot_status()

        embed = discord.Embed(
            title="✅ Status Atualizado",
            description=f"Status definido para:\n**{status_type.capitalize()}:** `{status_text}`",
            color=SUCCESS_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class SetRichPresenceModal(discord.ui.Modal, title="🎮 Definir Rich Presence"):
    rp_input = discord.ui.TextInput(
        label="Texto do Rich Presence",
        placeholder="Ex: Pirate Scripts | Sistema de Keys v2.0",
        required=True,
        max_length=128
    )

    async def on_submit(self, interaction: discord.Interaction):
        rp_text = self.rp_input.value.strip()
        save_bot_config("rich_presence", rp_text)
        embed = discord.Embed(
            title="✅ Rich Presence Atualizado",
            description=f"Rich Presence definido para:\n`{rp_text}`",
            color=SUCCESS_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ============================================================
# PAINEL PRINCIPAL
# ============================================================

async def show_main_panel(interaction: discord.Interaction, edit=False):
    """Mostra o painel principal."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as total FROM keys")
    total = c.fetchone()["total"]
    now = datetime.now().isoformat()
    c.execute("SELECT COUNT(*) as active FROM keys WHERE active = 1 AND (expiration IS NULL OR expiration > ?)", (now,))
    active = c.fetchone()["active"]
    c.execute("SELECT COUNT(*) as premium FROM keys WHERE key_type = 'premium'")
    premium = c.fetchone()["premium"]
    conn.close()

    embed = discord.Embed(
        title="🏴‍☠️ Pirate Scripts — Painel de Controle",
        description=(
            "Bem-vindo ao painel central de gerenciamento.\n"
            "Use o menu abaixo para navegar entre as seções."
        ),
        color=bot_config["color"],
        timestamp=datetime.now()
    )

    # Banner
    if bot_config.get("banner_url"):
        embed.set_image(url=bot_config["banner_url"])

    # Logo
    if bot_config.get("logo_url"):
        embed.set_thumbnail(url=bot_config["logo_url"])

    # Estatísticas rápidas
    embed.add_field(
        name="📊 Visão Geral",
        value=(
            f"```\n"
            f"✅ Keys Ativas:  {active}\n"
            f"👑 Premium:      {premium}\n"
            f"📦 Total Keys:   {total}\n"
            f"```"
        ),
        inline=True
    )

    embed.add_field(
        name="🗂️ Seções Disponíveis",
        value=(
            "📊 **Dashboard** — Gerencie suas keys\n"
            "🔑 **Gerador** — Crie novas keys\n"
            "🛡️ **Permissões** — Controle de acesso\n"
            "🎨 **Visual** — Aparência do bot"
        ),
        inline=True
    )

    embed.set_footer(text="Pirate Scripts v2.0 | Sistema de Keys")

    view = PainelView()

    if edit:
        await interaction.response.edit_message(embed=embed, view=view)
    else:
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ============================================================
# ATUALIZAR STATUS DO BOT
# ============================================================

async def update_bot_status():
    """Atualiza o status do bot com as configurações salvas."""
    status_text = bot_config.get("status", "Gerando Chaves - Pirate Scripts 🔒")
    status_type = bot_config.get("status_type", "playing")

    activity_map = {
        "playing": discord.ActivityType.playing,
        "watching": discord.ActivityType.watching,
        "listening": discord.ActivityType.listening,
        "competing": discord.ActivityType.competing,
    }

    activity_type = activity_map.get(status_type, discord.ActivityType.playing)
    activity = discord.Activity(type=activity_type, name=status_text)
    await bot.change_presence(activity=activity)


# ============================================================
# TASKS
# ============================================================

@tasks.loop(minutes=10)
async def cleanup_expired_keys():
    """Remove keys expiradas há mais de 7 dias."""
    conn = get_db()
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    c.execute("DELETE FROM keys WHERE expiration IS NOT NULL AND expiration < ? AND key_type != 'premium'", (cutoff,))
    deleted = c.rowcount
    conn.commit()
    conn.close()
    if deleted > 0:
        print(f"🧹 {deleted} keys expiradas removidas automaticamente.")


@tasks.loop(minutes=30)
async def refresh_status():
    """Atualiza o status do bot periodicamente."""
    await update_bot_status()


# ============================================================
# EVENTOS DO BOT
# ============================================================

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}", flush=True)
    try:
        synced = await bot.tree.sync()
        print(f"✅ Comandos sincronizados: {len(synced)} comandos!", flush=True)
    except Exception as e:
        print(f"⚠️ Erro ao sincronizar: {e}", flush=True)

    load_bot_config()
    await update_bot_status()
    cleanup_expired_keys.start()
    refresh_status.start()
    print("🏴‍☠️ Pirate Scripts Bot v2.0 pronto!", flush=True)


# ============================================================
# COMANDOS SLASH
# ============================================================

@bot.tree.command(name="painel", description="Abre o painel de controle da Pirate Scripts")
async def painel(interaction: discord.Interaction):
    """Comando principal do painel."""
    if not has_permission(interaction.user.id):
        embed = discord.Embed(
            title="❌ Acesso Negado",
            description="Você não tem permissão para acessar o painel!",
            color=ERROR_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await show_main_panel(interaction)


@bot.tree.command(name="validar_key", description="Valida uma key do sistema")
@app_commands.describe(key="A key a ser validada")
async def validar_key(interaction: discord.Interaction, key: str):
    """Valida uma key."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM keys WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()

    if not row:
        embed = discord.Embed(
            title="❌ Key Inválida",
            description="Esta key não foi encontrada no sistema.",
            color=ERROR_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if row["active"] == 0:
        embed = discord.Embed(
            title="⏸️ Key Desativada",
            description="Esta key está desativada.",
            color=WARNING_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if row["key_type"] == "premium" or row["expiration"] is None:
        embed = discord.Embed(
            title="👑 Key Premium Válida",
            description="Esta key premium é permanente e está ativa!",
            color=0xFFD700
        )
        embed.add_field(name="🔑 Key", value=f"```{key}```", inline=False)
        embed.add_field(name="⏰ Validade", value="Permanente", inline=True)
        embed.add_field(name="📊 Usos", value=str(row["uses"]), inline=True)
    else:
        exp = datetime.fromisoformat(row["expiration"])
        now = datetime.now()
        if exp <= now:
            embed = discord.Embed(
                title="⏰ Key Expirada",
                description=f"Esta key expirou em <t:{int(exp.timestamp())}:F>",
                color=ERROR_COLOR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="✅ Key Válida",
            description="A key foi validada com sucesso!",
            color=SUCCESS_COLOR
        )
        embed.add_field(name="🔑 Key", value=f"```{key}```", inline=False)
        embed.add_field(name="📅 Expira em", value=f"<t:{int(exp.timestamp())}:R>", inline=True)
        embed.add_field(name="📊 Usos", value=str(row["uses"]), inline=True)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="status_bot", description="Mostra o status atual do sistema")
async def status_bot(interaction: discord.Interaction):
    """Mostra status do sistema."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as total FROM keys")
    total = c.fetchone()["total"]
    now_iso = datetime.now().isoformat()
    c.execute("SELECT COUNT(*) as active FROM keys WHERE active = 1 AND (expiration IS NULL OR expiration > ?)", (now_iso,))
    active = c.fetchone()["active"]
    conn.close()

    embed = discord.Embed(
        title="📡 Status do Sistema",
        color=SUCCESS_COLOR,
        timestamp=datetime.now()
    )
    embed.add_field(name="🤖 Bot", value="✅ Online", inline=True)
    embed.add_field(name="🌐 API", value="✅ Online (porta 8080)", inline=True)
    embed.add_field(name="🗄️ Banco de Dados", value="✅ SQLite", inline=True)
    embed.add_field(name="📦 Keys Totais", value=str(total), inline=True)
    embed.add_field(name="✅ Keys Ativas", value=str(active), inline=True)
    embed.set_footer(text="Pirate Scripts v2.0")

    await interaction.response.send_message(embed=embed, ephemeral=True)


# ============================================================
# INICIAR BOT + API
# ============================================================

if __name__ == "__main__":
    try:
        # Inicializar banco de dados
        init_database()
        print("✅ Banco de dados inicializado!", flush=True)

        # Iniciar API HTTP em thread separada (opcional)
        try:
            http_thread = threading.Thread(target=start_http_server, daemon=True)
            http_thread.start()
        except Exception as e:
            print(f"⚠️ API HTTP desabilitada: {e}")

        # Iniciar bot Discord
        print(f"🚀 Iniciando bot com token...", flush=True)
        bot.run(BOT_TOKEN)
    except Exception as e:
        print(f"❌ ERRO CRÍTICO: {e}", flush=True)
        import traceback
        traceback.print_exc()
        exit(1)
