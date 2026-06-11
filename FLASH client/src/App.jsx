import React, { useState, useEffect } from 'react';
import { 
  Settings2, 
  ChevronLeft, 
  CheckCircle2, 
  AlertCircle, 
  Wifi, 
  Signal, 
  BatteryFull,
  ScanLine,
  Receipt,
  Bell,
  Eye,
  EyeOff,
  ArrowRightLeft,
  Wallet,
  Smartphone,
  ChevronRight,
  Activity,
  QrCode,
  Landmark,
  Zap
} from 'lucide-react';

// --- Konfigurasi Simulasi Jaringan ---
const NETWORK_PROFILES = {
  '5G': { name: '5G (Ultra Fast)', delay: 50, color: 'text-green-500', bg: 'bg-green-100', border: 'border-green-500' },
  '4G': { name: '4G LTE (Normal)', delay: 150, color: 'text-blue-500', bg: 'bg-blue-100', border: 'border-blue-500' },
  '3G': { name: '3G (Slow)', delay: 600, color: 'text-yellow-500', bg: 'bg-yellow-100', border: 'border-yellow-500' },
  'RURAL': { name: 'Rural Area (Edge)', delay: 2000, color: 'text-orange-500', bg: 'bg-orange-100', border: 'border-orange-500' },
  'OFFLINE': { name: 'Offline / Timeout', delay: 10000, color: 'text-red-500', bg: 'bg-red-100', border: 'border-red-500' }
};

