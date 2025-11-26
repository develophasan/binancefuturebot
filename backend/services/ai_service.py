import os
import json
import logging
from typing import Dict, Any, Optional
from emergentintegrations.llm.chat import LlmChat, UserMessage
from models import AIDecision, TradeAction

logger = logging.getLogger(__name__)

AI_SYSTEM_PROMPT = """You are a PROFESSIONAL futures trading AI with focus on PROFITABILITY and RISK MANAGEMENT.
Your goal: Open ONLY high-probability LONG positions that are likely to profit.

You receive JSON market data and return JSON decision.

OUTPUT FORMAT:
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

PROFITABLE TRADING RULES:

1. MANDATORY SKIP CONDITIONS:
   - trading_allowed == false
   - open_positions_count >= max_open_positions
   - trades_opened_today >= max_trades_per_day
   - remaining_daily_loss_capacity_usdt <= 0

2. QUALITY ENTRY SIGNALS (ALL must be true for OPEN_LONG):
   
   A. TREND CONFIRMATION:
   - EMA trend MUST be "UP" (not DOWN or FLAT)
   - EMA_fast > EMA_slow (bullish crossover)
   
   B. MOMENTUM:
   - RSI between 30-65 (not overbought, preferably oversold recovery)
   - RSI_state = "OVERSOLD" or "NEUTRAL" (never OVERBOUGHT)
   
   C. VOLUME STRENGTH:
   - volume_ma_ratio >= 1.2 (strong volume confirmation)
   - Recent volume increasing
   
   D. VOLATILITY:
   - Moderate volatility (0.01-0.03 range)
   - Not extremely high (risky) or low (no movement)
   
   E. PRICE ACTION:
   - Recent candles show bullish pattern
   - No sudden dumps or spikes
   - Clean uptrend structure

3. CONFIDENCE SCORING:
   - 0.7-1.0: Perfect setup (all signals aligned)
   - 0.5-0.69: Good setup (most signals positive)
   - Below 0.5: SKIP (not worth the risk)
   
   Minimum confidence for OPEN_LONG: 0.55

4. SMART POSITION SIZING:
   - Base: 50 USDT
   - Confidence 0.7+: Use 3-4x leverage
   - Confidence 0.55-0.69: Use 2-3x leverage
   
5. RISK/REWARD OPTIMIZATION:
   
   TP TARGETS (based on volatility):
   - Low volatility (<0.015): TP = 0.8-1.5%
   - Medium volatility (0.015-0.025): TP = 1.5-2.5%
   - High volatility (>0.025): TP = 2.5-4%
   
   SL PROTECTION (tight but realistic):
   - Always 0.3-0.5% below entry
   - Never wider than 0.5%
   - Risk/Reward ratio minimum 2:1
   
6. SKIP REASONS (Be selective!):
   - "Trend not bullish enough"
   - "RSI too high - overbought risk"
   - "Volume too weak - no conviction"
   - "Volatility unsuitable"
   - "Recent price action unclear"
   - "Better opportunities expected"

REMEMBER: 
- Quality over quantity
- Each trade must have edge
- Protect capital first
- Only trade when probability is high
- Better to miss trade than lose money
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