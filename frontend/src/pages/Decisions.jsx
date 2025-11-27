import { useEffect, useState } from "react";
import axios from "axios";
import { Brain, TrendingUp, X, Clock, Play } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Decisions = () => {
  const [decisions, setDecisions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedDecision, setSelectedDecision] = useState(null);
  const [manualTradeParams, setManualTradeParams] = useState({
    position_size_usdt: 50,
    leverage: 3,
    target_profit_percent: 4,
    stop_loss_percent: 2
  });
  const [submitting, setSubmitting] = useState(false);
  
  const fetchDecisions = async () => {
    try {
      const response = await axios.get(`${API}/decisions?limit=50`);
      setDecisions(response.data);
    } catch (error) {
      console.error("Error fetching decisions:", error);
      toast.error("Kararlar yüklenirken hata oluştu");
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchDecisions();
    const interval = setInterval(fetchDecisions, 30000); // 30 saniyede bir güncelle
    return () => clearInterval(interval);
  }, []);
  
  const formatDate = (dateString) => {
    if (!dateString) return "-";
    const date = new Date(dateString);
    return date.toLocaleString('tr-TR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };
  
  const openManualTradeModal = (decisionLog) => {
    setSelectedDecision(decisionLog);
    
    // AI'nın önerdiği değerleri default olarak ayarla
    const aiPosition = decisionLog.decision.position || {};
    const aiRisk = decisionLog.decision.risk || {};
    
    setManualTradeParams({
      position_size_usdt: aiPosition.position_size_value || 50,
      leverage: aiPosition.leverage || 3,
      target_profit_percent: aiRisk.target_profit_percent || 4,
      stop_loss_percent: aiRisk.stop_loss_percent || 2
    });
    
    setModalOpen(true);
  };
  
  const handleManualTrade = async () => {
    if (!selectedDecision) return;
    
    setSubmitting(true);
    try {
      const response = await axios.post(`${API}/positions/manual`, {
        symbol: selectedDecision.symbol,
        ...manualTradeParams
      });
      
      toast.success(response.data.message || "Pozisyon başarıyla açıldı!");
      setModalOpen(false);
      fetchDecisions(); // Refresh decisions
    } catch (error) {
      console.error("Error opening manual position:", error);
      toast.error(error.response?.data?.detail || "Pozisyon açılırken hata oluştu");
    } finally {
      setSubmitting(false);
    }
  };
  
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-gray-400">Yükleniyor...</div>
      </div>
    );
  }
  
  return (
    <div className="space-y-4 sm:space-y-6 p-2 sm:p-0" data-testid="decisions-page">
      <div className="flex items-center gap-2 sm:gap-3">
        <Brain className="w-6 h-6 sm:w-8 sm:h-8 text-cyan-400 flex-shrink-0" />
        <div className="min-w-0">
          <h1 className="text-lg sm:text-2xl font-bold text-white truncate">AI Kararları</h1>
          <p className="text-xs sm:text-sm text-gray-400 truncate">Yapay zeka ticaret kararları</p>
        </div>
      </div>
      
      {decisions.length === 0 ? (
        <Card className="bg-black/40 border-white/10 backdrop-blur">
          <CardContent className="p-8 text-center">
            <Brain className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400">Henüz AI kararı bulunmuyor</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {decisions.map((decisionLog, idx) => {
            const decision = decisionLog.decision;
            const isLong = decision.action === "OPEN_LONG";
            
            return (
              <Card
                key={decisionLog.id || idx}
                className="bg-black/40 border-white/10 backdrop-blur hover:border-cyan-500/30 transition-all"
                data-testid={`decision-${idx}`}
              >
                <CardContent className="p-3 sm:p-5">
                  <div className="flex flex-col sm:flex-row items-start gap-3 sm:gap-4">
                    {/* Mobile: Icon + Header Row */}
                    <div className="flex items-center gap-3 w-full sm:w-auto">
                      {/* Icon */}
                      <div className={`w-10 h-10 sm:w-12 sm:h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${
                        isLong
                          ? "bg-emerald-500/20 text-emerald-400"
                          : "bg-gray-500/20 text-gray-400"
                      }`}>
                        {isLong ? <TrendingUp className="w-5 h-5 sm:w-6 sm:h-6" /> : <X className="w-5 h-5 sm:w-6 sm:h-6" />}
                      </div>
                      
                      {/* Mobile: Symbol + Badges */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="text-base sm:text-lg font-bold text-white">{decisionLog.symbol}</h3>
                          <span className={`px-2 sm:px-3 py-0.5 sm:py-1 rounded-full text-xs font-semibold whitespace-nowrap ${
                            isLong
                              ? "bg-emerald-500/20 text-emerald-400"
                              : "bg-gray-500/20 text-gray-400"
                          }`}>
                            {isLong ? "LONG" : "SKIP"}
                          </span>
                          {decisionLog.was_executed && (
                            <span className="px-2 sm:px-3 py-0.5 sm:py-1 rounded-full text-xs font-semibold bg-cyan-500/20 text-cyan-400 whitespace-nowrap">
                              İşlem Açıldı
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    {/* Content */}
                    <div className="flex-1 w-full">
                      <p className="text-xs sm:text-sm text-gray-300 mb-2 sm:mb-3 leading-relaxed">{decision.reason}</p>
                        
                        <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-4 gap-2 sm:gap-4">
                          <div>
                            <p className="text-[10px] sm:text-xs text-gray-500">Güven Skoru</p>
                            <p className="text-sm sm:text-base font-semibold text-white">
                              {(decision.confidence * 100).toFixed(0)}%
                            </p>
                          </div>
                          
                          {decision.position && (
                            <>
                              <div>
                                <p className="text-[10px] sm:text-xs text-gray-500">Kaldıraç</p>
                                <p className="text-sm sm:text-base font-semibold text-cyan-400">
                                  {decision.position.leverage}x
                                </p>
                              </div>
                              <div>
                                <p className="text-[10px] sm:text-xs text-gray-500">Pozisyon</p>
                                <p className="text-sm sm:text-base font-semibold text-white">
                                  ${decision.position.position_size_value}
                                </p>
                              </div>
                            </>
                          )}
                          
                          {decision.risk && (
                            <div>
                              <p className="text-[10px] sm:text-xs text-gray-500">TP / SL</p>
                              <p className="text-sm font-semibold text-white">
                                {decision.risk.target_profit_percent}% / {decision.risk.stop_loss_percent}%
                              </p>
                            </div>
                          )}
                        </div>
                        
                        {/* Timestamp ve Manuel Gir Butonu */}
                        <div className="flex items-center justify-between gap-2 mt-3 pt-3 border-t border-white/10 flex-wrap">
                          <div className="flex items-center gap-2">
                            <Clock className="w-3 h-3 text-gray-500 flex-shrink-0" />
                            <span className="text-[10px] sm:text-xs text-gray-500">
                              {formatDate(decisionLog.created_at)}
                            </span>
                          </div>
                          
                          {/* Manuel Giriş Butonu */}
                          <Button
                            onClick={() => openManualTradeModal(decisionLog)}
                            className="bg-cyan-500 hover:bg-cyan-600 text-white text-xs sm:text-sm h-8 sm:h-9 px-3 sm:px-4"
                            size="sm"
                          >
                            <Play className="w-3 h-3 sm:w-4 sm:h-4 sm:mr-2" />
                            <span className="hidden sm:inline">Manuel Gir</span>
                            <span className="sm:hidden ml-1">Gir</span>
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
      
      {/* Manuel Trade Modal */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="bg-[#0a0e27] border-white/10 text-white sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold text-cyan-400">
              Manuel Pozisyon Aç - {selectedDecision?.symbol}
            </DialogTitle>
            <DialogDescription className="text-gray-400">
              AI önerilerini kullanabilir veya kendi parametrelerinizi ayarlayabilirsiniz
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div>
              <Label className="text-white">Pozisyon Miktarı (USDT)</Label>
              <Input
                type="number"
                value={manualTradeParams.position_size_usdt}
                onChange={(e) => setManualTradeParams({
                  ...manualTradeParams,
                  position_size_usdt: parseFloat(e.target.value)
                })}
                className="bg-black/40 border-white/20 text-white mt-1"
                min="1"
                step="1"
              />
            </div>
            
            <div>
              <Label className="text-white">Kaldıraç (x)</Label>
              <Input
                type="number"
                value={manualTradeParams.leverage}
                onChange={(e) => setManualTradeParams({
                  ...manualTradeParams,
                  leverage: parseInt(e.target.value)
                })}
                className="bg-black/40 border-white/20 text-white mt-1"
                min="1"
                max="20"
                step="1"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-white">Take Profit (%)</Label>
                <Input
                  type="number"
                  value={manualTradeParams.target_profit_percent}
                  onChange={(e) => setManualTradeParams({
                    ...manualTradeParams,
                    target_profit_percent: parseFloat(e.target.value)
                  })}
                  className="bg-black/40 border-white/20 text-white mt-1"
                  min="0.1"
                  step="0.1"
                />
              </div>
              
              <div>
                <Label className="text-white">Stop Loss (%)</Label>
                <Input
                  type="number"
                  value={manualTradeParams.stop_loss_percent}
                  onChange={(e) => setManualTradeParams({
                    ...manualTradeParams,
                    stop_loss_percent: parseFloat(e.target.value)
                  })}
                  className="bg-black/40 border-white/20 text-white mt-1"
                  min="0.1"
                  step="0.1"
                />
              </div>
            </div>
            
            {/* AI Öneri Bilgisi */}
            <div className="p-3 bg-cyan-500/10 border border-cyan-500/30 rounded-lg">
              <p className="text-xs text-cyan-300 font-medium mb-1">
                💡 AI Önerileri
              </p>
              <p className="text-xs text-gray-300">
                Güven: {selectedDecision ? (selectedDecision.decision.confidence * 100).toFixed(0) : 0}% | 
                Risk/Reward: {manualTradeParams.target_profit_percent > 0 && manualTradeParams.stop_loss_percent > 0 
                  ? (manualTradeParams.target_profit_percent / manualTradeParams.stop_loss_percent).toFixed(1)
                  : "0"}:1
              </p>
            </div>
          </div>
          
          <div className="flex gap-3 justify-end">
            <Button
              variant="outline"
              onClick={() => setModalOpen(false)}
              className="border-white/20 text-white hover:bg-white/10"
            >
              İptal
            </Button>
            <Button
              onClick={handleManualTrade}
              disabled={submitting}
              className="bg-emerald-500 hover:bg-emerald-600 text-white"
            >
              {submitting ? "Açılıyor..." : "Pozisyon Aç"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Decisions;