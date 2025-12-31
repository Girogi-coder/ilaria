import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DATA_DIR = path.join(__dirname, "..", "data");
const DATA_FILE = path.join(DATA_DIR, "conversations.json");

let conversations = {};
let loaded = false;

function load() {
  if (loaded) return;

  try {
    if (!fs.existsSync(DATA_DIR)) {
      fs.mkdirSync(DATA_DIR, { recursive: true });
    }

    if (fs.existsSync(DATA_FILE)) {
      const raw = fs.readFileSync(DATA_FILE, "utf-8");
      conversations = JSON.parse(raw || "{}");
    } else {
      conversations = {};
    }
  } catch (e) {
    console.error("❌ Failed to load conversations:", e);
    conversations = {};
  }

  loaded = true;
}

function save() {
  try {
    fs.writeFileSync(DATA_FILE, JSON.stringify(conversations, null, 2), "utf-8");
  } catch (e) {
    console.error("❌ Failed to save conversations:", e);
  }
}

function createConversation(firstMessageText) {
  load();

  const id = `c_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  const createdAt = new Date().toISOString();
  const title =
    (firstMessageText || "ახალი ჩატი").split("\n")[0].slice(0, 50) +
    (firstMessageText && firstMessageText.length > 50 ? "..." : "");

  conversations[id] = {
    id,
    title,
    createdAt,
    updatedAt: createdAt,
    messages: [],
  };

  save();
  return id;
}

function addMessage(conversationId, message) {
  load();
  const conv = conversations[conversationId];
  if (!conv) return;

  conv.messages.push({
    id: `m_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    role: message.role,
    content: message.content,
    timestamp: new Date().toISOString(),
  });

  conv.updatedAt = new Date().toISOString();
  save();
}

function getConversationsList() {
  load();
  return Object.values(conversations)
    .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))
    .map((c) => ({
      id: c.id,
      title: c.title,
      createdAt: c.createdAt,
      updatedAt: c.updatedAt,
    }));
}

function getConversation(conversationId) {
  load();
  return conversations[conversationId] || null;
}

export {
  createConversation,
  addMessage,
  getConversationsList,
  getConversation,
};
