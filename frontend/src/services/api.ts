export type ConversationRole = "user" | "assistant";

export interface ConversationMessage {
  role: ConversationRole;
  content: string;
}

export interface Source {
  id: number;
  content: string;
  section: string;
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
  metadata: Record<string, any>;
}

const API_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5001";

export async function sendChatMessage(
  message: string,
  conversation_history: ConversationMessage[]
): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation_history }),
  });

  // ერთხელ წაიკითხე body (json ან text)
  const contentType = res.headers.get("content-type") || "";

  if (!res.ok) {
    const errText = contentType.includes("application/json")
      ? JSON.stringify(await res.json()).slice(0, 2000)
      : (await res.text()).slice(0, 2000);

    console.error("❌ Backend error:", res.status, errText);
    throw new Error(errText || `Backend error: ${res.status} ${res.statusText}`);
  }

  const raw = (await res.json()) as any;

  // ✅ backend თუ აბრუნებს { success: true, data: {...} } - ამოიღე data
  const payload = raw?.data ?? raw;

  return {
    answer: payload?.answer ?? "",
    sources: payload?.sources ?? [],
    metadata: payload?.metadata ?? {},
  };
}
