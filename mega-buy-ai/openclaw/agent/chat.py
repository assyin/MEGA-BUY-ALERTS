"""Conversational chat with persistent memory.

Each conversation is stored in Supabase with full message history.
The agent has access to all its tools + past conversation context.
"""

import json
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timezone

import anthropic
from openai import OpenAI

from openclaw.config import get_settings
from openclaw.agent.tools import TOOLS
from openclaw.agent.tool_handlers import TOOL_HANDLERS
from openclaw.agent.prompts import SYSTEM_PROMPT
from openclaw.memory.insights import InsightsStore
from openclaw.agent.token_tracker import get_token_tracker


INSIGHT_TOOL = {
    "name": "save_insight",
    "description": """Sauvegarde un insight strategique important issu de cette conversation.
Appelle ce tool quand:
- L'utilisateur definit une nouvelle regle de trading (ex: "ne trade jamais quand BTC est bearish")
- On decouvre un pattern performant via l'analyse (ex: "les trades avec score 10/10 + 4h ont 80% WR")
- L'utilisateur exprime une preference claire (ex: "je prefere les trades avec R:R > 1:2")
- On identifie un piege a eviter (ex: "les trades DEGO avec RSI > 90 sont des pieges")
- L'utilisateur valide ou invalide une strategie

IMPORTANT: Chaque insight sera injecte dans ton prompt lors de futures analyses d'alertes.
Donc formule l'insight comme une REGLE actionnable.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "insight": {
                "type": "string",
                "description": "La regle ou l'insight a memoriser, formule comme une instruction actionnable"
            },
            "category": {
                "type": "string",
                "enum": ["strategy", "risk", "filter", "preference", "pattern"],
                "description": "Categorie de l'insight"
            },
            "priority": {
                "type": "integer",
                "description": "Priorite 1-10 (10 = critique, 5 = normal)",
                "default": 5
            }
        },
        "required": ["insight", "category"]
    }
}

CHAT_SYSTEM_PROMPT = SYSTEM_PROMPT + """

## Mode Conversation
Tu es en mode conversation avec l'utilisateur. Il peut te poser des questions sur:
- L'analyse d'un trade specifique
- Les strategies de trading
- L'historique des decisions
- Les ameliorations a apporter au systeme
- Le contexte du marche

Tu as acces a tous tes tools (analyze_alert, get_backtest_history, get_market_context, etc.).
Utilise-les quand c'est pertinent pour repondre avec des donnees reelles.

## IMPORTANT: Apprentissage par la conversation
Tu as un tool special `save_insight` qui sauvegarde des regles strategiques.
**Utilise-le activement** quand:
1. L'utilisateur dit "retiens ca", "souviens-toi", "a l'avenir", "desormais"
2. On decouvre un pattern gagnant/perdant via l'analyse des donnees
3. L'utilisateur definit une preference ou une regle de trading
4. On valide ou invalide une hypothese avec des chiffres

Chaque insight sauvegarde sera injecte dans ton prompt lors de tes futures analyses d'alertes.
C'est comme ca que tu t'ameliores au fil du temps.

Exemples d'insights a sauvegarder:
- "Ne jamais recommander BUY quand Fear & Greed < 20 (Extreme Fear)"
- "Les trades avec score 10/10 + combo 1h+4h ont historiquement 75% de win rate"
- "L'utilisateur prefere un R:R minimum de 1:2 avant de confirmer un trade"
- "DEGO et les tokens gaming ont tendance a faire des pump & dump — prudence accrue"

{insights_block}
"""


class ChatManager:
    """Manages persistent conversations with Claude + insight extraction."""

    def __init__(self):
        settings = get_settings()
        # OpenAI primary, Claude backup
        self.openai_client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.claude_client = anthropic.Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None
        self.model = "gpt-4o-mini" if self.openai_client else settings.openclaw_model
        self.max_tokens = settings.openclaw_max_tokens
        self.insights = InsightsStore()

        from supabase import create_client
        self.sb = create_client(settings.supabase_url, settings.supabase_service_key)
        self._conversations_ok = True
        try:
            self.sb.table("agent_conversations").select("id").limit(1).execute()
        except Exception:
            self._conversations_ok = False
            print("⚠️ agent_conversations table not found")

    # === CONVERSATION CRUD ===

    def create_conversation(self, title: str = "Nouvelle conversation") -> Optional[str]:
        """Create a new conversation, return its ID."""
        if not self._conversations_ok:
            return None
        try:
            result = self.sb.table("agent_conversations").insert({
                "title": title,
                "messages": [],
            }).execute()
            return result.data[0]["id"] if result.data else None
        except Exception as e:
            print(f"⚠️ Create conversation error: {e}")
            return None

    def get_conversation(self, conv_id: str) -> Optional[Dict]:
        """Get a conversation by ID."""
        if not self._conversations_ok:
            return None
        try:
            result = self.sb.table("agent_conversations") \
                .select("*").eq("id", conv_id).single().execute()
            return result.data
        except Exception:
            return None

    def list_conversations(self, limit: int = 20) -> List[Dict]:
        """List recent conversations."""
        if not self._conversations_ok:
            return []
        try:
            result = self.sb.table("agent_conversations") \
                .select("id, title, created_at, updated_at, tags") \
                .order("updated_at", desc=True) \
                .limit(limit).execute()
            return result.data or []
        except Exception:
            return []

    def update_conversation(self, conv_id: str, messages: List[Dict], title: str = None):
        """Update conversation messages."""
        if not self._conversations_ok:
            return
        try:
            data = {
                "messages": messages,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            if title:
                data["title"] = title
            self.sb.table("agent_conversations") \
                .update(data).eq("id", conv_id).execute()
        except Exception as e:
            print(f"⚠️ Update conversation error: {e}")

    def delete_conversation(self, conv_id: str):
        """Delete a conversation."""
        if not self._conversations_ok:
            return
        try:
            self.sb.table("agent_conversations") \
                .delete().eq("id", conv_id).execute()
        except Exception:
            pass

    # === CHAT ===

    async def send_message(self, conv_id: str, user_message: str) -> str:
        """Send a message in a conversation, get agent response."""
        # Load conversation
        conv = self.get_conversation(conv_id)
        if not conv:
            return "Conversation not found"

        messages = conv.get("messages", [])

        # Add user message
        messages.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Build API messages (only role + content for Claude)
        api_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
        ]

        # Run Claude with tool-use loop
        assistant_text = await self._run_chat_loop(api_messages, conv_id)

        # Add assistant response
        messages.append({
            "role": "assistant",
            "content": assistant_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Auto-title on first message
        title = conv.get("title")
        if title == "Nouvelle conversation" and len(messages) == 2:
            title = user_message[:60] + ("..." if len(user_message) > 60 else "")

        # Save
        self.update_conversation(conv_id, messages, title)

        return assistant_text

    async def _run_chat_loop(self, messages: List[Dict], conv_id: str = "") -> str:
        """Run Claude tool-use loop for chat with insight extraction."""
        # Build system prompt with current insights injected
        insights_block = self.insights.format_for_prompt()
        system = CHAT_SYSTEM_PROMPT.replace("{insights_block}", insights_block)

        # Add save_insight tool to the regular tools
        chat_tools = TOOLS + [INSIGHT_TOOL]

        tracker = get_token_tracker()

        # Convert tools to OpenAI format
        openai_tools = []
        for tool in chat_tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                }
            })

        if self.openai_client:
            return await self._openai_chat_loop(messages, system, openai_tools, conv_id, tracker)
        elif self.claude_client:
            return await self._claude_chat_loop(messages, system, chat_tools, conv_id, tracker)
        return "No AI provider configured"

    async def _openai_chat_loop(self, messages, system, tools, conv_id, tracker):
        """Chat loop using OpenAI."""
        oai_messages = [{"role": "system", "content": system}]
        for m in messages:
            oai_messages.append({"role": m["role"], "content": m["content"]})

        for _ in range(8):
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=self.model,
                max_tokens=self.max_tokens,
                messages=oai_messages,
                tools=tools,
                tool_choice="auto",
            )
            tracker.record_openai(dict(response.usage), self.model)

            choice = response.choices[0]
            if choice.message.tool_calls:
                oai_messages.append(choice.message)
                for tc in choice.message.tool_calls:
                    tool_name = tc.function.name
                    try:
                        tool_input = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        tool_input = {}

                    if tool_name == "save_insight":
                        insight_text = tool_input.get("insight", "")
                        category = tool_input.get("category", "strategy")
                        priority = tool_input.get("priority", 5)
                        self.insights.add_insight(insight_text, category, conv_id, priority)
                        result = {"saved": True, "insight": insight_text, "category": category}
                        print(f"  💡 New insight [{category}] (P{priority}): {insight_text[:80]}")
                    else:
                        handler = TOOL_HANDLERS.get(tool_name)
                        if handler:
                            try:
                                result = await handler(**tool_input)
                            except Exception as e:
                                result = {"error": str(e)}
                        else:
                            result = {"error": f"Unknown tool: {tool_name}"}

                    oai_messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, default=str),
                    })
            else:
                return choice.message.content or ""

        return "Analyse trop complexe."

    async def _claude_chat_loop(self, messages, system, chat_tools, conv_id, tracker):
        """Fallback chat loop using Claude."""
        for _ in range(8):
            response = await asyncio.to_thread(
                self.claude_client.messages.create,
                model="claude-sonnet-4-20250514",
                max_tokens=self.max_tokens,
                system=system,
                tools=chat_tools,
                messages=messages,
            )
            tracker.record(response, "claude-sonnet-4-20250514")

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        if block.name == "save_insight":
                            self.insights.add_insight(block.input.get("insight", ""), block.input.get("category", "strategy"), conv_id, block.input.get("priority", 5))
                            result = {"saved": True}
                        else:
                            handler = TOOL_HANDLERS.get(block.name)
                            result = await handler(**block.input) if handler else {"error": "unknown"}
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result, default=str)})
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                return "".join(b.text for b in response.content if hasattr(b, "text"))

        return "Analyse trop complexe."
