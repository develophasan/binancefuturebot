import os
import json
import logging
from typing import Dict, Any, Optional
from emergentintegrations.llm.chat import LlmChat, UserMessage
from models import AIDecision, TradeAction

logger = logging.getLogger(__name__)

AI_SYSTEM_PROMPT = """You are an AGGRESSIVE long-only futures trading agent for Binance Testnet.
This is TESTNET - we can take risks and test strategies actively!
Your goal: FIND and EXECUTE profitable long opportunities frequently.

You ALWAYS receive JSON input with market data and must return JSON decision.

Your ONLY output format:

{
  "action": "OPEN_LONG" | "SKIP",
  "confidence": number (0-1),
  "reason": string,
  "position": {
    "position_size_mode": "FIXED_USDT",
    "position_size_value": number,
    "leverage": number
  },
  "risk": {
    "target_profit_percent": number,
    "stop_loss_percent": number
  }
}

AGGRESSIVE RULES:

1. ONLY SKIP IF:
   - trading_allowed == false
   - open_positions_count >= max_open_positions
   - trades_opened_today >= max_trades_per_day
   - remaining_daily_loss_capacity_usdt <= 0

2. OPEN_LONG STRATEGY (Be Aggressive):
   - ANY positive momentum is opportunity
   - RSI < 70 is acceptable (not just oversold)
   - Volume ratio > 0.8 is enough (not strict 1.0)
   - EMA trend DOWN is OK if RSI oversold (bounce opportunity)
   - High volatility = more profit potential
   - Symbol whitelist is OPTIONAL - top gainers are good signals

3. Confidence threshold:
   - >= 0.3 is enough to OPEN_LONG
   - We're in testnet, test actively!

4. Position sizing (be bold):
   - Use 3-5x leverage frequently
   - Position size: 10-20 USDT
   - Higher leverage for stronger signals

5. TP/SL (aggressive targets):
   - TP: 0.5-2% (aim higher on strong momentum)
   - SL: 0.1-0.2% (tight stops, quick exit if wrong)
   - Adjust based on volatility

6. Decision making:
   - FAVOR action over caution
   - Look for ANY positive signal
   - Top gainers are great opportunities
   - Recent momentum is key
   - This is TESTNET - experiment!

REMEMBER: This is TESTNET. Take calculated risks. Open positions frequently. Test strategies. Learn from data.
"""


class AIDecisionService:
    def __init__(self):
        self.api_key = os.getenv("EMERGENT_LLM_KEY")
        if not self.api_key:
            logger.error("EMERGENT_LLM_KEY not found in environment")
            raise ValueError("EMERGENT_LLM_KEY is required")
        
        logger.info("AI Decision Service initialized with Emergent LLM")
    
    async def make_decision(self, decision_input: Dict[str, Any]) -> AIDecision:
        """Send decision input to AI and get trading decision"""
        try:
            # Create chat instance
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"trade_decision_{decision_input.get('symbol', 'unknown')}",
                system_message=AI_SYSTEM_PROMPT
            )
            
            # Use GPT-4o for best decision making
            chat.with_model("openai", "gpt-4o")
            
            # Prepare user message
            user_message = UserMessage(
                text=json.dumps(decision_input, indent=2)
            )
            
            # Get AI response
            logger.info(f"Requesting AI decision for {decision_input.get('symbol')}")
            response = await chat.send_message(user_message)
            
            # Parse response
            logger.info(f"AI Response: {response}")
            
            # Try to extract JSON from response
            decision_data = self._extract_json(response)
            
            if not decision_data:
                logger.warning("Failed to parse AI response as JSON, defaulting to SKIP")
                return AIDecision(
                    action=TradeAction.SKIP,
                    confidence=0.0,
                    reason="Failed to parse AI response"
                )
            
            # Validate and create AIDecision
            return self._validate_decision(decision_data)
            
        except Exception as e:
            logger.error(f"Error in AI decision making: {e}", exc_info=True)
            return AIDecision(
                action=TradeAction.SKIP,
                confidence=0.0,
                reason=f"Error: {str(e)}"
            )
    
    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from AI response text"""
        try:
            # Try direct JSON parse
            return json.loads(text)
        except:
            pass
        
        # Try to find JSON in markdown code block
        import re
        json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass
        
        # Try to find raw JSON object
        json_match = re.search(r'{.*}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except:
                pass
        
        return None
    
    def _validate_decision(self, data: Dict[str, Any]) -> AIDecision:
        """Validate and clean AI decision data"""
        action = data.get('action', 'SKIP')
        if action not in ['OPEN_LONG', 'SKIP']:
            action = 'SKIP'
        
        confidence = float(data.get('confidence', 0.0))
        confidence = max(0.0, min(1.0, confidence))  # Clamp between 0-1
        
        reason = data.get('reason', 'No reason provided')
        
        position = data.get('position')
        risk = data.get('risk')
        
        return AIDecision(
            action=TradeAction(action),
            confidence=confidence,
            reason=reason,
            position=position,
            risk=risk
        )