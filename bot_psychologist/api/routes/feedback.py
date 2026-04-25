"""Feedback-роуты API."""

from fastapi import APIRouter, Depends, HTTPException, status

from bot_agent.conversation_memory import get_conversation_memory

from ..auth import verify_api_key
from ..models import FeedbackRequest, FeedbackResponse
from .common import logger

router = APIRouter(prefix="/api/v1", tags=["bot"])

@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    summary="Отправить обратную связь",
    description="Отправить обратную связь на ответ"
)
async def submit_feedback(
    request: FeedbackRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Отправить обратную связь на ответ.
    
    **Типы обратной связи:**
    - `positive`: Ответ был полезен ✅
    - `negative`: Ответ не помог ❌
    - `neutral`: Нейтральная оценка 🤷
    
    **Рейтинг:** 1-5 звезд
    """
    
    logger.info(f"👍 Обратная связь от {request.user_id}: {request.feedback}")
    
    try:
        memory = get_conversation_memory(request.user_id)
        memory.add_feedback(
            turn_index=request.turn_index,
            feedback=request.feedback.value,
            rating=request.rating
        )
        
        return FeedbackResponse(
            status="success",
            message="Обратная связь сохранена",
            user_id=request.user_id,
            turn_index=request.turn_index
        )
    
    except IndexError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ход #{request.turn_index} не найден"
        )
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

