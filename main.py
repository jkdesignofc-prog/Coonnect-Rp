import os
import datetime
import asyncio
import discord
from discord import app_commands
from dotenv import load_dotenv

# ===============================
# ENV
# ===============================
load_dotenv()
TOKEN = os.getenv("TOKEN")

# ===============================
# CONFIG
# ===============================
GUILD_ID = 889608517802156074

CONNECT_BANNER_URL = "https://cdn.discordapp.com/attachments/1471669099305111681/1475887473828560996/Arma.png"
CONNECT_LOGO_URL = "https://cdn.discordapp.com/attachments/1471669099305111681/1475890195101651044/b33c058f841b4b283651526d031077b1-Photoroom.png"
CONNECT_NAME = "Connect RP Atendimento"

# ✅ EMOJI ANIMADO CERTO (troque o ID)
FINALIZAR_EMOJI = discord.PartialEmoji(name="a1", id=1475892543605706959, animated=True)

# Cargo staff
STAFF_ROLE_ID = 1475601034851258431

# Categorias
CATEGORY_DOACOES = 1475600622249181315
CATEGORY_SUPORTE = 1475600769872040066
CATEGORY_DENUNCIAS = 1475600892559364310
CATEGORY_LIDERANCA = 1475601396702117918
CATEGORY_CONTEUDO = 1413644531919884369

# Canais
LOG_CHANNEL_ID = 1475601613489049684
AVALIACAO_CHANNEL_ID = 889608520687833115
PUNICAO_CHANNEL_ID = 889608519731519525

# Canal do painel / canal dos comandos
CANAL_PAINEL_ID = 1021911632496050339
CANAL_COMANDOS_ID = 889608518380953646

# Guarda horário de abertura do ticket
ticket_abertura: dict[int, datetime.datetime] = {}

# Guarda staff do ticket
ticket_staff: dict[int, dict[str, int | None]] = {}   # {canal_id: {"resp": id, "aux": id}}
ticket_msg_id: dict[int, int] = {}                    # {canal_id: message_id do embed principal}


# ===============================
# CHECKS / HELPERS
# ===============================
def is_canal_painel():
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.channel_id == CANAL_PAINEL_ID
    return app_commands.check(predicate)

def is_canal_comandos():
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.channel_id == CANAL_COMANDOS_ID
    return app_commands.check(predicate)

def has_staff_role():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        return any(role.id == STAFF_ROLE_ID for role in interaction.user.roles)
    return app_commands.check(predicate)

def is_staff(member: discord.Member) -> bool:
    return any(r.id == STAFF_ROLE_ID for r in member.roles)

def get_ticket_resp_aux(channel_id: int):
    data = ticket_staff.get(channel_id, {"resp": None, "aux": None})
    return data.get("resp"), data.get("aux")


# ===============================
# BOT
# ===============================
class VersaillesRoleplay(discord.Client):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

        # Views persistentes
        self.add_view(TicketView())
        self.add_view(TicketControlView())  # ✅ view com botões assum/aux/add/rem/finalizar/sair

    async def on_ready(self):
        print(f"✅ O bot {self.user} foi ligado com sucesso.")

bot = VersaillesRoleplay()


