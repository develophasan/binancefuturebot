import { useState, useEffect } from "react";
import axios from "axios";
import { Search, TrendingUp, TrendingDown, Brain, Play, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Analyze = () => {
  const [symbols, setSymbols] = useState([]);
  const [filteredSymbols, setFilteredSymbols] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSymbols();
  }, []);

  useEffect(() => {
    if (searchQuery) {
      const filtered = symbols.filter(s => 
        s.toLowerCase().includes(searchQuery.toLowerCase())
      );
      setFilteredSymbols(filtered);
    } else {
      setFilteredSymbols(symbols.slice(0, 50)); // İlk 50 coin
    }
  }, [searchQuery, symbols]);

  const fetchSymbols = async () => {
    try {
      const response = await axios.get(`${API}/market/all-symbols`);
      setSymbols(response.data);
      setFilteredSymbols(response.data.slice(0, 50));
    } catch (error) {
      console.error("Error fetching symbols:", error);
      toast.error("Coin listesi yüklenemedi");
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async (symbol) => {
    setAnalyzing(true);
    setAnalysis(null);
    
    try {
      toast.loading(`${symbol} analiz ediliyor...`, { id: "analyze" });
      
      const response = await axios.get(`${API}/market/analyze-symbol`, {
        params: { symbol }
      });
      
      setAnalysis(response.data);
      toast.success(`${symbol} analizi tamamlandı!`, { id: "analyze" });
      
    } catch (error) {
      console.error("Error analyzing:", error);
      toast.error(error.response?.data?.detail || "Analiz başarısız", { id: "analyze" });
    } finally {
      setAnalyzing(false);
    }
  };

  const openManualTrade = (symbol, decision) => {
    // Navigate to decisions page or open modal
    toast.info(`${symbol} için manuel işlem özelliği yakında!`);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
      </div>
    );
  }

  const decision = analysis?.decision;
  const isLong = decision?.action === "OPEN_LONG";

  return (
    <div className="space-y-4 sm:space-y-6 p-2 sm:p-0">
      {/* Header */}
      <div className="flex items-center gap-2 sm:gap-3">
        <Search className="w-6 h-6 sm:w-8 sm:h-8 text-cyan-400 flex-shrink-0" />
        <div className="min-w-0">
          <h1 className="text-lg sm:text-2xl font-bold text-white">Coin Analizi</h1>
          <p className="text-xs sm:text-sm text-gray-400 truncate">İstediğiniz coini AI ile analiz edin</p>
        </div>
      </div>

      {/* Search */}
      <Card className="bg-black/40 border-white/10 backdrop-blur">
        <CardHeader className="p-4 sm:p-6">
          <CardTitle className="text-base sm:text-lg text-white">Coin Seçin</CardTitle>
        </CardHeader>
        <CardContent className="p-3 sm:p-6 space-y-4">
          <Input
            type="text"
            placeholder="Coin ara (örn: BTC, ETH, SOL...)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-black/40 border-white/20 text-white text-sm sm:text-base"
          />

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
            {filteredSymbols.map((symbol) => (
              <Button
                key={symbol}
                onClick={() => handleAnalyze(symbol)}
                disabled={analyzing}
                variant="outline"
                className="bg-black/40 border-cyan-500/30 text-white hover:bg-cyan-500/20 hover:border-cyan-500 text-xs sm:text-sm h-9 sm:h-10"
              >
                {symbol.replace("USDT", "")}
              </Button>
            ))}
          </div>

          {filteredSymbols.length === 0 && (
            <p className="text-center text-gray-400 text-sm py-4">Coin bulunamadı</p>
          )}
        </CardContent>
      </Card>

      {/* Analysis Result */}
      {analyzing && (
        <Card className="bg-black/40 border-white/10 backdrop-blur">
          <CardContent className="p-8 text-center">
            <Loader2 className="w-12 h-12 text-cyan-400 animate-spin mx-auto mb-4" />
            <p className="text-white">AI analiz yapıyor...</p>
          </CardContent>
        </Card>
      )}

      {analysis && !analyzing && (
        <Card className="bg-black/40 border-white/10 backdrop-blur">
          <CardHeader className="p-4 sm:p-6">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <CardTitle className="text-lg sm:text-xl text-white flex items-center gap-2">
                <Brain className="w-5 h-5 sm:w-6 sm:h-6 text-cyan-400" />
                {analysis.symbol} Analiz Sonucu
              </CardTitle>
              <Badge className={`${
                isLong ? 'bg-emerald-500/20 text-emerald-400' : 'bg-gray-500/20 text-gray-400'
              }`}>
                {isLong ? "LONG ÖNERİSİ" : "SKIP"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="p-3 sm:p-6 space-y-4">
            {/* Current Price & Confidence */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs sm:text-sm text-gray-400">Güncel Fiyat</p>
                <p className="text-lg sm:text-2xl font-bold text-white">
                  ${analysis.current_price.toFixed(6)}
                </p>
              </div>
              <div>
                <p className="text-xs sm:text-sm text-gray-400">AI Güven Skoru</p>
                <p className={`text-lg sm:text-2xl font-bold ${
                  decision.confidence >= 0.7 ? 'text-emerald-400' : 
                  decision.confidence >= 0.5 ? 'text-yellow-400' : 'text-gray-400'
                }`}>
                  {(decision.confidence * 100).toFixed(0)}%
                </p>
              </div>
            </div>

            {/* AI Reasoning */}
            <div className="bg-black/40 p-3 sm:p-4 rounded-lg">
              <p className="text-xs sm:text-sm text-gray-400 mb-2">AI Açıklaması:</p>
              <p className="text-sm sm:text-base text-white">{decision.reason}</p>
            </div>

            {/* Indicators */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 sm:gap-4">
              <div>
                <p className="text-[10px] sm:text-xs text-gray-400">RSI</p>
                <p className="text-sm sm:text-base font-semibold text-white">
                  {analysis.indicators.rsi.toFixed(1)}
                </p>
              </div>
              <div>
                <p className="text-[10px] sm:text-xs text-gray-400">EMA Trend</p>
                <p className={`text-sm sm:text-base font-semibold ${
                  analysis.indicators.ema_trend === 'UP' ? 'text-emerald-400' : 
                  analysis.indicators.ema_trend === 'DOWN' ? 'text-red-400' : 'text-gray-400'
                }`}>
                  {analysis.indicators.ema_trend}
                </p>
              </div>
              <div>
                <p className="text-[10px] sm:text-xs text-gray-400">Volume Ratio</p>
                <p className="text-sm sm:text-base font-semibold text-white">
                  {analysis.indicators.volume_ma_ratio.toFixed(2)}x
                </p>
              </div>
              <div>
                <p className="text-[10px] sm:text-xs text-gray-400">Funding Rate</p>
                <p className={`text-sm sm:text-base font-semibold ${
                  analysis.indicators.funding_rate < 0 ? 'text-emerald-400' : 'text-red-400'
                }`}>
                  {(analysis.indicators.funding_rate * 100).toFixed(4)}%
                </p>
              </div>
              <div>
                <p className="text-[10px] sm:text-xs text-gray-400">OI Change 24h</p>
                <p className={`text-sm sm:text-base font-semibold ${
                  analysis.indicators.oi_change > 0 ? 'text-emerald-400' : 'text-red-400'
                }`}>
                  {analysis.indicators.oi_change > 0 ? '+' : ''}{analysis.indicators.oi_change.toFixed(2)}%
                </p>
              </div>
            </div>

            {/* Position Details (if LONG) */}
            {isLong && decision.position && (
              <div className="bg-emerald-500/10 border border-emerald-500/30 p-3 sm:p-4 rounded-lg">
                <p className="text-xs sm:text-sm text-emerald-400 font-semibold mb-3">Önerilen Pozisyon Detayları:</p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div>
                    <p className="text-[10px] sm:text-xs text-gray-400">Pozisyon</p>
                    <p className="text-sm sm:text-base font-semibold text-white">
                      ${decision.position.position_size_value}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] sm:text-xs text-gray-400">Kaldıraç</p>
                    <p className="text-sm sm:text-base font-semibold text-cyan-400">
                      {decision.position.leverage}x
                    </p>
                  </div>
                  {decision.risk && (
                    <>
                      <div>
                        <p className="text-[10px] sm:text-xs text-gray-400">Take Profit</p>
                        <p className="text-sm sm:text-base font-semibold text-emerald-400">
                          {decision.risk.target_profit_percent}%
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] sm:text-xs text-gray-400">Stop Loss</p>
                        <p className="text-sm sm:text-base font-semibold text-red-400">
                          {decision.risk.stop_loss_percent}%
                        </p>
                      </div>
                    </>
                  )}
                </div>
              </div>
            )}

            {/* Action Button */}
            {isLong && (
              <Button
                onClick={() => openManualTrade(analysis.symbol, decision)}
                className="w-full bg-emerald-500 hover:bg-emerald-600 text-white h-10 sm:h-12 text-sm sm:text-base"
              >
                <Play className="w-4 h-4 sm:w-5 sm:h-5 mr-2" />
                Manuel Pozisyon Aç
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Analyze;
