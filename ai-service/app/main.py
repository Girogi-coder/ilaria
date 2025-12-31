import os
from typing import List, Dict, Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

ERROR_MESSAGES = {
    "empty_query": "გთხოვთ დაწეროთ თქვენი კითხვა",
    "service_unavailable": "სერვისი დროებით მიუწვდომელია",
    "processing_error": "შეცდომა დამუშავებისას",
}


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: List[ConversationMessage] = []


class Source(BaseModel):
    id: int
    content: str
    section: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]
    metadata: Dict[str, Any]


class RagService:
    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY არ არის განსაზღვრული .env ფაილში")

        genai.configure(api_key=api_key)

        self.model_name = os.getenv("LLM_MODEL", "gemini-2.5-flash")
        self.model = genai.GenerativeModel(self.model_name)

    async def generate_response(
        self,
        query: str,
        history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        history სტრუქტურა:
        [
          {"role": "user" | "assistant", "content": "..."},
          ...
        ]
        """

        history_text_lines: List[str] = []
        for msg in history:
            prefix = "User" if msg["role"] == "user" else "Assistant"
            history_text_lines.append(f"{prefix}: {msg['content']}")

        history_text = "\n".join(history_text_lines) if history_text_lines else "—"

        system_instruction = (
            "შენ ხარ დამხმარე AI ასისტენტი ilaria აპისთვის. "
            "უპასუხე მკაფიოდ, სტრუქტურირებულად და მაქსიმალურად სასარგებლოდ. "
            "თუ კითხვა არ არის ნათელი, სთხოვი მომხმარებელს დაზუსტებას."
            "თუ მომხმარებელმა კითხვა დაგისვა ინგლისურად მხოლოდ მაგ შემთხვევაში უპასუხე ინგლისურად"
        )

        full_prompt = (
            f"{system_instruction}\n\n"
            f"საუბრის ისტორია:\n{history_text}\n\n"
            f"ახლა მომხმარებლის ახალი კითხვა:\nUser: {query}\n\n"
            "გთხოვ დეტალური და გასაგები პასუხი ქართულად."
        )

        try:
            response = self.model.generate_content(full_prompt)

            if not response or not getattr(response, "text", None):
                answer_text = "ვერ შევძელი ამ კითხვის დამუშავება, სცადე სხვა ფორმულირება."
            else:
                answer_text = response.text

            sources = [
                {
                    "content": "პასუხი გენერირებულია Gemini მოდელით მოცემული ისტორიის და კითხვის საფუძველზე.",
                    "section": f"model: {self.model_name}",
                }
            ]

            metadata = {
                "model": self.model_name,
                "has_history": bool(history),
            }

            return {
                "answer": answer_text,
                "source_documents": sources,
                "metadata": metadata,
            }

        except Exception as e:
            print(f"❌ Gemini error in RagService.generate_response: {e}")

            fallback_answer = (
                "ამ წუთას ვერ ვაკავშირებ AI მოდელს (Gemini). "
                "სცადე კიდევ ერთხელ რამდენიმე წუთში ან ხელახლა გადატვირთე სისტემა."
            )

            return {
                "answer": fallback_answer,
                "source_documents": [],
                "metadata": {
                    "model": self.model_name,
                    "error": str(e),
                    "has_history": bool(history),
                },
            }



try:
    rag_service: RagService | None = RagService()
except Exception as e:
    print(f"❌ RagService init error: {e}")
    rag_service = None


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # production-ში შეგიძლია შეცვალო კონკრეტული დომენით
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "rag_service_ready": rag_service is not None}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not rag_service:
        raise HTTPException(
            status_code=503,
            detail=ERROR_MESSAGES["service_unavailable"],
        )

    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES["empty_query"],
        )

    try:
        history_payload = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ]

        raw = await rag_service.generate_response(
            query=request.message,
            history=history_payload,
        )

        sources: List[Source] = []
        for i, doc in enumerate(raw.get("source_documents", [])):
            sources.append(
                Source(
                    id=i,
                    content=doc.get("content", ""),
                    section=doc.get("section", ""),
                )
            )

        response = ChatResponse(
            answer=raw.get("answer", ""),
            sources=sources,
            metadata=raw.get("metadata", {}),
        )
        return response

    except HTTPException:
        raise

    except Exception as e:
        print(f"❌ Error in /api/chat: {e}")
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES["processing_error"],
        )


@app.post("/chat", response_model=ChatResponse)
async def chat_alias(request: ChatRequest):
    return await chat(request)
