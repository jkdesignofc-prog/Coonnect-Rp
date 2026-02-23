require("dotenv").config();
const { Client, GatewayIntentBits, Partials, Events } = require("discord.js");

const tickets = require("./features/tickets");
const punish = require("./features/punishments");
const antilinks = require("./features/antilinks");

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent, // precisa estar ligado no Dev Portal
  ],
  partials: [Partials.Channel],
});

client.once(Events.ClientReady, c => {
  console.log(`✅ Logado como ${c.user.tag}`);
});

client.on(Events.MessageCreate, (message) => {
  tickets.onMessageCreate(message);
  antilinks.onMessageCreate(message);
});

client.on(Events.InteractionCreate, async (interaction) => {
  try {
    // SLASH COMMANDS
    if (interaction.isChatInputCommand()) {
      if (interaction.commandName === "ticket-panel") return tickets.sendTicketPanel(interaction);
      if (interaction.commandName === "punicoes") return punish.openPanel(interaction);
      if (interaction.commandName === "antilinks") {
        const status = interaction.options.getString("status", true);
        return antilinks.setEnabled(interaction, status === "on");
      }
    }

    // SELECT MENUS
    if (interaction.isStringSelectMenu()) {
      if (interaction.customId === tickets.ID.selectCategory) {
        const cat = interaction.values[0];
        return tickets.openTicketModal(interaction, cat);
      }

      if (interaction.customId.startsWith(`${punish.ID.applySelect}:`)) {
        return punish.handleApplySelect(interaction);
      }

      if (interaction.customId.startsWith(`${punish.ID.removeSelect}:`)) {
        return punish.handleRemoveSelect(interaction);
      }
    }

    // BUTTONS
    if (interaction.isButton()) {
      if (interaction.customId === tickets.ID.claim) return tickets.claimTicket(interaction);
      if (interaction.customId === tickets.ID.adminPanel) return tickets.showAdminPanel(interaction);
      if (interaction.customId === tickets.ID.close) return tickets.closeTicketFlow(interaction);
      if (interaction.customId === tickets.ID.history) return tickets.showHistory(interaction);
      if (interaction.customId === tickets.ID.transcript) return tickets.sendTranscript(interaction);
    }

    // MODALS
    if (interaction.isModalSubmit()) {
      // criar ticket modal
      if (interaction.customId.startsWith(`${tickets.ID.openModal}:`)) {
        const cat = interaction.customId.split(":")[1];
        return tickets.createTicketFromModal(interaction, cat);
      }

      // fechar ticket modal
      if (interaction.customId === tickets.ID.closeModal) {
        return tickets.closeTicketFromModal(interaction);
      }

      // punição motivo modal
      if (interaction.customId.startsWith(`${punish.ID.reasonModal}:`)) {
        return punish.handleReasonModal(interaction);
      }
    }
  } catch (err) {
    console.error(err);
    if (interaction.isRepliable()) {
      interaction.reply({ content: "❌ Ocorreu um erro ao processar.", ephemeral: true }).catch(() => {});
    }
  }
});

client.login(process.env.DISCORD_TOKEN);