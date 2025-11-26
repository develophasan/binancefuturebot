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
    <div className="space-y-6" data-testid="decisions-page">
      <div className="flex items-center gap-3">
        <Brain className="w-8 h-8 text-cyan-400" />
        <div>
          <h1 className="text-2xl font-bold text-white">AI Kararları</h1>
          <p className="text-sm text-gray-400">Yapay zeka tarafından verilen ticaret kararları</p>
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
                <CardContent className="p-5">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4 flex-1">
                      {/* Icon */}
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${
                        isLong
                          ? "bg-emerald-500/20 text-emerald-400"
                          : "bg-gray-500/20 text-gray-400"
                      }`}>
                        {isLong ? <TrendingUp className="w-6 h-6" /> : <X className="w-6 h-6" />}
                      </div>
                      
                      {/* Content */}
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="text-lg font-bold text-white">{decisionLog.symbol}</h3>
                          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                            isLong
                              ? "bg-emerald-500/20 text-emerald-400"
                              : "bg-gray-500/20 text-gray-400"
                          }`}>
                            {isLong ? "LONG" : "SKIP"}
                          </span>
                          {decisionLog.was_executed && (
                            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-cyan-500/20 text-cyan-400">
                              İşlem Açıldı
                            </span>
                          )}
                        </div>
                        
                        <p className="text-sm text-gray-300 mb-3">{decision.reason}</p>
                        
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div>
                            <p className="text-xs text-gray-500">Güven Skoru</p>
                            <p className="text-sm font-semibold text-white">
                              {(decision.confidence * 100).toFixed(0)}%
                            </p>
                          </div>
                          
                          {decision.position && (
                            <>
                              <div>
                                <p className="text-xs text-gray-500">Kaldıraç</p>
                                <p className="text-sm font-semibold text-cyan-400">
                                  {decision.position.leverage}x
                                </p>
                              </div>
                              <div>
                                <p className="text-xs text-gray-500">Pozisyon</p>
                                <p className="text-sm font-semibold text-white">
                                  ${decision.position.position_size_value}
                                </p>
                              </div>
                            </>
                          )}
                          
                          {decision.risk && (
                            <div>
                              <p className="text-xs text-gray-500">TP / SL</p>
                              <p className="text-sm font-semibold text-white">
                                {decision.risk.target_profit_percent}% / {decision.risk.stop_loss_percent}%
                              </p>
                            </div>
                          )}
                        </div>
                        
                        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-white/10">
                          <Clock className="w-3 h-3 text-gray-500" />
                          <span className="text-xs text-gray-500">
                            {formatDate(decisionLog.created_at)}
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    {/* Manuel Giriş Butonu */}
                    <div className="ml-4">
                      <Button
                        onClick={() => openManualTradeModal(decisionLog)}
                        className="bg-cyan-500 hover:bg-cyan-600 text-white"
                        size="sm"
                      >
                        <Play className="w-4 h-4 mr-2" />
                        Manuel Gir
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Decisions;