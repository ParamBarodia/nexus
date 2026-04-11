/**
 * Nexus WhatsApp Bridge
 * Runs whatsapp-web.js and exposes HTTP API on :8766 for the Python brain.
 */

const { Client, LocalAuth } = require("whatsapp-web.js");
const qrcode = require("qrcode-terminal");
const express = require("express");

const BRAIN_URL = process.env.JARVIS_BRAIN_URL || "http://localhost:8765";
const PORT = parseInt(process.env.WHATSAPP_BRIDGE_PORT || "8766");
const ALLOWED_NUMBERS = (process.env.WHATSAPP_ALLOWED_NUMBERS || "")
  .split(",")
  .map((n) => n.trim())
  .filter(Boolean);

const app = express();
app.use(express.json());

let clientReady = false;
let qrString = null;

// WhatsApp Client
const client = new Client({
  authStrategy: new LocalAuth({
    dataPath: "C:\\jarvis\\data\\whatsapp_session",
  }),
  puppeteer: {
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  },
});

client.on("qr", (qr) => {
  qrString = qr;
  console.log("[Bridge] Scan this QR code with WhatsApp:");
  qrcode.generate(qr, { small: true });
});

client.on("ready", () => {
  clientReady = true;
  qrString = null;
  console.log("[Bridge] WhatsApp client ready!");
});

client.on("disconnected", (reason) => {
  clientReady = false;
  console.log("[Bridge] Disconnected:", reason);
});

// Incoming message handler — forward to brain
client.on("message", async (msg) => {
  const from = msg.from.replace("@c.us", "").replace("@g.us", "");
  const body = msg.body;

  console.log(`[Bridge] Message from ${from}: ${body.substring(0, 100)}`);

  // Whitelist check — exact match after normalizing (strip +, spaces, dashes)
  const normalize = (n) => n.replace(/[\s\-+]/g, "");
  if (ALLOWED_NUMBERS.length > 0) {
    const normalizedFrom = normalize(from);
    const allowed = ALLOWED_NUMBERS.some((n) => normalizedFrom === normalize(n));
    if (!allowed) {
      console.log(`[Bridge] Blocked: ${from} not in whitelist`);
      return;
    }
  }

  // Forward to brain
  try {
    const resp = await fetch(`${BRAIN_URL}/whatsapp/incoming`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from, body, timestamp: Date.now() }),
    });
    const data = await resp.json();

    // If brain returns a reply, send it back
    if (data.reply) {
      await msg.reply(data.reply);
      console.log(`[Bridge] Replied to ${from}: ${data.reply.substring(0, 100)}`);
    }
  } catch (err) {
    console.error("[Bridge] Failed to forward to brain:", err.message);
  }
});

// --- HTTP API ---

app.get("/status", (req, res) => {
  res.json({
    connected: clientReady,
    qr_pending: !!qrString,
  });
});

app.get("/qr", (req, res) => {
  if (qrString) {
    res.json({ qr: qrString });
  } else if (clientReady) {
    res.json({ qr: null, message: "Already connected" });
  } else {
    res.json({ qr: null, message: "Waiting for QR generation..." });
  }
});

app.post("/send", async (req, res) => {
  const { number, message } = req.body;
  if (!clientReady) {
    return res.status(503).json({ error: "WhatsApp not connected" });
  }
  try {
    // Ensure number format: country code + number + @c.us
    const chatId = number.replace("+", "") + "@c.us";
    await client.sendMessage(chatId, message);
    console.log(`[Bridge] Sent to ${number}: ${message.substring(0, 100)}`);
    res.json({ ok: true });
  } catch (err) {
    console.error("[Bridge] Send failed:", err.message);
    res.status(500).json({ error: err.message });
  }
});

// Start
app.listen(PORT, () => {
  console.log(`[Bridge] HTTP API on port ${PORT}`);
});

client.initialize();
console.log("[Bridge] WhatsApp bridge starting...");
