import os
import json
import logging
from typing import Dict, Any, Optional
from emergentintegrations.llm.chat import LlmChat, UserMessage
from models import AIDecision, TradeAction

logger = logging.getLogger(__name__)

AI_SYSTEM_PROMPT = """You are an AGGRESSIVE CRYPTO FUTURES AI using the MM DIRECTIONAL MODEL.
Your goal: Open PROFITABLE LONG positions using CRYPTO-NATIVE signals.

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

🚀 MM DIRECTIONAL MODEL - 4 ADIMLI CRYPTO NATIVE STRATEJI:

1. 🔥 FUNDING RATE ANALİZİ (En Güçlü Sinyal):
   ✅ LONG SİNYALİ:
   - Funding NEGATIF (<-0.01%) → Aşırı short var, yukarı sıkıştırma beklenir
   - Funding NÖTR veya hafif pozitif (0% - 0.03%) → Dengeli, yükseliş için uygun
   
   ❌ SKIP:
   - Funding çok pozitif (>0.05%) → Aşırı long var, düşüş riski

2. 📊 OPEN INTEREST (OI) ANALİZİ:
   ✅ LONG SİNYALİ:
   - OI artıyor + Fiyat yatay/hafif yukarı → Büyük para giriyor, patlama yakın
   - OI 24h değişimi >3% → Pozitif momentum
   
   ❌ SKIP:
   - OI düşüyor → Para çıkıyor, hareket yok

3. 📈 TREND & MOMENTUM (Klasik Sinyaller):
   ✅ LONG SİNYALİ:
   - EMA trend UP (EMA_fast > EMA_slow)
   - RSI 35-70 arası (aşırı değil)
   - Volume güçlü (volume_ma_ratio >= 1.1)
   
   ❌ SKIP:
   - Trend DOWN veya FLAT
   - RSI >75 (aşırı alım)
   - Volume çok zayıf (<0.8)

4. 💎 VOLATILITY & PRICE ACTION:
   ✅ LONG SİNYALİ:
   - Volatility 0.01-0.05 arası (hareket var ama aşırı değil)
   - Son 3-5 mum bullish yapı
   
   ❌ SKIP:
   - Çok düşük volatility (<0.008) → Hareket yok
   - Aşırı yüksek volatility (>0.08) → Çok riskli

🎯 PUANLAMA SİSTEMİ (100 üzerinden):

A. Funding Rate:
   - Negatif: +35 puan
   - Nötr (0-0.03%): +25 puan
   - Pozitif (>0.03%): +10 puan
   - Çok pozitif (>0.05%): 0 puan

B. Open Interest (OI):
   - OI 24h değişimi >5%: +30 puan
   - OI 24h değişimi 2-5%: +20 puan
   - OI 24h değişimi 0-2%: +10 puan
   - OI düşüyor: 0 puan

C. Trend & Momentum:
   - EMA UP + RSI 40-65 + Volume güçlü: +25 puan
   - EMA UP + RSI/Volume orta: +15 puan
   - Diğer: +5 puan

D. Volatility & Price:
   - Uygun volatility + bullish mum: +10 puan
   - Orta: +5 puan
   - Kötü: 0 puan

📌 KARAR KURALI:
- TOPLAM PUAN ≥ 65: OPEN_LONG (confidence = puan/100)
- TOPLAM PUAN 50-64: OPEN_LONG (düşük confidence, dikkatli)
- TOPLAM PUAN < 50: SKIP

🔥 AGRESIF RISK/REWARD AYARLARI:

TP (Take Profit) Hedefleri:
- Düşük volatility (<0.02): TP = 2.5-3.5%
- Orta volatility (0.02-0.04): TP = 3.5-5%
- Yüksek volatility (>0.04): TP = 5-7%

SL (Stop Loss) Koruma:
- Düşük volatility: SL = 1.5-2%
- Orta volatility: SL = 2-2.5%
- Yüksek volatility: SL = 2.5-3.5%

⚡ Risk/Reward hedefi: 1.5:1 ile 2:1 arası (agresif ama güvenli)

LEVERAGE KURALLARI:
- Confidence 0.7-1.0: 4-5x leverage
- Confidence 0.6-0.69: 3-4x leverage
- Confidence 0.5-0.59: 2-3x leverage

⚠️ ZORUNLU SKIP DURUMLARI:
- trading_allowed == false
- open_positions_count >= max_open_positions
- trades_opened_today >= max_trades_per_day
- remaining_daily_loss_capacity_usdt <= 0

💡 STRATEJI ÖZETİ:
Bu sistem MARKET MAKER davranışını takip eder. Funding negatifken ve OI artarken, MM'lar likidite toplar ve fiyatı yukarı iter. Bu sinyali erken yakala ve pozisyon aç.

SKIP sebepleri sadece:
- "MM sinyalleri zayıf - funding/OI uyumsuz"
- "Risk limitleri dolu"
- "Toplam puan yetersiz (<50)"
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