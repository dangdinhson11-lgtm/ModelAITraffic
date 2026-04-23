import os
import requests
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from analytics.models import TrafficCamera, TrafficHistory
from analytics.ai_utils import analyze_image
from datetime import datetime
from time import sleep

class Command(BaseCommand):
    help = 'Toi uu hoa bo cao anh: Ghi de anh cu va dung Session de tang toc'

    def handle(self, *args, **options):
        # 1. Dung Session de tai su dung ket noi (Tang toc do)
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Accept": "image/avif,image/webp,*/*",
            "Referer": "https://giaothong.hochiminhcity.gov.vn/",
        })
        
        # Sao chep Cookies tu script goc
        cookies = {
            "ASP.NET_SessionId": "t2oslxxsqllan4lgzhah3cgt",
            ".VDMS": "C50F85C6C71667BE6ED050D74003980406811A8F6C3BE32B157BABF3CD92E74B0BA3E01A4B490B8BA16EAF15828702B1FB68957AD67317B9D42579BB90FCC150AF18CA519E195678537CA47740D9831A7E454628FC6A4097185A66629BB114F7EE9611E85CE9747C30D5968598EFBF67382F9DD1",
            "_frontend": "!9YOHO1qc4zwwKz24P1VY/lC/bQptjssYZ3m9UbDnTWnCQqqoOil+geXpFacMNljkY7bQh63nOwwyIko=",
        }
        session.cookies.update(cookies)

        cameras = TrafficCamera.objects.exclude(camera_id__isnull=True)
        
        while True:
            self.stdout.write(self.style.SUCCESS(f"\n=== CHU KY CAP NHAT: {datetime.now().strftime('%H:%M:%S')} ==="))
            
            for camera in cameras:
                url = f"https://giaothong.hochiminhcity.gov.vn:8007/Render/CameraHandler.ashx?id={camera.camera_id}&bg=black&w=640&h=480"
                
                try:
                    resp = session.get(url, timeout=10)
                    if resp.status_code == 200:
                        # 2. GIAI PHAP TOI UU: Xoa anh cu truoc khi luu anh moi de tranh nhan ban file
                        if camera.last_image:
                            old_path = camera.last_image.path
                            if os.path.exists(old_path):
                                os.remove(old_path)
                        
                        # Luu anh moi voi ten co dinh
                        file_name = f"{camera.camera_id}.jpg"
                        camera.last_image.save(file_name, ContentFile(resp.content), save=False)
                        
                        # Chay AI phan tich
                        results = analyze_image(camera.last_image.path, road_area_pixels=camera.road_area_pixels)
                        
                        # Cap nhat Database
                        camera.current_density = results['density']
                        camera.current_vehicle_count = results['vehicle_count']
                        camera.current_traffic_level = results['traffic_level']
                        camera.save()
                        
                        # Luu lich su (chi luu data, khong luu file anh lich su de tiet kiem o cung)
                        TrafficHistory.objects.create(
                            camera=camera,
                            density_pce=results['density'],
                            vehicle_count=results['vehicle_count'],
                            traffic_level=results['traffic_level']
                        )
                        self.stdout.write(f" OK -> {camera.title}: {results['density']}%")
                    else:
                        self.stdout.write(self.style.WARNING(f" Loi {resp.status_code} tai {camera.title}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f" Error {camera.title}: {str(e)}"))
            
            # 3. Giai phong bo nho sau moi chu ky
            import gc
            gc.collect()
            
            self.stdout.write(self.style.SUCCESS("--- Cho 60 giay de tiep tuc ---"))
            sleep(60)