# ===============================
# COMANDO /avaliar-staff
# ===============================
@bot.tree.command(name="avaliar-staff", description="Avalie um membro da equipe")
@app_commands.describe(staff="Mencione o staff", nota="Nota 1 a 10", avaliacao="Sua avaliação")
async def avaliar_staff(interaction: discord.Interaction, staff: discord.Member, nota: int, avaliacao: str):
    if nota < 1 or nota > 10:
        await interaction.response.send_message("⚠️ A nota deve ser entre 1 e 10.", ephemeral=True)
        return

    embed = discord.Embed(
        title="⭐ AVALIAÇÃO DE STAFF",
        color=discord.Color.gold(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.add_field(name="👤 Jogador", value=interaction.user.mention, inline=False)
    embed.add_field(name="🛠️ Staff Avaliado", value=staff.mention, inline=False)
    embed.add_field(name="📊 Nota", value=str(nota), inline=True)
    embed.add_field(name="📝 Avaliação", value=avaliacao, inline=False)

    channel = interaction.guild.get_channel(AVALIACAO_CHANNEL_ID) if interaction.guild else None
    if channel:
        await channel.send(embed=embed)

    await interaction.response.send_message("✅ Avaliação registrada com sucesso!", ephemeral=True)


# ===============================
# COMANDO /aplicar-punicao
# ===============================
@bot.tree.command(name="aplicar-punicao", description="Aplicar uma punição a um jogador")
@has_staff_role()
@is_canal_comandos()
@app_commands.describe(jogador="Jogador", id_fivem="ID do FiveM", punicao="Tipo", motivo="Motivo")
async def aplicar_punicao(interaction: discord.Interaction, jogador: discord.Member, id_fivem: str, punicao: str, motivo: str):
    embed = discord.Embed(
        title="🚨 NOVA PUNIÇÃO",
        color=discord.Color.red(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.add_field(name="👤 Jogador Punido", value=f"{jogador.mention} (`{jogador.id}`)", inline=False)
    embed.add_field(name="🆔 ID FiveM", value=id_fivem, inline=True)
    embed.add_field(name="⚖️ Tipo de Punição", value=punicao, inline=True)
    embed.add_field(name="📝 Motivo", value=motivo, inline=False)
    embed.set_footer(text=f"Punição aplicada por {interaction.user}")

    channel = interaction.guild.get_channel(PUNICAO_CHANNEL_ID) if interaction.guild else None
    if channel:
        await channel.send(embed=embed)

    await interaction.response.send_message("✅ Punição registrada com sucesso!", ephemeral=True)


# ===============================
# MODAIS
# ===============================
class RenameModal(discord.ui.Modal, title="Renomear Ticket"):
    novo_nome = discord.ui.TextInput(label="Novo nome", placeholder="Digite o novo nome...")

    async def on_submit(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
            return await interaction.response.send_message("⚠️ Apenas staff pode renomear.", ephemeral=True)
        await interaction.channel.edit(name=self.novo_nome.value)
        await interaction.response.send_message(f"✏️ Ticket renomeado para **{self.novo_nome.value}**", ephemeral=True)


class AddMemberModal(discord.ui.Modal, title="Adicionar Membro"):
    membro = discord.ui.TextInput(label="ID ou @", placeholder="@usuario ou ID")

    async def on_submit(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
            return await interaction.response.send_message("⚠️ Apenas staff pode adicionar membro.", ephemeral=True)

        try:
            user_id = int(self.membro.value.replace("<@", "").replace(">", "").replace("!", "").strip())
            member = interaction.guild.get_member(user_id)
            if not member:
                return await interaction.response.send_message("⚠️ Usuário não encontrado!", ephemeral=True)

            await interaction.channel.set_permissions(member, view_channel=True, send_messages=True, attach_files=True)
            await interaction.response.send_message(f"➕ {member.mention} foi adicionado ao ticket!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao adicionar membro: {e}", ephemeral=True)


class RemoveMemberModal(discord.ui.Modal, title="Remover Membro"):
    membro = discord.ui.TextInput(label="ID ou @", placeholder="@usuario ou ID")

    async def on_submit(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
            return await interaction.response.send_message("⚠️ Apenas staff pode remover membro.", ephemeral=True)

        try:
            user_id = int(self.membro.value.replace("<@", "").replace(">", "").replace("!", "").strip())
            member = interaction.guild.get_member(user_id)
            if not member:
                return await interaction.response.send_message("⚠️ Usuário não encontrado!", ephemeral=True)

            await interaction.channel.set_permissions(member, overwrite=None)
            await interaction.response.send_message(f"➖ {member.mention} foi removido do ticket!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao remover membro: {e}", ephemeral=True)


class AvaliarAtendimentoModal(discord.ui.Modal, title="Avaliar Atendimento"):
    staff_id = discord.ui.TextInput(label="ID do Staff (ou @)", placeholder="Cole o ID ou mencione o staff")
    nota = discord.ui.TextInput(label="Nota (1 a 10)", placeholder="Ex: 10", max_length=2)
    avaliacao = discord.ui.TextInput(label="Sua avaliação", style=discord.TextStyle.paragraph, max_length=1000)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        channel = guild.get_channel(AVALIACAO_CHANNEL_ID) if guild else None

        try:
            sid = int(self.staff_id.value.replace("<@", "").replace(">", "").replace("!", "").strip())
        except:
            return await interaction.response.send_message("⚠️ ID do staff inválido.", ephemeral=True)

        staff = guild.get_member(sid) if guild else None

        try:
            n = int(self.nota.value.strip())
        except:
            return await interaction.response.send_message("⚠️ A nota precisa ser número (1 a 10).", ephemeral=True)

        if n < 1 or n > 10:
            return await interaction.response.send_message("⚠️ A nota deve ser entre 1 e 10.", ephemeral=True)

        embed = discord.Embed(
            title="⭐ AVALIAÇÃO DE ATENDIMENTO",
            color=discord.Color.gold(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="👤 Jogador", value=interaction.user.mention, inline=False)
        embed.add_field(name="🛠️ Staff Avaliado", value=staff.mention if staff else f"`{sid}`", inline=False)
        embed.add_field(name="📊 Nota", value=str(n), inline=True)
        embed.add_field(name="📝 Avaliação", value=self.avaliacao.value, inline=False)

        if channel:
            await channel.send(embed=embed)

        await interaction.response.send_message("✅ Avaliação enviada! Obrigado 😊", ephemeral=True)


# ===============================
# CONFIRMAR SAÍDA
# ===============================
class ConfirmLeaveView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="Sim, Sair do Ticket", style=discord.ButtonStyle.success, emoji="✅")
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.set_permissions(interaction.user, overwrite=None)
        await interaction.response.edit_message(content="✅ Você saiu do ticket.", embed=None, view=None)

    @discord.ui.button(label="Não, Continuar no Ticket", style=discord.ButtonStyle.danger, emoji="❌")
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="✅ Ok, você continua no ticket.", embed=None, view=None)


# ===============================
# VIEW PRINCIPAL DO TICKET (BOTÕES NO EMBED DO TICKET)
# ===============================
class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _deny_staff(self, interaction: discord.Interaction):
        await interaction.response.send_message("⚠️ Apenas a **staff** pode usar este botão.", ephemeral=True)

    async def _edit_main_embed(self, channel: discord.TextChannel):
        mid = ticket_msg_id.get(channel.id)
        if not mid:
            return
        try:
            msg = await channel.fetch_message(mid)
        except:
            return

        resp_id, aux_id = get_ticket_resp_aux(channel.id)
        resp = channel.guild.get_member(resp_id) if resp_id else None
        aux = channel.guild.get_member(aux_id) if aux_id else None

        emb = msg.embeds[0] if msg.embeds else None
        if not emb:
            return

        # remove campos antigos de resp/aux se existirem
        new_fields = []
        for f in emb.fields:
            if f.name.lower().startswith("👮 responsável") or f.name.lower().startswith("🆘 auxiliar"):
                continue
            new_fields.append(f)

        emb.clear_fields()
        for f in new_fields:
            emb.add_field(name=f.name, value=f.value, inline=f.inline)

        emb.add_field(name="👮 Responsável", value=(resp.mention if resp else "`—`"), inline=True)
        emb.add_field(name="🆘 Auxiliar", value=(aux.mention if aux else "`—`"), inline=True)

        await msg.edit(embed=emb, view=self)

    # ============================
    # USER
    # ============================
    @discord.ui.button(
        label="Desejo sair ou cancelar esse ticket",
        style=discord.ButtonStyle.danger,
        emoji="🚪",
        custom_id="ticket:user_leave"
    )
    async def user_leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⚠️ Sair do Ticket",
            description=(
                "**Tem certeza que deseja sair deste ticket?**\n\n"
                "🚨 **Atenção:**\n"
                "• Você perderá acesso ao canal\n"
                "• O ticket continua até um staff finalizar\n\n"
                "📝 Isso é para evitar spam de tickets."
            ),
            color=0x8B0000
        )
        await interaction.response.send_message(embed=embed, view=ConfirmLeaveView(), ephemeral=True)

    @discord.ui.button(
        label="Como libero minha DM?",
        style=discord.ButtonStyle.secondary,
        emoji="❓",
        custom_id="ticket:dm_help"
    )
    async def dm_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg = (
            "📩 **Como liberar sua DM:**\n"
            "1) Abra o servidor\n"
            "2) Clique no nome do servidor\n"
            "3) **Configurações de privacidade**\n"
            "4) Ative **Permitir mensagens diretas** ✅"
        )
        await interaction.response.send_message(msg, ephemeral=True)

    # ============================
    # STAFF
    # ============================
    @discord.ui.button(
        label="Assumir Ticket",
        style=discord.ButtonStyle.secondary,
        emoji="✅",
        custom_id="ticket:assumir"
    )
    async def assumir(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
            return await self._deny_staff(interaction)

        ticket_staff.setdefault(interaction.channel_id, {"resp": None, "aux": None})
        ticket_staff[interaction.channel_id]["resp"] = interaction.user.id

        await interaction.response.send_message(f"✅ {interaction.user.mention} assumiu como **Responsável**.", ephemeral=True)
        await self._edit_main_embed(interaction.channel)

    @discord.ui.button(
        label="Auxiliar Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🆘",
        custom_id="ticket:auxiliar"
    )
    async def auxiliar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
            return await self._deny_staff(interaction)

        ticket_staff.setdefault(interaction.channel_id, {"resp": None, "aux": None})
        ticket_staff[interaction.channel_id]["aux"] = interaction.user.id

        await interaction.response.send_message(f"🆘 {interaction.user.mention} entrou como **Auxiliar**.", ephemeral=True)
        await self._edit_main_embed(interaction.channel)

    @discord.ui.button(
        label="Adicionar Membro",
        style=discord.ButtonStyle.success,
        emoji="➕",
        custom_id="ticket:add_member"
    )
    async def add_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
            return await self._deny_staff(interaction)
        await interaction.response.send_modal(AddMemberModal())

    @discord.ui.button(
        label="Remover Membro",
        style=discord.ButtonStyle.secondary,
        emoji="➖",
        custom_id="ticket:remove_member"
    )
    async def remove_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
            return await self._deny_staff(interaction)
        await interaction.response.send_modal(RemoveMemberModal())

    @discord.ui.button(
        label="Finalizar Ticket",
        style=discord.ButtonStyle.success,
        emoji=FINALIZAR_EMOJI,
        custom_id="ticket:finalizar"
    )
    async def finalizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
            return await self._deny_staff(interaction)
        await interaction.response.send_modal(CloseTicketModal())


# ===============================
# FINALIZAÇÃO + TRANSCRIPT
# ===============================
import asyncio
import zipfile

# ===============================
# FINALIZAÇÃO + TRANSCRIPT
# ===============================
import zipfile

class CloseTicketModal(discord.ui.Modal, title="Finalizar Ticket"):
    motivo = discord.ui.TextInput(
        label="Considerações finais",
        placeholder="Ex: resolveu / abriu errado / sem resposta...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        canal = interaction.channel
        guild = interaction.guild
        log_channel = guild.get_channel(LOG_CHANNEL_ID) if guild else None

        if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
            await interaction.followup.send("⚠️ Apenas a staff pode finalizar.", ephemeral=True)
            return

        # autor pelo nome do canal
        autor = None
        if guild and "-" in canal.name:
            user_name = canal.name.split("-")[-1]
            autor = discord.utils.find(lambda m: m.name == user_name, guild.members)

        aberto_em = ticket_abertura.get(canal.id, datetime.datetime.utcnow())
        tempo_aberto = datetime.datetime.utcnow() - aberto_em
        tempo_formatado = str(tempo_aberto).split(".")[0]
        senha = hex(canal.id)[-6:]

        # Resp/Aux
        resp_id, aux_id = get_ticket_resp_aux(canal.id)
        resp = guild.get_member(resp_id) if (guild and resp_id) else None
        aux = guild.get_member(aux_id) if (guild and aux_id) else None

        # =========================
        # Transcript HTML
        # =========================
        transcript_html = f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8">
<title>Transcript - {canal.name}</title></head><body>
<h2>Transcript do Ticket: {canal.name}</h2>
<p>Servidor: {guild.name if guild else '—'}</p>
<p>Finalizado por: {interaction.user} em {datetime.datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')}</p>
<p><b>Responsável:</b> {resp if resp else '—'}</p>
<p><b>Auxiliar:</b> {aux if aux else '—'}</p>
<p><b>Considerações finais:</b> {self.motivo.value}</p>
<p><b>Senha:</b> {senha}</p>
<hr>
"""
        async for msg in canal.history(limit=None, oldest_first=True):
            content = (msg.content or "").replace("<", "&lt;").replace(">", "&gt;")
            transcript_html += f"<p><b>{msg.author}</b> [{msg.created_at.strftime('%d/%m/%Y %H:%M:%S')}]:<br>{content}</p>\n"

        transcript_html += f"""
<hr>
<p>⏳ Tempo aberto: {tempo_formatado}</p>
<p>™ {guild.name if guild else 'Servidor'} © All rights reserved</p>
</body></html>
"""

        filename = f"transcript-{canal.id}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(transcript_html)

        # ZIP (pra não aparecer html feio)
        zipname = f"transcript-{canal.id}.zip"
        try:
            with zipfile.ZipFile(zipname, "w", zipfile.ZIP_DEFLATED) as z:
                z.write(filename, arcname=f"transcript-{canal.id}.html")
        except Exception as e:
            print("ERRO ZIP:", repr(e))
            zipname = None

        # =========================
        # LOG (EMBED BONITO + ANEXO + BOTÃO)
        # =========================
        transcript_url: Optional[str] = None
        msg_log: Optional[discord.Message] = None

        if log_channel:
            send_path = None
            if zipname and os.path.exists(zipname):
                send_path = zipname
            else:
                send_path = filename  # fallback

            log_embed = discord.Embed(
                title="📕 TICKET FINALIZADO (LOG)",
                description=(
                    f"👤 **Autor:** {autor.mention if autor else 'Usuário não identificado'}\n"
                    f"👮 **Responsável:** {resp.mention if resp else '`—`'}\n"
                    f"🆘 **Auxiliar:** {aux.mention if aux else '`—`'}\n"
                    f"🛠️ **Finalizado por:** {interaction.user.mention}\n"
                    f"⏳ **Tempo aberto:** {tempo_formatado}\n"
                    f"🔐 **Senha:** `{senha}`\n\n"
                    f"**Considerações finais:**\n```{self.motivo.value}```"
                ),
                color=0x8B0000
            )
            log_embed.set_author(name=CONNECT_NAME, icon_url=CONNECT_LOGO_URL)
            log_embed.set_thumbnail(url=CONNECT_LOGO_URL)
            log_embed.set_image(url=CONNECT_BANNER_URL)
            log_embed.set_footer(text="™ Connect RP © All rights reserved")

            # manda embed + arquivo na mesma mensagem
            try:
                msg_log = await log_channel.send(
                    embed=log_embed,
                    file=discord.File(send_path)
                )
                if msg_log.attachments:
                    transcript_url = msg_log.attachments[0].url

                if transcript_url:
                    await msg_log.edit(view=LogTranscriptView(transcript_url=transcript_url, senha=senha))
            except Exception as e:
                print("ERRO LOG SEND:", repr(e))

        # =========================
        # DM (EMBED CHIQUE + ZIP + BOTÃO)
        # =========================
        categoria_nome = canal.category.name if canal.category else "Sem categoria"
        aberto_str = aberto_em.strftime("%d/%m/%Y às %H:%M:%S")

        dm_embed = discord.Embed(
            title="Ticket Finalizado! 📋",
            description=(
                f"Seu Ticket de ID: `{canal.id}`\n\n"
                f"🏷️ Categoria: **{categoria_nome}**\n"
                f"🕒 Aberto em **{aberto_str}**\n"
                f"⏳ Tempo aberto: **{tempo_formatado}**\n\n"
                f"👮 Responsável: {resp.mention if resp else '`—`'}\n"
                f"🆘 Auxiliar: {aux.mention if aux else '`—`'}\n"
                f"🛠️ Finalizado por: {interaction.user.mention}\n\n"
                f"📝 Considerações:\n```{self.motivo.value}```\n"
                f"🔐 Senha do Transcript: `{senha}`"
            ),
            color=discord.Color.green()
        )
        dm_embed.set_author(name=CONNECT_NAME, icon_url=CONNECT_LOGO_URL)
        dm_embed.set_thumbnail(url=CONNECT_LOGO_URL)
        dm_embed.set_image(url=CONNECT_BANNER_URL)
        dm_embed.set_footer(text="™ Connect RP © All rights reserved")

        dm_ok = False
        if autor:
            try:
                files = []
                if zipname and os.path.exists(zipname):
                    files.append(discord.File(zipname))

                await autor.send(
                    embed=dm_embed,
                    view=FinalTicketView(transcript_url=transcript_url, senha=senha),
                    files=files
                )
                dm_ok = True
            except Exception as e:
                print("ERRO DM:", repr(e))
                dm_ok = False

        if not dm_ok and autor:
            try:
                await canal.send(
                    f"{autor.mention} ⚠️ Não consegui te mandar no privado (DM bloqueada). "
                    f"Ative suas mensagens diretas do servidor para receber o transcript."
                )
            except:
                pass

        await interaction.followup.send("✅ Ticket finalizado com sucesso!", ephemeral=True)

        # limpa arquivos
        try:
            os.remove(filename)
        except:
            pass
        if zipname:
            try:
                os.remove(zipname)
            except:
                pass

        await asyncio.sleep(5)
        await canal.delete()

class LogTranscriptView(discord.ui.View):
    def __init__(self, transcript_url: str, senha: str):
        super().__init__(timeout=None)
        self.senha = senha

        self.add_item(discord.ui.Button(
            label="Acessar Transcript",
            style=discord.ButtonStyle.link,
            url=transcript_url,
            emoji="📎"
        ))

    @discord.ui.button(label="Senha", style=discord.ButtonStyle.secondary, emoji="🔐", custom_id="log:senha")
    async def senha_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"🔐 Senha do transcript: `{self.senha}`", ephemeral=True)


class FinalTicketView(discord.ui.View):
    def __init__(self, transcript_url: Optional[str], senha: str):
        super().__init__(timeout=None)
        self.senha = senha

        if transcript_url:
            self.add_item(discord.ui.Button(
                label="Acessar o Transcript",
                style=discord.ButtonStyle.link,
                url=transcript_url,
                emoji="📎"
            ))

    @discord.ui.button(label="Senha", style=discord.ButtonStyle.secondary, emoji="🔐", custom_id="ticket:mostrar_senha")
    async def mostrar_senha(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"🔐 Senha do transcript: `{self.senha}`", ephemeral=True)

    @discord.ui.button(label="Avaliar Atendimento", style=discord.ButtonStyle.primary, emoji="⭐", custom_id="ticket:avaliar")
    async def avaliar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AvaliarAtendimentoModal())

# ===============================
# SELECT + MODAL MOTIVO
# ===============================
class TicketMotivoModal(discord.ui.Modal, title="Motivo do Ticket"):
    motivo = discord.ui.TextInput(
        label="Qual o motivo do seu ticket?",
        placeholder="Explique com detalhes...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=300
    )

    def __init__(self, escolha: str):
        super().__init__()
        self.escolha = escolha

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        canal = None
        try:
            guild = interaction.guild
            if guild is None:
                return await interaction.followup.send("❌ Erro: guild não encontrada.", ephemeral=True)

            categorias = {
                "Doações": CATEGORY_DOACOES,
                "Suporte": CATEGORY_SUPORTE,
                "Denúncias": CATEGORY_DENUNCIAS,
                "Assumir liderança": CATEGORY_LIDERANCA,
                "Ser criador de conteúdo": CATEGORY_CONTEUDO
            }

            category = guild.get_channel(categorias.get(self.escolha))
            if category is None or not isinstance(category, discord.CategoryChannel):
                return await interaction.followup.send("❌ Categoria inválida. Verifique IDs.", ephemeral=True)

            staff_role = guild.get_role(STAFF_ROLE_ID)
            bot_member = guild.me

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
            }
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
            if bot_member:
                overwrites[bot_member] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

            canal = await guild.create_text_channel(
                name=f"🎟️・{self.escolha.lower().replace(' ', '-')}-{interaction.user.name}",
                category=category,
                overwrites=overwrites
            )

            # guarda infos do ticket
            ticket_abertura[canal.id] = datetime.datetime.utcnow()
            ticket_staff[canal.id] = {"resp": None, "aux": None}

            # embed principal (com espaço pra resp/aux)
            embed = discord.Embed(
                title="Ticket Criado com Sucesso! 📌",
                description=(
                    "Todos os responsáveis pelo ticket já estão cientes da abertura.\n"
                    f"{interaction.user.mention}, evite chamar alguém via DM — aguarde que iremos atender."
                ),
                color=0x8B0000
            )
            embed.set_author(name=CONNECT_NAME, icon_url=CONNECT_LOGO_URL)
            embed.set_thumbnail(url=interaction.user.display_avatar.url)

            embed.add_field(name="Categoria Escolhida:", value=f"📌 **{self.escolha}**", inline=False)
            embed.add_field(
                name="Descreva o motivo do contato com o máximo de detalhes possíveis",
                value=f"```{self.motivo.value}```",
                inline=False
            )
            embed.add_field(name="👮 Responsável", value="`—`", inline=True)
            embed.add_field(name="🆘 Auxiliar", value="`—`", inline=True)

            embed.set_footer(text="OBS: Mantenha sua DM aberta para receber avisos e a opção de avaliar seu atendimento.")

            # manda 1 mensagem só (embed + botões)
            m = await canal.send(embed=embed, view=TicketControlView())
            ticket_msg_id[canal.id] = m.id

            await interaction.followup.send(f"✅ Seu ticket foi criado: {canal.mention}", ephemeral=True)

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ O bot não tem permissão. Dê: **Gerenciar Canais**, **Ver Canais**, **Enviar Mensagens**.",
                ephemeral=True
            )
            if canal:
                try:
                    await canal.delete()
                except:
                    pass
        except Exception as e:
            print("ERRO TicketMotivoModal:", repr(e))
            await interaction.followup.send(f"❌ Erro ao criar o ticket: `{e}`", ephemeral=True)
            if canal:
                try:
                    await canal.delete()
                except:
                    pass


class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Doações", description="Ticket sobre doações."),
            discord.SelectOption(label="Suporte", description="Ticket para suporte."),
            discord.SelectOption(label="Denúncias", description="Ticket para denúncias."),
            discord.SelectOption(label="Assumir liderança", description="Ticket para liderança."),
            discord.SelectOption(label="Ser criador de conteúdo", description="Ticket para criadores."),
        ]
        super().__init__(
            placeholder="Clique aqui para selecionar...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket:select"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketMotivoModal(self.values[0]))


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


# ===============================
# COMANDO /painel
# ===============================
@bot.tree.command(name="painel", description="Criar o painel de ticket")
@is_canal_painel()
async def painel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🔥 Atendimento Connect RP",
        description=(
            "│ **Sistema de Tickets para atendimentos aos jogadores**\n"
            "│ \n"
            "│ ❌ Não abra tickets sem **Necessidade**.\n"
            "│ ⚠️ Não marque excessivamente a *equipe*.\n"
        ),
        color=0x8B0000
    )
    embed.set_thumbnail(url=CONNECT_LOGO_URL)
    embed.set_image(url="https://cdn.discordapp.com/attachments/1471669099305111681/1475887473828560996/Arma.png")
    embed.set_footer(text="")

    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("✅ Painel enviado.", ephemeral=True)


@painel.error
async def painel_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(f"⚠️ Use este comando apenas no canal <#{CANAL_PAINEL_ID}>.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Erro: {error}", ephemeral=True)


@aplicar_punicao.error
async def aplicar_punicao_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("⚠️ Você não tem permissão ou está no canal errado.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Erro: {error}", ephemeral=True)


# ===============================
# RUN
# ===============================
if not TOKEN:
    raise RuntimeError("TOKEN não encontrado. Verifique o arquivo .env com TOKEN=...")

bot.run(TOKEN)