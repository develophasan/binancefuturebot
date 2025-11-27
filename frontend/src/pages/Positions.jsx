import { useEffect, useState } from "react";
import axios from "axios";
import { TrendingUp, Clock, DollarSign, Target, AlertTriangle, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { formatPrice, formatPnL, formatPercent } from "@/utils/formatPrice";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Positions = () => {
  const [openPositions, setOpenPositions] = useState([]);
  const [closedPositions, setClosedPositions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [closeAllDialogOpen, setCloseAllDialogOpen] = useState(false);
  const [closingAll, setClosingAll] = useState(false);
  const [closeSingleDialogOpen, setCloseSingleDialogOpen] = useState(false);
  const [selectedPosition, setSelectedPosition] = useState(null);
  const [closingSingle, setClosingSingle] = useState(false);
  
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
  
  const handleCloseAllPositions = async () => {
    setClosingAll(true);
    try {
      const response = await axios.post(`${API}/positions/close-all`);
      toast.success(response.data.message || "Tüm pozisyonlar kapatıldı!");
      
      // Refresh positions
      await fetchPositions();
      setCloseAllDialogOpen(false);
    } catch (error) {
      console.error("Error closing all positions:", error);
      toast.error(error.response?.data?.detail || "Pozisyonlar kapatılırken hata oluştu");
    } finally {
      setClosingAll(false);
    }
  };
  
  const handleCloseSinglePosition = async () => {
    if (!selectedPosition) return;
    
    setClosingSingle(true);
    try {
      // Show loading toast
      const loadingToast = toast.loading("Pozisyon kapatılıyor...", {
        description: "Market fiyatından satış emri yerleştiriliyor"
      });
      
      const response = await axios.post(`${API}/positions/${selectedPosition.id}/close`);
      
      // Dismiss loading toast
      toast.dismiss(loadingToast);
      
      // Show detailed success message
      if (response.data.details) {
        const details = response.data.details;
        const isProfitable = details.realized_pnl >= 0;
        
        toast.success("Pozisyon Kapatıldı!", {
          description: (
            <div className="space-y-1 text-xs mt-2">
              <div className="flex justify-between">
                <span>Symbol:</span>
                <span className="font-semibold">{details.symbol}</span>
              </div>
              <div className="flex justify-between">
                <span>Giriş:</span>
                <span>${formatPrice(details.entry_price)}</span>
              </div>
              <div className="flex justify-between">
                <span>Çıkış:</span>
                <span>${formatPrice(details.exit_price)}</span>
              </div>
              <div className="flex justify-between border-t border-white/10 pt-1">
                <span>PnL:</span>
                <span className={isProfitable ? 'text-emerald-400 font-semibold' : 'text-red-400 font-semibold'}>
                  ${details.realized_pnl.toFixed(2)} ({details.pnl_percent.toFixed(2)}%)
                </span>
              </div>
            </div>
          ),
          duration: 6000
        });
      } else {
        toast.success(response.data.message || "Pozisyon kapatıldı!");
      }
      
      // Refresh positions
      await fetchPositions();
      setCloseSingleDialogOpen(false);
      setSelectedPosition(null);
    } catch (error) {
      console.error("Error closing position:", error);
      toast.error(error.response?.data?.detail || "Pozisyon kapatılırken hata oluştu");
    } finally {
      setClosingSingle(false);
    }
  };
  
  const openCloseSingleDialog = (position) => {
    setSelectedPosition(position);
    setCloseSingleDialogOpen(true);
  };
  
  useEffect(() => {
    fetchPositions();
    // Her 500ms'de bir güncelle (WebSocket destekli ultra hızlı)
    const interval = setInterval(() => {
      fetchPositions();
    }, 500);
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
                ${formatPrice(position.entry_price)}
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
                  ${formatPrice(currentPrice)}
                </p>
              </div>
            ) : position.exit_price && (
              <div>
                <p className="text-xs text-gray-400 flex items-center gap-1">
                  <DollarSign className="w-3 h-3" />
                  Çıkış Fiyatı
                </p>
                <p className="text-sm font-semibold text-white">
                  ${formatPrice(position.exit_price)}
                </p>
              </div>
            )}
            <div>
              <p className="text-xs text-gray-400 flex items-center gap-1">
                <Target className="w-3 h-3" />
                Take Profit
              </p>
              <p className="text-sm font-semibold text-emerald-400">
                ${formatPrice(position.take_profit_price)}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                Stop Loss
              </p>
              <p className="text-sm font-semibold text-red-400">
                ${formatPrice(position.stop_loss_price)}
              </p>
            </div>
          </div>
          
          <div className="flex items-center justify-between pt-3 border-t border-white/10">
            <div className="flex items-center gap-1 text-xs text-gray-500">
              <Clock className="w-3 h-3" />
              {formatDate(position.opened_at)}
            </div>
            <div className="text-xs text-gray-400">
              Miktar: {formatPrice(position.quantity)}
            </div>
          </div>
          
          {/* Kapat butonu - sadece açık pozisyonlar için */}
          {isOpen && (
            <div className="pt-3 border-t border-white/10 mt-3">
              <Button
                onClick={() => openCloseSingleDialog(position)}
                variant="outline"
                size="sm"
                className="w-full border-red-500/50 text-red-400 hover:bg-red-500/10 hover:text-red-300"
              >
                <XCircle className="w-4 h-4 mr-2" />
                Pozisyonu Kapat
              </Button>
            </div>
          )}
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
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <TrendingUp className="w-8 h-8 text-cyan-400" />
          <div>
            <h1 className="text-2xl font-bold text-white">Pozisyonlar</h1>
            <p className="text-sm text-gray-400">Açık ve kapalı pozisyonlarınızı görüntüleyin</p>
          </div>
        </div>
        
        {/* Tümünü Kapat Butonu */}
        {openPositions.length > 0 && (
          <Button
            onClick={() => setCloseAllDialogOpen(true)}
            variant="destructive"
            className="bg-red-500 hover:bg-red-600 text-white"
          >
            <XCircle className="w-4 h-4 mr-2" />
            Tümünü Kapat ({openPositions.length})
          </Button>
        )}
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
      
      {/* Close All Confirmation Dialog */}
      <AlertDialog open={closeAllDialogOpen} onOpenChange={setCloseAllDialogOpen}>
        <AlertDialogContent className="bg-[#0a0e27] border-white/10">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-xl font-bold text-red-400 flex items-center gap-2">
              <XCircle className="w-6 h-6" />
              Tüm Pozisyonları Kapat?
            </AlertDialogTitle>
            <AlertDialogDescription className="text-gray-300">
              <span className="text-white font-semibold">{openPositions.length} adet</span> açık pozisyon market fiyatından kapatılacak. 
              Bu işlem geri alınamaz!
              <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                <p className="text-sm text-red-300">
                  ⚠️ TP/SL orderları iptal edilecek ve pozisyonlar mevcut fiyattan kapatılacak.
                </p>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel 
              className="border-white/20 text-white hover:bg-white/10"
              disabled={closingAll}
            >
              İptal
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleCloseAllPositions}
              disabled={closingAll}
              className="bg-red-500 hover:bg-red-600 text-white"
            >
              {closingAll ? "Kapatılıyor..." : "Evet, Tümünü Kapat"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      
      {/* Close Single Position Dialog */}
      <AlertDialog open={closeSingleDialogOpen} onOpenChange={setCloseSingleDialogOpen}>
        <AlertDialogContent className="bg-[#0a0e27] border-white/10">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-xl font-bold text-orange-400 flex items-center gap-2">
              <XCircle className="w-6 h-6" />
              Pozisyonu Kapat?
            </AlertDialogTitle>
            <AlertDialogDescription className="text-gray-300">
              {selectedPosition && (
                <>
                  <div className="mb-3">
                    <span className="text-white font-semibold text-lg">{selectedPosition.symbol}</span> pozisyonu market fiyatından kapatılacak.
                  </div>
                  
                  <div className="space-y-2 text-sm bg-black/40 p-3 rounded-lg">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Giriş Fiyatı:</span>
                      <span className="text-white">${formatPrice(selectedPosition.entry_price)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Güncel PnL:</span>
                      <span className={selectedPosition.unrealized_pnl_usdt >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                        ${selectedPosition.unrealized_pnl_usdt?.toFixed(2)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Miktar:</span>
                      <span className="text-white">{formatPrice(selectedPosition.quantity)}</span>
                    </div>
                  </div>
                  
                  <div className="mt-3 p-2 bg-orange-500/10 border border-orange-500/30 rounded-lg">
                    <p className="text-xs text-orange-300">
                      ⚠️ TP/SL orderları iptal edilecek ve pozisyon mevcut fiyattan kapatılacak.
                    </p>
                  </div>
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel 
              className="border-white/20 text-white hover:bg-white/10"
              disabled={closingSingle}
            >
              İptal
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleCloseSinglePosition}
              disabled={closingSingle}
              className="bg-orange-500 hover:bg-orange-600 text-white"
            >
              {closingSingle ? "Kapatılıyor..." : "Evet, Kapat"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default Positions;