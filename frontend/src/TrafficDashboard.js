import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Camera, Activity, Play, ChevronRight, Upload } from 'lucide-react';

const TrafficDashboard = () => {
  const [cameras, setCameras] = useState([]);
  const [selectedCamera, setSelectedCamera] = useState(null);
  const [view, setView] = useState('grid');
  const [realtimeData, setRealtimeData] = useState(null);

  // 1. Lay danh sach camera khi load trang
  useEffect(() => {
    fetch('http://localhost:8000/api/cameras/')
      .then(res => res.json())
      .then(data => setCameras(data));
  }, []);

  // 2. Co che keo anh lien tuc (Polling) khi xem chi tiet
  useEffect(() => {
    let interval;
    if (view === 'detail' && selectedCamera) {
      interval = setInterval(() => {
        // Trong thuc te, day se la API call de lay frame moi nhat tu camera URL
        // Hoac Frontend tu fetch anh tu camera URL roi upload len Django process
        refreshCameraData();
      }, 3000); // 3 giay cap nhat 1 lan
    }
    return () => clearInterval(interval);
  }, [view, selectedCamera]);

  const refreshCameraData = () => {
    fetch(`http://localhost:8000/api/cameras/${selectedCamera.id}/`)
      .then(res => res.json())
      .then(data => {
        setRealtimeData(data);
      });
  };

  const handleSelectCamera = (camera) => {
    setSelectedCamera(camera);
    setRealtimeData(camera);
    setView('detail');
  };

  return (
    <div className="min-h-screen bg-[#060e20] text-[#dee5ff]">
      <header className="fixed top-0 w-full z-50 h-20 bg-[#060e20]/60 backdrop-blur-3xl border-b border-[#a1faff]/10 flex items-center px-8">
        <h1 className="text-2xl font-bold tracking-tighter text-[#a1faff]">AI TRAFFIC HUB</h1>
      </header>

      <main className="pt-28 px-8 pb-12">
        {view === 'grid' ? (
          <section>
            <div className="flex justify-between items-center mb-10">
                <h2 className="text-4xl font-bold uppercase italic">Giám sát Camera Trực tiếp</h2>
                <button className="flex items-center gap-2 px-6 py-2 bg-primary text-on-primary rounded-xl font-bold">
                    <Upload size={18} /> Tải lên Video Phân tích
                </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {cameras.map(cam => (
                <div key={cam.id} onClick={() => handleSelectCamera(cam)} className="bg-[#0f1930] rounded-3xl p-6 border border-white/5 hover:border-primary/30 cursor-pointer transition-all">
                  <div className="aspect-video bg-black rounded-2xl mb-4 overflow-hidden relative">
                    <img src={cam.last_image || 'https://via.placeholder.com/320x180?text=No+Live+Stream'} className="w-full h-full object-cover" />
                    <div className="absolute top-3 left-3 px-2 py-1 bg-rose-500 text-[10px] font-bold rounded uppercase animate-pulse">Live</div>
                  </div>
                  <h4 className="font-bold text-lg">{cam.title}</h4>
                  <div className="flex justify-between mt-4 text-sm">
                    <span className="text-gray-400">Mật độ:</span>
                    <span className="text-[#a1faff] font-bold">{cam.current_density}%</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        ) : (
          <section className="animate-in fade-in duration-500">
            <button onClick={() => setView('grid')} className="flex items-center gap-2 text-gray-400 hover:text-primary mb-6">
              <ChevronRight className="rotate-180" /> Quay lại danh sách
            </button>
            
            <div className="grid grid-cols-12 gap-8">
              <div className="col-span-12 lg:col-span-8">
                <div className="relative aspect-video bg-black rounded-[2rem] overflow-hidden border border-primary/20 shadow-2xl">
                  <img src={realtimeData?.last_image} className="w-full h-full object-contain" />
                  <div className="absolute top-6 left-6 px-4 py-2 bg-black/60 backdrop-blur-md rounded-full border border-primary/30 flex items-center gap-2">
                    <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
                    <span className="text-xs font-bold uppercase tracking-widest text-emerald-500">Đang xử lý AI thời gian thực</span>
                  </div>
                </div>

                <div className="mt-8 bg-[#0f1930]/40 backdrop-blur-xl p-8 rounded-[2rem] border border-white/5">
                  <h3 className="text-xl font-bold mb-6">Biến thiên lưu lượng (Lịch sử)</h3>
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={realtimeData?.history || []}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
                        <XAxis dataKey="timestamp" hide />
                        <YAxis stroke="#6d758c" fontSize={12} />
                        <Tooltip />
                        <Area type="monotone" dataKey="density_pce" stroke="#a1faff" fill="#a1faff" fillOpacity={0.1} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>

              <div className="col-span-12 lg:col-span-4 space-y-6">
                <div className="bg-[#0f1930] p-8 rounded-3xl border border-white/5">
                  <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Mật độ hiện tại</span>
                  <div className="text-6xl font-bold text-primary my-2">{realtimeData?.current_density.toFixed(1)}%</div>
                  <div className="px-3 py-1 bg-primary/10 text-primary text-xs font-bold rounded-full inline-block">{realtimeData?.current_traffic_level}</div>
                </div>
                
                <div className="bg-[#0f1930] p-8 rounded-3xl border border-white/5">
                  <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Số lượng phương tiện</span>
                  <div className="text-6xl font-bold text-emerald-400 my-2">{realtimeData?.current_vehicle_count}</div>
                  <span className="text-sm text-gray-400">Xe đang trong vùng quan tâm</span>
                </div>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
};

export default TrafficDashboard;
