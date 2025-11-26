import { useEffect, useState } from "react";
import axios from "axios";
import { TrendingUp, Clock, DollarSign, Target, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { formatPrice, formatPnL, formatPercent } from "@/utils/formatPrice";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Positions = () => {
  const [openPositions, setOpenPositions] = useState([]);
  const [closedPositions, setClosedPositions] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const fetchPositions = async () => {
    try {
      const [openRes, closedRes] = await Promise.all([
        axios.get(`${API}/positions?status=OPEN&_t=${Date.now()}`), // Cache buster
        axios.get(`${API}/positions?status=CLOSED`)
      ]);
      
      console.log('💰 PnL Güncellemesi:', openRes.data.map(p => 
        `${p.symbol}: $${p.unrealized_pnl_usdt?.toFixed(2) || '0.00'}`
      ));
      
      setOpenPositions(openRes.data);
      setClosedPositions(closedRes.data);
    } catch (error) {
      console.error("Error fetching positions:", error);
      // toast.error("Pozisyonlar yüklenirken hata oluştu"); // Çok sık toast çıkmaması için kaldırdım
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchPositions();
    // 2 saniyede bir güncelle (gerçek zamanlı)
    const interval = setInterval(() => {
      fetchPositions();
      console.log('📊 Pozisyonlar güncelleniyor...', new Date().toLocaleTimeString());
    }, 2000);
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
      minute: '2-digit'
    });
  };
  
  const PositionCard = ({ position, isOpen }) => {
    // Use unrealized_pnl for open positions, realized_pnl for closed
    const pnl = isOpen 
      ? (position.unrealized_pnl_usdt || 0)
      : (position.realized_pnl_usdt || 0);
    
    const pnlPercent = isOpen
      ? (position.price_change_percent || 0)
      : (position.realized_pnl_usdt ? (position.realized_pnl_usdt / position.position_size_usdt) * 100 : 0);
    
    const currentPrice = isOpen && position.current_price
      ? position.current_price
      : position.exit_price;
    
    return (
      <Card className="bg-black/40 border-white/10 backdrop-blur hover:border-cyan-500/30 transition-all" data-testid={`position-${position.id}`}>
        <CardContent className="p-4">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h3 className="text-lg font-bold text-white">{position.symbol}</h3>
              <div className="flex items-center gap-2 mt-1">
                <span className="px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/20 text-emerald-400">
                  LONG
                </span>
                <span className="px-2 py-0.5 rounded text-xs font-medium bg-cyan-500/20 text-cyan-400">
                  {position.leverage}x
                </span>
                {isOpen && (
                  <span className="px-2 py-0.5 rounded text-xs font-medium bg-orange-500/20 text-orange-400 animate-pulse">
                    LIVE
                  </span>
                )}
              </div>
            </div>
            <div className="text-right">
              <p className={`text-xl font-bold ${
                pnl >= 0 ? "text-emerald-400" : "text-red-400"
              }`}>
                {pnl >= 0 ? '+' : ''}${formatPnL(pnl)}
              </p>
              <p className={`text-xs ${
                pnlPercent >= 0 ? "text-emerald-400" : "text-red-400"
              }`}>
                {pnlPercent >= 0 ? '+' : ''}{formatPercent(pnlPercent)}%
              </p>
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <p className="text-xs text-gray-400 flex items-center gap-1">
                <DollarSign className="w-3 h-3" />
                Giriş Fiyatı
              </p>
              <p className="text-sm font-semibold text-white">
                ${position.entry_price?.toFixed(2)}
              </p>
            </div>
            {isOpen && currentPrice ? (
              <div>
                <p className="text-xs text-gray-400 flex items-center gap-1">
                  <DollarSign className="w-3 h-3" />
                  Anlık Fiyat
                </p>
                <p className={`text-sm font-semibold ${
                  currentPrice >= position.entry_price ? "text-emerald-400" : "text-red-400"
                }`}>
                  ${currentPrice?.toFixed(2)}
                </p>
              </div>
            ) : position.exit_price && (
              <div>
                <p className="text-xs text-gray-400 flex items-center gap-1">
                  <DollarSign className="w-3 h-3" />
                  Çıkış Fiyatı
                </p>
                <p className="text-sm font-semibold text-white">
                  ${position.exit_price?.toFixed(2)}
                </p>
              </div>
            )}
            <div>
              <p className="text-xs text-gray-400 flex items-center gap-1">
                <Target className="w-3 h-3" />
                Take Profit
              </p>
              <p className="text-sm font-semibold text-emerald-400">
                ${position.take_profit_price?.toFixed(2)}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                Stop Loss
              </p>
              <p className="text-sm font-semibold text-red-400">
                ${position.stop_loss_price?.toFixed(2)}
              </p>
            </div>
          </div>
          
          <div className="flex items-center justify-between pt-3 border-t border-white/10">
            <div className="flex items-center gap-1 text-xs text-gray-500">
              <Clock className="w-3 h-3" />
              {formatDate(position.opened_at)}
            </div>
            <div className="text-xs text-gray-400">
              Miktar: {position.quantity?.toFixed(4)}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  };
  
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-gray-400">Yükleniyor...</div>
      </div>
    );
  }
  
  return (
    <div className="space-y-6" data-testid="positions-page">
      <div className="flex items-center gap-3">
        <TrendingUp className="w-8 h-8 text-cyan-400" />
        <div>
          <h1 className="text-2xl font-bold text-white">Pozisyonlar</h1>
          <p className="text-sm text-gray-400">Açık ve kapalı pozisyonlarınızı görüntüleyin</p>
        </div>
      </div>
      
      <Tabs defaultValue="open" className="w-full">
        <TabsList className="bg-black/40 border border-white/10">
          <TabsTrigger value="open" data-testid="tab-open-positions">
            Açık Pozisyonlar ({openPositions.length})
          </TabsTrigger>
          <TabsTrigger value="closed" data-testid="tab-closed-positions">
            Kapalı Pozisyonlar ({closedPositions.length})
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="open" className="mt-6">
          {openPositions.length === 0 ? (
            <Card className="bg-black/40 border-white/10 backdrop-blur">
              <CardContent className="p-8 text-center">
                <TrendingUp className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-400">Henüz açık pozisyon bulunmuyor</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {openPositions.map((position) => (
                <PositionCard key={position.id} position={position} isOpen={true} />
              ))}
            </div>
          )}
        </TabsContent>
        
        <TabsContent value="closed" className="mt-6">
          {closedPositions.length === 0 ? (
            <Card className="bg-black/40 border-white/10 backdrop-blur">
              <CardContent className="p-8 text-center">
                <TrendingUp className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-400">Henüz kapalı pozisyon bulunmuyor</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {closedPositions.map((position) => (
                <PositionCard key={position.id} position={position} isOpen={false} />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Positions;