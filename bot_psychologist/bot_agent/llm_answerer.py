# bot_agent/llm_answerer.py
"""
LLM Answerer Module
===================

Р“РµРЅРµСЂР°С†РёСЏ РѕС‚РІРµС‚РѕРІ С‡РµСЂРµР· OpenAI API СЃ СЃРёСЃС‚РµРјРЅС‹Рј РїСЂРѕРјРїС‚РѕРј Р±РѕС‚Р°-РїСЃРёС…РѕР»РѕРіР°.
"""

import logging
from typing import List, Dict, Optional
from pathlib import Path

from .data_loader import Block
from .config import config

logger = logging.getLogger(__name__)

_PROMPT_BASE_PATH = Path(__file__).resolve().parent / "prompt_system_base.md"


def _read_prompt_text(path: Path) -> str:
    """
    Read UTF-8 prompt text from disk.
    We allow BOM so the file can be edited in Windows tools comfortably.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8-sig")
    return text.lstrip("\ufeff").strip()


class LLMAnswerer:
    """
    Р¤РѕСЂРјРёСЂСѓРµС‚ РѕС‚РІРµС‚ РЅР° РѕСЃРЅРѕРІРµ РЅР°Р№РґРµРЅРЅС‹С… Р±Р»РѕРєРѕРІ, РёСЃРїРѕР»СЊР·СѓСЏ OpenAI API.
    
    Usage:
        >>> answerer = LLMAnswerer()
        >>> result = answerer.generate_answer("Р§С‚Рѕ С‚Р°РєРѕРµ РѕСЃРѕР·РЅР°РІР°РЅРёРµ?", blocks)
        >>> print(result["answer"])
    """
    
    def __init__(self):
        self.api_key = config.OPENAI_API_KEY
        self.client = None
        
        if not self.api_key:
            logger.warning("вљ пёЏ OPENAI_API_KEY РЅРµ СѓСЃС‚Р°РЅРѕРІР»РµРЅ. LLM РѕС‚РІРµС‚С‹ РЅРµРґРѕСЃС‚СѓРїРЅС‹.")
        else:
            self._init_client()
    
    def _init_client(self):
        """РРЅРёС†РёР°Р»РёР·Р°С†РёСЏ OpenAI РєР»РёРµРЅС‚Р°"""
        try:
            import openai
            self.client = openai.OpenAI(api_key=self.api_key)
            logger.info("вњ“ OpenAI РєР»РёРµРЅС‚ РёРЅРёС†РёР°Р»РёР·РёСЂРѕРІР°РЅ")
        except ImportError:
            logger.error("вќЊ openai РЅРµ СѓСЃС‚Р°РЅРѕРІР»РµРЅ. РЈСЃС‚Р°РЅРѕРІРёС‚Рµ: pip install openai")
            raise
    
    def build_system_prompt(self) -> str:
        """
        РЎРёСЃС‚РµРјРЅС‹Р№ РїСЂРѕРјРїС‚ РґР»СЏ Р±РѕС‚Р°-РїСЃРёС…РѕР»РѕРіР°.
        
        РћРїСЂРµРґРµР»СЏРµС‚ РїРѕРІРµРґРµРЅРёРµ, С‚РѕРЅ Рё РѕРіСЂР°РЅРёС‡РµРЅРёСЏ Р±РѕС‚Р°.
        """
        try:
            return _read_prompt_text(_PROMPT_BASE_PATH)
        except FileNotFoundError:
            logger.warning(f"вљ пёЏ System prompt file not found: {_PROMPT_BASE_PATH}. Falling back to РІСЃС‚СЂРѕРµРЅРЅРѕРјСѓ РїСЂРѕРјРїС‚Сѓ.")
            return (
                "РўС‹ вЂ” СЃРїРѕРєРѕР№РЅС‹Р№ Рё С‚РѕС‡РЅС‹Р№ РїРѕРјРѕС‰РЅРёРє.\n"
                "РћС‚РІРµС‡Р°Р№ РїРѕ-СЂСѓСЃСЃРєРё. РћРїРёСЂР°Р№СЃСЏ РЅР° РјР°С‚РµСЂРёР°Р»С‹, РїРµСЂРµРґР°РЅРЅС‹Рµ РІ РєРѕРЅС‚РµРєСЃС‚Рµ. "
                "Р•СЃР»Рё РІ РјР°С‚РµСЂРёР°Р»Р°С… РЅРµС‚ РѕС‚РІРµС‚Р° вЂ” С‡РµСЃС‚РЅРѕ СЃРєР°Р¶Рё РѕР± СЌС‚РѕРј Рё РїРѕРїСЂРѕСЃРё СѓС‚РѕС‡РЅРµРЅРёРµ."
            )
    
    def build_context_prompt(
        self,
        blocks: List[Block],
        user_question: str,
        conversation_history: Optional[str] = None
    ) -> str:
        """
        Р¤РѕСЂРјРёСЂСѓРµС‚ РєРѕРЅС‚РµРєСЃС‚ РґР»СЏ LLM: РЅР°Р№РґРµРЅРЅС‹Рµ Р±Р»РѕРєРё + РІРѕРїСЂРѕСЃ.
        
        Args:
            blocks: РЎРїРёСЃРѕРє СЂРµР»РµРІР°РЅС‚РЅС‹С… Р±Р»РѕРєРѕРІ
            user_question: Р’РѕРїСЂРѕСЃ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
            conversation_history: РСЃС‚РѕСЂРёСЏ РїРѕСЃР»РµРґРЅРёС… N РѕР±РјРµРЅРѕРІ (РµСЃР»Рё РµСЃС‚СЊ)
            
        Returns:
            РћС‚С„РѕСЂРјР°С‚РёСЂРѕРІР°РЅРЅС‹Р№ РєРѕРЅС‚РµРєСЃС‚ РґР»СЏ LLM
        """
        context = ""

        if conversation_history:
            context += conversation_history.strip() + "\n\n"

        context += "РњРђРўР•Р РРђР› РР— Р›Р•РљР¦РР™:\n\n"
        
        for i, block in enumerate(blocks, 1):
            context += f"--- Р‘Р›РћРљ {i} ---\n"
            context += f"Р›РµРєС†РёСЏ: {block.document_title}\n"
            context += f"РўРµРјР°: {block.title}\n"
            context += f"РўР°Р№РјРєРѕРґ: {block.start} вЂ” {block.end}\n"
            context += f"РЎСЃС‹Р»РєР°: {block.youtube_link}\n"
            context += f"РљСЂР°С‚РєРѕРµ РѕРїРёСЃР°РЅРёРµ: {block.summary}\n"
            context += f"РџРѕР»РЅС‹Р№ С‚РµРєСЃС‚:\n{block.content}\n\n"
        
        context += f"Р’РћРџР РћРЎ РџРћР›Р¬Р—РћР’РђРўР•Р›РЇ:\n{user_question}\n\n"
        context += "РЎС„РѕСЂРјРёСЂСѓР№ РѕС‚РІРµС‚, РѕРїРёСЂР°СЏСЃСЊ РЅР° РјР°С‚РµСЂРёР°Р» РІС‹С€Рµ."
        
        return context
    
    def generate_answer(
        self,
        user_question: str,
        blocks: List[Block],
        conversation_history: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict:
        """
        Р¤РѕСЂРјРёСЂСѓРµС‚ РѕС‚РІРµС‚ С‡РµСЂРµР· OpenAI API.
        
        Args:
            user_question: Р’РѕРїСЂРѕСЃ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
            blocks: РЎРїРёСЃРѕРє СЂРµР»РµРІР°РЅС‚РЅС‹С… Р±Р»РѕРєРѕРІ
            model: РњРѕРґРµР»СЊ LLM (РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ РёР· config)
            temperature: РўРµРјРїРµСЂР°С‚СѓСЂР° РіРµРЅРµСЂР°С†РёРё
            max_tokens: РњР°РєСЃРёРјР°Р»СЊРЅР°СЏ РґР»РёРЅР° РѕС‚РІРµС‚Р°
            
        Returns:
            Dict СЃ РєР»СЋС‡Р°РјРё:
                - answer: str вЂ” РіРѕС‚РѕРІС‹Р№ РѕС‚РІРµС‚
                - model_used: str вЂ” РєР°РєСѓСЋ РјРѕРґРµР»СЊ РёСЃРїРѕР»СЊР·РѕРІР°Р»Рё
                - tokens_used: int вЂ” РєРѕР»РёС‡РµСЃС‚РІРѕ С‚РѕРєРµРЅРѕРІ
                - error: Optional[str] вЂ” РµСЃР»Рё Р±С‹Р»Р° РѕС€РёР±РєР°
        """
        # РћР±СЂР°Р±РѕС‚РєР° СЃР»СѓС‡Р°СЏ Р±РµР· Р±Р»РѕРєРѕРІ
        if not blocks:
            logger.warning("вљ пёЏ РќРµС‚ Р±Р»РѕРєРѕРІ РґР»СЏ РєРѕРЅС‚РµРєСЃС‚Р°!")
            return {
                "answer": "Рљ СЃРѕР¶Р°Р»РµРЅРёСЋ, СЏ РЅРµ РЅР°С€С‘Р» СЂРµР»РµРІР°РЅС‚РЅРѕРіРѕ РјР°С‚РµСЂРёР°Р»Р° РґР»СЏ СЌС‚РѕРіРѕ РІРѕРїСЂРѕСЃР°. РџРѕРїСЂРѕР±СѓР№С‚Рµ РїРµСЂРµС„РѕСЂРјСѓР»РёСЂРѕРІР°С‚СЊ.",
                "model_used": None,
                "tokens_used": 0,
                "error": "no_blocks"
            }
        
        # РџСЂРѕРІРµСЂРєР° РєР»РёРµРЅС‚Р°
        if not self.client:
            return {
                "answer": "вќЊ OpenAI API РЅРµРґРѕСЃС‚СѓРїРµРЅ. РџСЂРѕРІРµСЂСЊС‚Рµ OPENAI_API_KEY РІ .env",
                "model_used": None,
                "tokens_used": 0,
                "error": "no_api_key"
            }
        
        # РџР°СЂР°РјРµС‚СЂС‹
        model = model or config.LLM_MODEL
        temperature = temperature if temperature is not None else config.LLM_TEMPERATURE
        max_tokens = max_tokens or config.LLM_MAX_TOKENS
        
        # РџСЂРѕРјРїС‚С‹
        system_prompt = self.build_system_prompt()
        context = self.build_context_prompt(
            blocks,
            user_question,
            conversation_history=conversation_history
        )
        
        logger.debug(f"рџ“¤ РћС‚РїСЂР°РІР»СЏСЋ Р·Р°РїСЂРѕСЃ Рє {model}...")
        
        try:
            token_kwargs = self._token_limit_kwargs(model, max_tokens)
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context}
                ],
                **self._temperature_kwargs(model, temperature),
                **token_kwargs,
            )
            
            answer = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0
            
            logger.debug(f"вњ… РћС‚РІРµС‚ РїРѕР»СѓС‡РµРЅ ({tokens} С‚РѕРєРµРЅРѕРІ)")
            
            return {
                "answer": answer,
                "model_used": model,
                "tokens_used": tokens,
                "error": None
            }
        
        except Exception as e:
            logger.error(f"вќЊ РћС€РёР±РєР° РїСЂРё РІС‹Р·РѕРІРµ OpenAI API: {e}")
            return {
                "answer": f"РћС€РёР±РєР° РїСЂРё С„РѕСЂРјРёСЂРѕРІР°РЅРёРё РѕС‚РІРµС‚Р°: {str(e)}",
                "model_used": model,
                "tokens_used": 0,
                "error": str(e)
            }



    @staticmethod
    def _token_limit_kwargs(model: str, max_tokens: int) -> Dict[str, int]:
        """Build token-limit kwargs compatible with model family."""
        model_name = (model or "").lower().strip()
        if model_name.startswith("gpt-5"):
            return {"max_completion_tokens": max_tokens}
        return {"max_tokens": max_tokens}


    @staticmethod
    def _temperature_kwargs(model: str, temperature: float) -> Dict[str, float]:
        """Build temperature kwargs compatible with model family."""
        model_name = (model or "").lower().strip()
        if model_name.startswith("gpt-5"):
            return {}
        return {"temperature": temperature}
