import { useEffect, useState } from "react";
import axios from "axios";
import { History as HistoryIcon, TrendingUp, TrendingDown, Clock, DollarSign } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { formatPrice } from "@/utils/formatPrice";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const History = () => {
  const [closedPositions, setClosedPositions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalTrades: 0,
    winRate: 0,
    totalPnL: 0,
    avgPnL: 0
  });
  
  const fetchClosedPositions = async () => {
    try {
      const response = await axios.get(`${API}/positions?status=CLOSED`);
      const positions = response.data;
      setClosedPositions(positions);
      
      // Calculate stats
      const totalTrades = positions.length;
      const winners = positions.filter(p => (p.realized_pnl_usdt || 0) > 0).length;
      const totalPnL = positions.reduce((sum, p) => sum + (p.realized_pnl_usdt || 0), 0);
      
      setStats({
        totalTrades,
        winRate: totalTrades > 0 ? (winners / totalTrades) * 100 : 0,
        totalPnL,
        avgPnL: totalTrades > 0 ? totalPnL / totalTrades : 0
      });
    } catch (error) {
      console.error("Error fetching closed positions:", error);
      toast.error("Geçmiş yüklenirken hata oluştu");
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchClosedPositions();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchClosedPositions, 30000);
    return () => clearInterval(interval);
  }, []);
  
  const formatDate = (dateString) => {
    if (!dateString) return "-";
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('tr-TR', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  };
  
  const calculateDuration = (openedAt, closedAt) => {
    if (!openedAt || !closedAt) return "-";
    const start = new Date(openedAt);
    const end = new Date(closedAt);
    const diffMs = end - start;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 60) return `${diffMins}dk`;
    const hours = Math.floor(diffMins / 60);
    const mins = diffMins % 60;
    return `${hours}s ${mins}dk`;
  };
  
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-gray-400">Yükleniyor...</div>
      </div>
    );
  }
  
  return (
    <div className="space-y-6" data-testid="history-page">
      <div className="flex items-center gap-3">
        <HistoryIcon className="w-8 h-8 text-cyan-400" />
        <div>
          <h1 className="text-2xl font-bold text-white">İşlem Geçmişi</h1>
          <p className="text-sm text-gray-400">Kapatılmış pozisyonlar ve performans</p>
        </div>
      </div>
      
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-black/40 border-white/10 backdrop-blur">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-400">Toplam İşlem</p>
                <p className="text-2xl font-bold text-white mt-1">{stats.totalTrades}</p>
              </div>
              <TrendingUp className="w-8 h-8 text-cyan-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-black/40 border-white/10 backdrop-blur">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-400">Kazanma Oranı</p>
                <p className={`text-2xl font-bold mt-1 ${stats.winRate >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {stats.winRate.toFixed(1)}%
                </p>
              </div>
              <TrendingUp className="w-8 h-8 text-emerald-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-black/40 border-white/10 backdrop-blur">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-400">Toplam PnL</p>
                <p className={`text-2xl font-bold mt-1 ${stats.totalPnL >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  ${stats.totalPnL.toFixed(2)}
                </p>
              </div>
              <DollarSign className="w-8 h-8 text-yellow-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-black/40 border-white/10 backdrop-blur">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-400">Ort. PnL</p>
                <p className={`text-2xl font-bold mt-1 ${stats.avgPnL >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  ${stats.avgPnL.toFixed(2)}
                </p>
              </div>
              <TrendingUp className="w-8 h-8 text-blue-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Closed Positions Table */}
      <Card className="bg-black/40 border-white/10 backdrop-blur">
        <CardHeader>
          <CardTitle className="text-white">Kapatılmış Pozisyonlar</CardTitle>
        </CardHeader>
        <CardContent>
          {closedPositions.length === 0 ? (
            <div className="text-center py-12">
              <HistoryIcon className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">Henüz kapatılmış pozisyon yok</p>
              <p className="text-xs text-gray-500 mt-2">İşlemler kapatıldıkça burada görünecek</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full" data-testid="history-table">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-400">Sembol</th>
                    <th className="text-right py-3 px-4 text-xs font-medium text-gray-400">Giriş</th>
                    <th className="text-right py-3 px-4 text-xs font-medium text-gray-400">Çıkış</th>
                    <th className="text-right py-3 px-4 text-xs font-medium text-gray-400">Miktar</th>
                    <th className="text-center py-3 px-4 text-xs font-medium text-gray-400">Kaldıraç</th>
                    <th className="text-right py-3 px-4 text-xs font-medium text-gray-400">PnL</th>
                    <th className="text-center py-3 px-4 text-xs font-medium text-gray-400">Süre</th>
                    <th className="text-right py-3 px-4 text-xs font-medium text-gray-400">Kapanış</th>
                  </tr>
                </thead>
                <tbody>
                  {closedPositions.map((position) => {
                    const pnl = position.realized_pnl_usdt || 0;
                    const isProfit = pnl > 0;
                    
                    return (
                      <tr 
                        key={position.id} 
                        className="border-b border-white/5 hover:bg-white/5 transition-colors"
                        data-testid={`history-row-${position.symbol}`}
                      >
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <span className="text-white font-medium">{position.symbol}</span>
                            <Badge className="bg-cyan-500/20 text-cyan-300 text-xs">
                              LONG
                            </Badge>
                          </div>
                        </td>
                        <td className="text-right py-3 px-4 text-sm text-gray-300">
                          ${formatPrice(position.entry_price)}
                        </td>
                        <td className="text-right py-3 px-4 text-sm text-gray-300">
                          ${formatPrice(position.exit_price || 0)}
                        </td>
                        <td className="text-right py-3 px-4 text-sm text-gray-300">
                          {position.quantity}
                        </td>
                        <td className="text-center py-3 px-4">
                          <Badge className="bg-purple-500/20 text-purple-300 text-xs">
                            {position.leverage}x
                          </Badge>
                        </td>
                        <td className="text-right py-3 px-4">
                          <div className="flex items-center justify-end gap-1">
                            {isProfit ? (
                              <TrendingUp className="w-3 h-3 text-emerald-400" />
                            ) : (
                              <TrendingDown className="w-3 h-3 text-red-400" />
                            )}
                            <span className={`font-medium ${isProfit ? 'text-emerald-400' : 'text-red-400'}`}>
                              ${pnl.toFixed(2)}
                            </span>
                          </div>
                        </td>
                        <td className="text-center py-3 px-4">
                          <div className="flex items-center justify-center gap-1 text-xs text-gray-400">
                            <Clock className="w-3 h-3" />
                            {calculateDuration(position.opened_at, position.closed_at)}
                          </div>
                        </td>
                        <td className="text-right py-3 px-4 text-xs text-gray-400">
                          {formatDate(position.closed_at)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default History;
