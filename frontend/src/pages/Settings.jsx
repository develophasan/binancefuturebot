import { useEffect, useState } from "react";
import axios from "axios";
import { Settings as SettingsIcon, Save, Info } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Settings = () => {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  const fetchSettings = async () => {
    try {
      const response = await axios.get(`${API}/settings`);
      setSettings(response.data);
    } catch (error) {
      console.error("Error fetching settings:", error);
      toast.error("Ayarlar yüklenirken hata oluştu");
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchSettings();
  }, []);
  
  const handleSave = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/settings`, settings);
      toast.success("Ayarlar başarıyla kaydedildi");
    } catch (error) {
      console.error("Error saving settings:", error);
      toast.error("Ayarlar kaydedilemedi");
    } finally {
      setSaving(false);
    }
  };
  
  const handleChange = (field, value) => {
    setSettings(prev => ({ ...prev, [field]: value }));
  };
  
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-gray-400">Yükleniyor...</div>
      </div>
    );
  }
  
  if (!settings) return null;
  
  return (
    <div className="space-y-6" data-testid="settings-page">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <SettingsIcon className="w-8 h-8 text-cyan-400" />
          <div>
            <h1 className="text-2xl font-bold text-white">Ayarlar</h1>
            <p className="text-sm text-gray-400">Bot parametrelerini yapılandırın</p>
          </div>
        </div>
        
        <Button
          onClick={handleSave}
          disabled={saving}
          className="bg-cyan-500 hover:bg-cyan-600"
          data-testid="save-settings-btn"
        >
          <Save className="w-4 h-4 mr-2" />
          {saving ? "Kaydediliyor..." : "Kaydet"}
        </Button>
      </div>
      
      {/* Bot Status */}
      <Card className="bg-black/40 border-white/10 backdrop-blur">
        <CardHeader>
          <CardTitle className="text-white">Bot Durumu</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <Label className="text-white">Bot Aktif</Label>
              <p className="text-sm text-gray-400 mt-1">
                Botu aktif veya pasif yapın
              </p>
            </div>
            <Switch
              checked={settings.is_active}
              onCheckedChange={(checked) => handleChange('is_active', checked)}
              data-testid="toggle-active"
            />
          </div>
        </CardContent>
      </Card>
      
      {/* Position Sizing */}
      <Card className="bg-black/40 border-white/10 backdrop-blur">
        <CardHeader>
          <CardTitle className="text-white">Pozisyon Boyutlandırma</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label className="text-white">Pozisyon Boyutu Modu</Label>
            <Select
              value={settings.position_size_mode}
              onValueChange={(value) => handleChange('position_size_mode', value)}
            >
              <SelectTrigger className="bg-black/40 border-white/20 text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="FIXED_USDT">Sabit USDT</SelectItem>
                <SelectItem value="PERCENT_OF_EQUITY">Bakiye Yüzdesi</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div>
            <Label className="text-white">
              Pozisyon Değeri ({settings.position_size_mode === "FIXED_USDT" ? "USDT" : "%"})
            </Label>
            <Input
              type="number"
              step="0.1"
              value={settings.position_size_value}
              onChange={(e) => handleChange('position_size_value', parseFloat(e.target.value))}
              className="bg-black/40 border-white/20 text-white"
              data-testid="position-size-input"
            />
          </div>
        </CardContent>
      </Card>
      
      {/* Leverage */}
      <Card className="bg-black/40 border-white/10 backdrop-blur">
        <CardHeader>
          <CardTitle className="text-white">Kaldıraç Ayarları</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-white">Min Kaldıraç</Label>
              <Input
                type="number"
                min="1"
                max="20"
                value={settings.min_leverage}
                onChange={(e) => handleChange('min_leverage', parseInt(e.target.value))}
                className="bg-black/40 border-white/20 text-white"
                data-testid="min-leverage-input"
              />
            </div>
            <div>
              <Label className="text-white">Max Kaldıraç</Label>
              <Input
                type="number"
                min="1"
                max="20"
                value={settings.max_leverage}
                onChange={(e) => handleChange('max_leverage', parseInt(e.target.value))}
                className="bg-black/40 border-white/20 text-white"
                data-testid="max-leverage-input"
              />
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* Risk Management */}
      <Card className="bg-black/40 border-white/10 backdrop-blur">
        <CardHeader>
          <CardTitle className="text-white">Risk Yönetimi</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-white">Hedef Kar (%)</Label>
              <Input
                type="number"
                step="0.01"
                value={settings.target_profit_percent}
                onChange={(e) => handleChange('target_profit_percent', parseFloat(e.target.value))}
                className="bg-black/40 border-white/20 text-white"
                data-testid="target-profit-input"
              />
            </div>
            <div>
              <Label className="text-white">Stop Loss (%)</Label>
              <Input
                type="number"
                step="0.01"
                value={settings.stop_loss_percent}
                onChange={(e) => handleChange('stop_loss_percent', parseFloat(e.target.value))}
                className="bg-black/40 border-white/20 text-white"
                data-testid="stop-loss-input"
              />
            </div>
          </div>
          
          <div>
            <Label className="text-white">İşlem Başına Max Risk (%)</Label>
            <Input
              type="number"
              step="0.01"
              value={settings.max_risk_per_trade_percent}
              onChange={(e) => handleChange('max_risk_per_trade_percent', parseFloat(e.target.value))}
              className="bg-black/40 border-white/20 text-white"
              data-testid="max-risk-input"
            />
          </div>
          
          <div>
            <Label className="text-white">Günlük Max Zarar (USDT)</Label>
            <Input
              type="number"
              step="1"
              value={settings.max_daily_loss_usdt}
              onChange={(e) => handleChange('max_daily_loss_usdt', parseFloat(e.target.value))}
              className="bg-black/40 border-white/20 text-white"
              data-testid="max-daily-loss-input"
            />
          </div>
        </CardContent>
      </Card>
      
      {/* Trading Limits */}
      <Card className="bg-black/40 border-white/10 backdrop-blur">
        <CardHeader>
          <CardTitle className="text-white">İşlem Limitleri</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-white">Max Açık Pozisyon</Label>
              <Input
                type="number"
                min="1"
                value={settings.max_open_positions}
                onChange={(e) => handleChange('max_open_positions', parseInt(e.target.value))}
                className="bg-black/40 border-white/20 text-white"
                data-testid="max-positions-input"
              />
            </div>
            <div>
              <Label className="text-white">Günlük Max İşlem</Label>
              <Input
                type="number"
                min="1"
                value={settings.max_trades_per_day}
                onChange={(e) => handleChange('max_trades_per_day', parseInt(e.target.value))}
                className="bg-black/40 border-white/20 text-white"
                data-testid="max-trades-input"
              />
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* Info */}
      <Card className="bg-cyan-500/10 border-cyan-500/30 backdrop-blur">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-cyan-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-cyan-100 font-medium">
                Ayar Değişiklikleri
              </p>
              <p className="text-xs text-cyan-200/70 mt-1">
                Değişiklikler kaydedildikten sonra hemen uygulanır. Bot her 5 dakikada bir piyasayı kontrol eder.
                Binance API anahtarları .env dosyasından yapılandırılmalıdır.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Settings;