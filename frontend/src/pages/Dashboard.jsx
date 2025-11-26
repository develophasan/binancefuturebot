import { useEffect, useState } from "react";
import axios from "axios";
import { Activity, TrendingUp, DollarSign, AlertCircle, PlayCircle, PauseCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Dashboard = () => {
  const [status, setStatus] = useState(null);
  const [topGainers, setTopGainers] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const fetchData = async () => {
    try {
      const [statusRes, gainersRes] = await Promise.all([
        axios.get(`${API}/bot/status`),
        axios.get(`${API}/market/top-gainers?limit=5`)
      ]);
      
      setStatus(statusRes.data);
      setTopGainers(gainersRes.data);
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
      toast.error("Veri yüklenirken hata oluştu");
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchData();
    // 2 saniyede bir güncelle (gerçek zamanlı)
    const interval = setInterval(() => {
      fetchData();
      console.log('🔄 Dashboard güncelleniyor...', new Date().toLocaleTimeString());
    }, 2000);
    return () => clearInterval(interval);
  }, []);
  
  const handleToggleBot = async () => {
    try {
      const endpoint = status?.is_running ? "stop" : "start";
      await axios.post(`${API}/bot/${endpoint}`);
      toast.success(`Bot ${status?.is_running ? 'durduruldu' : 'başlatıldı'}`);
      fetchData();
    } catch (error) {
      console.error("Error toggling bot:", error);
      toast.error("Bot durumu değiştirilemedi");
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
    <div className="space-y-6" data-testid="dashboard">
      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Bot Status */}
        <Card className="bg-black/40 border-white/10 backdrop-blur">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-400 flex items-center gap-2">
              <Activity className="w-4 h-4" />
              Bot Durumu
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-2xl font-bold ${
                  status?.is_running && status?.is_active
                    ? "text-emerald-400"
                    : "text-gray-500"
                }`}>
                  {status?.is_running && status?.is_active ? "AKTIF" : "DURDURULDU"}
                </p>
              </div>
              <Button
                onClick={handleToggleBot}
                size="sm"
                className={`${
                  status?.is_running
                    ? "bg-red-500 hover:bg-red-600"
                    : "bg-emerald-500 hover:bg-emerald-600"
                }`}
                data-testid="toggle-bot-btn"
              >
                {status?.is_running ? (
                  <PauseCircle className="w-4 h-4" />
                ) : (
                  <PlayCircle className="w-4 h-4" />
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
        
        {/* Open Positions */}
        <Card className="bg-black/40 border-white/10 backdrop-blur">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-400 flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Açık Pozisyonlar
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-cyan-400">
              {status?.open_positions_count || 0}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Bugün açılan: {status?.trades_today || 0}
            </p>
          </CardContent>
        </Card>
        
        {/* Daily PnL */}
        <Card className="bg-black/40 border-white/10 backdrop-blur">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-400 flex items-center gap-2">
              <DollarSign className="w-4 h-4" />
              Günlük PnL
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-3xl font-bold ${
              (status?.daily_pnl_usdt || 0) >= 0
                ? "text-emerald-400"
                : "text-red-400"
            }`}>
              ${(status?.daily_pnl_usdt || 0).toFixed(2)}
            </p>
            <p className="text-xs text-gray-500 mt-1">USDT</p>
          </CardContent>
        </Card>
        
        {/* Total Equity */}
        <Card className="bg-black/40 border-white/10 backdrop-blur">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-400 flex items-center gap-2">
              <DollarSign className="w-4 h-4" />
              Toplam Bakiye
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-white">
              ${(status?.total_equity_usdt || 0).toFixed(2)}
            </p>
            <p className="text-xs text-gray-500 mt-1">USDT</p>
          </CardContent>
        </Card>
      </div>
      
      {/* Top Gainers */}
      <Card className="bg-black/40 border-white/10 backdrop-blur">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-white flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-emerald-400" />
            24 Saatlik En Çok Yükselen Coinler
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {topGainers.length === 0 ? (
              <div className="text-gray-400 text-center py-4">
                Veri yükleniyor...
              </div>
            ) : (
              topGainers.map((gainer, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-all"
                  data-testid={`top-gainer-${idx}`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-400 to-cyan-500 flex items-center justify-center text-white text-xs font-bold">
                      {idx + 1}
                    </div>
                    <div>
                      <p className="font-semibold text-white">{gainer.symbol}</p>
                      <p className="text-xs text-gray-400">
                        ${gainer.price?.toFixed(2) || '0.00'}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-emerald-400 font-bold">
                      +{gainer.price_change_percent?.toFixed(2)}%
                    </p>
                    <p className="text-xs text-gray-500">
                      Vol: ${(gainer.volume_24h / 1000000).toFixed(1)}M
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
      
      {/* Info Alert */}
      <Card className="bg-cyan-500/10 border-cyan-500/30 backdrop-blur">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-cyan-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-cyan-100 font-medium">
                Bot Testnet modunda çalışıyor
              </p>
              <p className="text-xs text-cyan-200/70 mt-1">
                Tüm işlemler Binance Futures Testnet üzerinde gerçekleştirilmektedir. Gerçek para riski yoktur.
                AI her 5 dakikada bir piyasayı analiz eder ve uygun fırsatlarda long pozisyon açar.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Dashboard;