import os
import json
import logging
from typing import Dict, Any, Optional
from emergentintegrations.llm.chat import LlmChat, UserMessage
from models import AIDecision, TradeAction

logger = logging.getLogger(__name__)

AI_SYSTEM_PROMPT = """You are a long-only futures trading decision agent used inside a Python Binance trading bot.
You never send orders yourself. You only return JSON decisions.
You specialize in small short-term profit strategies with strict risk control.
You are conservative, disciplined, and skip trades if conditions are unclear.

You ALWAYS receive JSON input with:
- symbol, timeframe
- OHLCV candles[]
- technical indicators (EMA fast/slow, EMA trend, RSI, RSI state, ATR, volatility, volume ratio)
- account snapshot (equity, free margin, daily PnL)
- risk state (allowed or not, daily limits, open positions)
- user parameters (TP, SL, leverage, size, risk profile)
- context (timezone, symbol whitelist)

Your ONLY output is:

{
  "action": "OPEN_LONG" or "SKIP",
  "confidence": number (0-1),
  "reason": string,
  "position": {
    "position_size_mode": "FIXED_USDT" or "PERCENT_OF_EQUITY",
    "position_size_value": number,
    "leverage": number
  },
  "risk": {
    "target_profit_percent": number,
    "stop_loss_percent": number
  }
}

RULES:

1. ALWAYS SKIP IF ANY:
   - trading_allowed == false
   - open_positions_count >= max_open_positions
   - trades_opened_today >= max_trades_per_day
   - remaining_daily_loss_capacity_usdt <= 0
   - symbol not in whitelist
   - free_margin too low

2. LONG ONLY.
   - Never consider shorts.
   - Avoid downtrend unless extreme oversold bounce.

3. Market conditions required for OPEN_LONG:
   - EMA trend UP or FLAT (not strongly DOWN)
   - RSI <= 50 (prefer OVERSOLD/NEUTRAL)
   - volume_ma_ratio > 1.0
   - volatility not extremely low

4. Confidence:
   - must be >= 0.6 to OPEN_LONG
   - else SKIP

5. Risk:
   - Never exceed user max leverage or min leverage range
   - Never exceed user set stop_loss_percent or max_risk_per_trade_percent
   - Use realistic TP/SL based on volatility

6. Behavior:
   - Conservative by default
   - Skip often if uncertain
   - Provide a short meaningful reason
   - NEVER output anything except the JSON object
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