export default function App() {
  // --- State Aplikasi ---
  const [currentScreen, setCurrentScreen] = useState('dashboard');
  const [merchantId, setMerchantId] = useState('CIMB-57555-452');
  const [amount, setAmount] = useState('50000');
  const [showBalance, setShowBalance] = useState(true);
  
  // State Simulasi & Metrik
  const [networkProfile, setNetworkProfile] = useState('RURAL');
  const [isFlashEnabled, setIsFlashEnabled] = useState(false);
  const [lastLatency, setLastLatency] = useState(null);
  const [latencyHistory, setLatencyHistory] = useState([]);
  
  // State Data Transaksi
  const [merchantData, setMerchantData] = useState(null);
  const [transactionData, setTransactionData] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [balance, setBalance] = useState(5000000);

  // Waktu
  const [currentTime, setCurrentTime] = useState('');
  useEffect(() => {
    const updateTime = () => setCurrentTime(new Date().toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }));
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // --- API / Logic Simulation ---
  const simulateApiCall = async (apiName, requestData) => {
    const baseNetworkDelay = NETWORK_PROFILES[networkProfile].delay;
    const legacyBlockingDelay = 2500; 
    
    // Logika simulasi disederhanakan
    const actualDelay = isFlashEnabled 
      ? 45 // Fast track
      : baseNetworkDelay + legacyBlockingDelay;

    const startTime = Date.now();

    return new Promise((resolve, reject) => {
      setTimeout(() => {
        const endTime = Date.now();
        const latency = endTime - startTime;
        
        setLastLatency(latency);
        setLatencyHistory(prev => [{ 
          endpoint: apiName, 
          latency, 
          time: new Date().toLocaleTimeString('id-ID'),
          flash: isFlashEnabled
        }, ...prev].slice(0, 4));

        if (networkProfile === 'OFFLINE') {
          reject(new Error('Request Timeout / Koneksi Terputus'));
          return;
        }

        if (apiName === '/inquiry') {
          if (!requestData.merchantId) reject(new Error('Merchant ID tidak valid'));
          else resolve({
            id: "inq-" + Math.random().toString(36).substr(2, 9),
            transaction_ref: "INQ-" + Date.now(),
            type: "QRIS_INQUIRY",
            status: "SUCCESS",
            amount: parseInt(requestData.amount),
            currency: "IDR",
            merchant_name: "Toko Buku Sejahtera",
            description: "Test inquiry QRIS",
          });
        } else if (apiName === '/payment') {
          resolve({
            id: "pay-" + Math.random().toString(36).substr(2, 9),
            transaction_ref: "PAY-" + Date.now(),
            type: "QRIS_PAYMENT",
            status: "SUCCESS",
            amount: requestData.amount,
            currency: "IDR",
            description: "Payment berhasil"
          });
        }
      }, actualDelay);
    });
  };

  // --- Handlers ---
  const handleInquiry = async () => {
    if (!merchantId || !amount || parseInt(amount) <= 0) return;
    setCurrentScreen('processing');
    setErrorMsg('');
    try {
      const response = await simulateApiCall('/inquiry', { merchantId, amount });
      setMerchantData(response);
      setCurrentScreen('inquiry');
    } catch (err) {
      setErrorMsg(err.message);
      setCurrentScreen('error');
    }
  };

  const handlePayment = async () => {
    setCurrentScreen('processing');
    try {
      const response = await simulateApiCall('/payment', { merchantId, amount: merchantData.amount });
      setTransactionData(response);
      setBalance(prev => prev - response.amount);
      setCurrentScreen('success');
    } catch (err) {
      setErrorMsg(err.message);
      setCurrentScreen('error');
    }
  };

  const resetApp = () => {
    setCurrentScreen('dashboard');
    setMerchantData(null);
    setTransactionData(null);
    setErrorMsg('');
  };

  // --- UI Components ---
  const iOSStatusBar = ({ isDark = false }) => (
    <div className={`flex justify-between items-center px-5 pt-3 pb-1 text-xs font-semibold z-50 transition-colors shrink-0 ${isDark ? 'text-white' : 'text-black'}`}>
      <span>{currentTime}</span>
      <div className="w-24 h-5 bg-black rounded-full absolute left-1/2 -translate-x-1/2 top-1.5 z-50"></div>
      <div className="flex space-x-1.5 items-center">
        <Signal size={14} />
        <Wifi size={14} />
        <BatteryFull size={16} />
      </div>
    </div>
  );

  return (
    <div className="min-h-[100dvh] bg-gray-100 flex flex-col lg:flex-row items-center justify-center p-4 lg:p-6 font-sans gap-6 lg:gap-10 overflow-x-hidden">
      
      {/* --- PHONE CONTAINER MOCKUP --- */}
      {/* Menggunakan fixed width/height agar konten di dalamnya edge-to-edge sempurna */}
      <div className="relative w-[320px] min-w-[320px] h-[680px] bg-gray-50 rounded-[2.5rem] shadow-2xl border-[6px] border-black overflow-hidden shrink-0 flex flex-col">
        
        {/* iOS Home Indicator */}
        <div className="absolute bottom-1.5 left-1/2 -translate-x-1/2 w-1/3 h-1.5 bg-black/80 rounded-full z-50 pointer-events-none"></div>

        {/* SCREEN: DASHBOARD */}
        {currentScreen === 'dashboard' && (
          <div className="flex-1 w-full flex flex-col animate-in fade-in duration-300 relative bg-gray-50">
            <div className="bg-red-600 rounded-b-[2rem] pb-6 relative shadow-sm shrink-0 w-full">
              {iOSStatusBar({ isDark: true })}
              
              <div className="px-5 pt-4 flex justify-between items-center">
                <div className="text-white">
                  <p className="text-[10px] opacity-90">Selamat datang,</p>
                  <h1 className="text-lg font-bold">Budi Hartono</h1>
                </div>
                <div className="w-8 h-8 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center text-white relative">
                  <Bell size={16} />
                  <span className="absolute top-1.5 right-2 w-1.5 h-1.5 bg-yellow-400 rounded-full"></span>
                </div>
              </div>

              <div className="mx-4 mt-4 bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-4 text-white shadow-md">
                <div className="flex justify-between items-center mb-1">
                  <p className="text-xs font-medium opacity-90">Rekening Utama</p>
                  <button onClick={() => setShowBalance(!showBalance)} className="p-1">
                    {showBalance ? <Eye size={14} /> : <EyeOff size={14} />}
                  </button>
                </div>
                <h2 className="text-xl font-bold mb-3 font-mono tracking-tight">
                  {showBalance ? `Rp ${balance.toLocaleString('id-ID')}` : 'Rp ••••••••'}
                </h2>
                <div className="flex items-center space-x-1 text-[9px] bg-black/20 w-fit px-2.5 py-1 rounded-full">
                  <span>1234-5678-9012</span>
                </div>
              </div>
            </div>

            <div className="px-4 -mt-4 relative z-10 mb-4 shrink-0 w-full">
              <div className="bg-white rounded-2xl p-3 shadow-sm border border-gray-100 grid grid-cols-4 gap-y-2">
                <div className="flex flex-col items-center gap-1.5">
                  <button className="w-9 h-9 bg-red-50 text-red-600 rounded-xl flex items-center justify-center">
                    <ArrowRightLeft size={18} />
                  </button>
                  <span className="text-[9px] font-medium text-gray-600">Transfer</span>
                </div>
                <div className="flex flex-col items-center gap-1.5">
                  <button className="w-9 h-9 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center">
                    <Wallet size={18} />
                  </button>
                  <span className="text-[9px] font-medium text-gray-600">Top Up</span>
                </div>
                <div className="flex flex-col items-center gap-1.5">
                  <button className="w-9 h-9 bg-green-50 text-green-600 rounded-xl flex items-center justify-center">
                    <Smartphone size={18} />
                  </button>
                  <span className="text-[9px] font-medium text-gray-600">Pulsa</span>
                </div>
                <div className="flex flex-col items-center gap-1.5 cursor-pointer" onClick={() => setCurrentScreen('scan')}>
                  <button className="w-9 h-9 bg-red-600 text-white rounded-xl flex items-center justify-center shadow-md shadow-red-600/30 active:scale-95 transition-all">
                    <QrCode size={18} />
                  </button>
                  <span className="text-[9px] font-bold text-red-600">Pay QRIS</span>
                </div>
              </div>
            </div>

            <div className="px-5 flex-1 w-full pb-6">
              <div className="flex justify-between items-center mb-2">
                <h3 className="text-sm font-bold text-gray-900">Riwayat</h3>
                <button className="text-[10px] text-red-600 font-semibold">Semua</button>
              </div>
              <div className="space-y-2.5">
                <div className="flex items-center justify-between bg-white p-3 rounded-xl border border-gray-100 shadow-sm w-full">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 bg-orange-100 text-orange-500 rounded-lg flex items-center justify-center shrink-0">
                      <Landmark size={14} />
                    </div>
                    <div>
                      <p className="text-[11px] font-bold text-gray-900">Transfer Keluar</p>
                      <p className="text-[9px] text-gray-500">BCA - Zaki</p>
                    </div>
                  </div>
                  <span className="text-xs font-bold text-gray-900">- Rp 150.000</span>
                </div>
                
                {transactionData && (
                  <div className="flex items-center justify-between bg-white p-3 rounded-xl border border-gray-100 shadow-sm border-l-2 border-l-red-500 w-full">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 bg-red-100 text-red-600 rounded-lg flex items-center justify-center shrink-0">
                        <QrCode size={14} />
                      </div>
                      <div className="overflow-hidden">
                        <p className="text-[11px] font-bold text-gray-900 truncate">QRIS Payment</p>
                        <p className="text-[9px] text-gray-500 truncate w-24">{merchantData?.merchant_name}</p>
                      </div>
                    </div>
                    <span className="text-xs font-bold text-gray-900 whitespace-nowrap">- Rp {transactionData.amount.toLocaleString('id-ID')}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* SCREEN: SCAN QRIS */}
        {currentScreen === 'scan' && (
          <div className="flex-1 w-full flex flex-col bg-gray-50 animate-in slide-in-from-right duration-300">
            {iOSStatusBar({ isDark: false })}
            
            <div className="flex items-center px-4 mb-3 z-10 shrink-0 w-full">
              <button onClick={() => setCurrentScreen('dashboard')} className="p-1.5 -ml-1 text-gray-900 active:opacity-50 bg-white rounded-full shadow-sm border border-gray-200">
                <ChevronLeft size={20} />
              </button>
              <h1 className="text-sm font-bold text-gray-900 ml-2">Scan QRIS</h1>
            </div>

            <div className="flex-1 px-4 flex flex-col w-full pb-6">
              <div className="relative w-full aspect-square bg-gray-900 rounded-3xl overflow-hidden mb-4 flex items-center justify-center shadow-inner shrink-0 max-h-[220px]">
                <ScanLine size={50} className="text-white/20 animate-pulse" />
                <div className="absolute inset-6 border-2 border-dashed border-white/50 rounded-2xl"></div>
              </div>

              <div className="bg-white rounded-2xl p-4 shadow-sm border border-gray-100 relative shrink-0 w-full">
                <div className="space-y-3 pt-1">
                  <div>
                    <label className="block text-[10px] font-bold text-gray-700 mb-1 ml-1">Merchant ID</label>
                    <input 
                      type="text" 
                      value={merchantId}
                      onChange={(e) => setMerchantId(e.target.value)}
                      className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-red-500 font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-gray-700 mb-1 ml-1">Nominal (Rp)</label>
                    <input 
                      type="number" 
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                      className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm font-bold text-gray-900 focus:outline-none focus:ring-1 focus:ring-red-500"
                    />
                  </div>
                  <button 
                    onClick={handleInquiry}
                    className="w-full bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg py-3 mt-1 shadow-md shadow-red-600/30 active:scale-95 transition-all flex justify-center items-center gap-1.5 text-xs"
                  >
                    <span>Lanjutkan</span>
                    <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* SCREEN: INQUIRY (CONFIRMATION) */}
        {currentScreen === 'inquiry' && merchantData && (
          <div className="flex-1 w-full flex flex-col bg-gray-50 animate-in slide-in-from-right duration-300">
            {iOSStatusBar({ isDark: false })}
            
            <div className="flex items-center px-4 mb-2 shrink-0 w-full">
              <button onClick={() => setCurrentScreen('scan')} className="p-1.5 -ml-1 text-gray-900 active:opacity-50">
                <ChevronLeft size={24} />
              </button>
              <h1 className="text-sm font-bold text-gray-900 ml-1">Konfirmasi</h1>
            </div>

            <div className="px-4 pb-6 flex-1 flex flex-col w-full">
              <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 flex-1 relative overflow-hidden flex flex-col w-full">
                
                <div className="text-center mb-5 relative z-10 shrink-0 w-full">
                  <div className="w-14 h-14 bg-white rounded-full flex items-center justify-center mx-auto mb-2 shadow-sm border border-gray-100">
                    <Receipt className="text-red-600" size={24} />
                  </div>
                  <h2 className="text-gray-400 text-[9px] uppercase tracking-widest mb-0.5 font-bold">Penerima</h2>
                  <p className="text-lg font-bold text-gray-900 leading-tight truncate">{merchantData.merchant_name}</p>
                  <p className="text-[10px] text-gray-400 font-mono mt-1 bg-gray-50 inline-block px-1.5 py-0.5 rounded">ID: {merchantId}</p>
                </div>

                <div className="border-t border-dashed border-gray-100 py-4 mb-2 shrink-0 w-full">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-gray-500 text-xs font-medium">Nominal</span>
                    <span className="text-lg font-bold text-gray-900 font-mono">Rp {merchantData.amount.toLocaleString('id-ID')}</span>
                  </div>
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="text-gray-500">Biaya Admin</span>
                    <span className="text-green-600 font-bold bg-green-50 px-1.5 rounded">Gratis</span>
                  </div>
                </div>

                <div className="bg-gray-50 rounded-xl p-3 mt-auto border border-gray-100 shrink-0 w-full">
                  <div className="flex items-center space-x-2.5">
                    <div className="w-8 h-8 bg-red-600 rounded-md flex items-center justify-center text-white font-bold text-[8px] shadow-sm shrink-0">CIMB</div>
                    <div className="overflow-hidden">
                      <p className="text-xs font-bold text-gray-900 truncate">Rekening Utama</p>
                      <p className="text-[10px] text-gray-500">Rp {balance.toLocaleString('id-ID')}</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="pt-4 shrink-0 w-full">
                 <button 
                  onClick={handlePayment}
                  className="w-full bg-red-600 hover:bg-red-700 text-white font-bold rounded-xl py-3.5 shadow-lg shadow-red-600/20 active:scale-95 transition-all flex items-center justify-center text-sm"
                >
                  <span>Bayar</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* SCREEN: PROCESSING */}
        {currentScreen === 'processing' && (
          <div className="flex-1 w-full flex flex-col bg-white">
             {iOSStatusBar({ isDark: false })}
            <div className="flex-1 flex flex-col items-center justify-center animate-in fade-in duration-200 w-full">
              <div className="relative mb-6">
                <div className="w-16 h-16 border-4 border-red-50 rounded-full"></div>
                <div className="w-16 h-16 border-4 border-red-600 rounded-full border-t-transparent animate-spin absolute top-0 left-0"></div>
                <div className="absolute inset-0 flex items-center justify-center">
                  {isFlashEnabled ? (
                    <Zap size={20} className="text-yellow-500 animate-bounce" />
                  ) : (
                    <Wifi size={20} className={NETWORK_PROFILES[networkProfile].color + " animate-pulse"} />
                  )}
                </div>
              </div>
              <h2 className="text-base font-bold text-gray-900 mb-1">Memproses...</h2>
              <div className="text-[10px] text-gray-500 text-center px-6 leading-relaxed">
                {isFlashEnabled 
                  ? <span className="text-green-600 font-bold flex flex-col items-center">
                      Akselerasi Memori Aktif
                    </span>
                  : <span>Via jaringan {NETWORK_PROFILES[networkProfile].name}</span>
                }
              </div>
            </div>
          </div>
        )}

        {/* SCREEN: SUCCESS */}
        {currentScreen === 'success' && transactionData && (
          <div className="flex-1 w-full flex flex-col bg-gray-50 pt-4 animate-in zoom-in-95 duration-400">
             {iOSStatusBar({ isDark: false })}
            <div className="flex-1 flex flex-col items-center px-4 mt-4 w-full">
              <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mb-4 shadow-lg shadow-green-500/20 shrink-0">
                <CheckCircle2 size={32} className="text-white" />
              </div>
              <h1 className="text-lg font-bold text-gray-900 mb-0.5">Berhasil!</h1>
              <p className="text-gray-500 mb-4 text-[10px]">Dana telah diteruskan.</p>

              <div className="w-full bg-white rounded-2xl p-4 shadow-sm border border-gray-100 space-y-4 text-left relative overflow-hidden shrink-0">
                <div className="absolute top-0 right-0 p-3 opacity-5 pointer-events-none">
                  <Receipt size={60} />
                </div>
                <div>
                  <p className="text-[9px] font-bold text-gray-400 uppercase">Nominal</p>
                  <p className="text-xl font-bold text-gray-900 font-mono mt-0.5">Rp {transactionData.amount.toLocaleString('id-ID')}</p>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <p className="text-[9px] font-bold text-gray-400 uppercase">Referensi</p>
                    <p className="text-[10px] font-mono text-gray-900 mt-0.5 truncate pr-2">{transactionData.transaction_ref}</p>
                  </div>
                  <div>
                    <p className="text-[9px] font-bold text-gray-400 uppercase">Waktu</p>
                    <p className="text-[10px] font-mono text-gray-900 mt-0.5">{new Date().toLocaleTimeString('id-ID')}</p>
                  </div>
                </div>
                
                {isFlashEnabled && (
                  <div className="bg-yellow-50 p-2 rounded-lg border border-yellow-100 flex items-start gap-2 mt-2">
                    <Zap size={14} className="text-yellow-600 mt-0.5 shrink-0 animate-pulse" />
                    <p className="text-[9px] text-yellow-800 leading-tight">
                      Log transaksi diselesaikan di latar belakang tanpa menunda respons.
                    </p>
                  </div>
                )}
              </div>
            </div>
            
            <div className="pb-6 px-4 shrink-0 pt-2 w-full">
               <button 
                onClick={resetApp}
                className="w-full bg-gray-900 hover:bg-black text-white font-bold rounded-xl py-3 active:scale-95 transition-all text-xs shadow-md"
              >
                Selesai
              </button>
            </div>
          </div>
        )}

        {/* SCREEN: ERROR */}
        {currentScreen === 'error' && (
          <div className="flex-1 w-full flex flex-col bg-gray-50 animate-in slide-in-from-bottom duration-300">
             {iOSStatusBar({ isDark: false })}
            <div className="flex-1 flex flex-col items-center justify-center p-5 text-center w-full">
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4 border-2 border-white shadow-sm">
                <AlertCircle size={32} className="text-red-600" />
              </div>
              <h1 className="text-lg font-bold text-gray-900 mb-2">Gagal</h1>
              <div className="bg-red-50 text-red-700 px-3 py-2 rounded-lg border border-red-100 w-full mb-6 text-[10px] break-words">
                {errorMsg}
              </div>
              
              <button 
                onClick={() => setCurrentScreen('dashboard')}
                className="w-full bg-gray-900 text-white font-bold rounded-lg py-3 active:scale-95 transition-all shadow-sm mb-2 text-xs"
              >
                Kembali
              </button>
              <button 
                onClick={() => setCurrentScreen('scan')}
                className="w-full bg-white text-gray-700 border border-gray-200 font-bold rounded-lg py-3 active:scale-95 transition-all text-xs"
              >
                Coba Ulang
              </button>
            </div>
          </div>
        )}
      </div>
      
      {/* --- EXTERNAL CONTROL PANEL --- */}
      <div className="w-full max-w-[340px] shrink-0 flex flex-col gap-3">
        
        <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-200">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-blue-100 text-blue-600 rounded-lg">
              <Settings2 size={18} />
            </div>
            <div>
              <h2 className="text-base font-bold text-gray-900 leading-none">Kontrol Simulasi</h2>
              <p className="text-[10px] text-gray-500 mt-1">Skenario Optimasi Throughput QRIS</p>
            </div>
          </div>
        </div>

        {/* FLASH CONTROL CARD */}
        <div className={`p-4 rounded-2xl shadow-sm border-2 transition-colors duration-500 relative overflow-hidden ${isFlashEnabled ? 'bg-indigo-900 border-indigo-500' : 'bg-white border-gray-200'}`}>
          <div className="flex justify-between items-center relative z-10">
            <div>
              <h3 className={`font-bold flex items-center gap-1.5 text-sm ${isFlashEnabled ? 'text-white' : 'text-gray-900'}`}>
                <Zap size={16} className={isFlashEnabled ? 'text-yellow-400 fill-yellow-400' : 'text-gray-400'}/> 
                Sistem FLASH
              </h3>
              <p className={`text-[9px] font-mono tracking-wide mt-0.5 ${isFlashEnabled ? 'text-indigo-200' : 'text-gray-500'}`}>
                Akselerasi Memori & Proses Paralel
              </p>
            </div>
            
            <button 
              onClick={() => setIsFlashEnabled(!isFlashEnabled)}
              className={`w-11 h-6 rounded-full transition-colors relative flex items-center px-1 border focus:outline-none ${isFlashEnabled ? 'bg-green-500 border-green-400' : 'bg-gray-200 border-gray-300'}`}
            >
              <div className={`w-4 h-4 bg-white rounded-full shadow-sm transform transition-transform duration-300 ${isFlashEnabled ? 'translate-x-5' : 'translate-x-0'}`}></div>
            </button>
          </div>

          <p className={`text-[10px] mt-3 relative z-10 leading-relaxed ${isFlashEnabled ? 'text-blue-100' : 'text-gray-600'}`}>
            {isFlashEnabled 
              ? "⚡ Nyala: Memintas antrean sistem lama. Menggunakan memori kilat & menyelesaikan tugas sekunder di latar belakang."
              : "Mati: Berjalan normal. Seluruh request akan tertahan (blocking) menunggu respons sistem utama yang lambat."}
          </p>
        </div>

        {/* Network Simulator Card */}
        <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-200">
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-bold text-gray-900 flex items-center gap-1.5 text-xs">
              <Wifi size={14} className="text-gray-500"/> Profil Jaringan
            </h3>
            <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${NETWORK_PROFILES[networkProfile].bg} ${NETWORK_PROFILES[networkProfile].color} ${NETWORK_PROFILES[networkProfile].border}`}>
              {NETWORK_PROFILES[networkProfile].delay} ms base
            </span>
          </div>
          
          <div className="space-y-1.5">
            {Object.entries(NETWORK_PROFILES).map(([key, profile]) => (
              <button
                key={key}
                onClick={() => setNetworkProfile(key)}
                className={`w-full flex items-center justify-between p-2 rounded-lg border transition-all group ${
                  networkProfile === key 
                    ? `border-blue-500 bg-blue-50` 
                    : `border-transparent bg-gray-50 hover:bg-gray-100`
                }`}
              >
                <div className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full ${profile.color.replace('text', 'bg')} ${networkProfile === key ? 'animate-pulse' : ''}`}></div>
                  <span className={`text-xs font-semibold ${networkProfile === key ? 'text-blue-700' : 'text-gray-700'}`}>
                    {profile.name}
                  </span>
                </div>
                {networkProfile === key && <CheckCircle2 className="text-blue-500" size={14} />}
              </button>
            ))}
          </div>
        </div>

        {/* Metrics & Logs Card */}
        <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-200 flex-1 flex flex-col min-h-[140px]">
          <h3 className="font-bold text-gray-900 flex items-center gap-1.5 text-xs mb-2">
            <Activity size={14} className="text-gray-500"/> Log Latensi API
          </h3>
          
          {lastLatency === null ? (
            <div className="flex-1 bg-gray-50 border border-dashed border-gray-300 rounded-xl flex items-center justify-center p-4 text-center text-gray-400 text-[10px]">
              Belum ada transaksi diuji.
            </div>
          ) : (
            <div className="space-y-3">
              <div className={`flex justify-between items-center text-white p-3 rounded-xl shadow-inner ${isFlashEnabled ? 'bg-gradient-to-r from-green-600 to-emerald-600' : 'bg-gray-900'}`}>
                <div>
                  <span className="text-[9px] font-bold opacity-80 uppercase tracking-widest block">
                    P95 Latency
                  </span>
                </div>
                <span className="text-xl font-mono font-bold flex items-end gap-1">
                  {lastLatency} <span className="text-[10px] font-normal opacity-80 mb-0.5">ms</span>
                </span>
              </div>

              <div>
                <div className="space-y-1.5">
                  {latencyHistory.map((log, idx) => (
                    <div key={idx} className="flex justify-between items-center p-2 bg-gray-50 rounded-lg border border-gray-100">
                      <div className="flex items-center gap-2">
                        {log.flash ? <Zap size={10} className="text-yellow-500 fill-yellow-500" /> : <div className="w-2.5" />}
                        <span className="text-[9px] text-gray-400 font-mono bg-white px-1 py-0.5 rounded shadow-sm border border-gray-100">{log.time}</span>
                        <span className="font-bold text-gray-700 text-[10px]">{log.endpoint}</span>
                      </div>
                      <span className={`font-mono font-bold text-[10px] ${log.latency > 1500 ? 'text-red-500' : log.latency > 300 ? 'text-yellow-600' : 'text-green-600'}`}>
                        {log.latency}ms
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}