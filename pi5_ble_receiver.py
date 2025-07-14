import asyncio
import json
import time
from datetime import datetime
from bleak import BleakScanner, BleakClient

class Pi5BLEReceiver:
    def __init__(self):
        """Pi5 BLE 수신기 초기화"""
        self.device_address = None
        self.client = None
        self.trigger_callback = None
        
        # 타겟 디바이스 정보
        self.target_name = "PicoSecurity"
        self.target_service_uuid = "12345678-1234-1234-1234-123456789abc"
        self.target_char_uuid = "87654321-4321-4321-4321-cba987654321"
        
        print("🔧 Pi5 BLE 수신기 초기화")
    
    def set_trigger_callback(self, callback_func):
        """트리거 콜백 함수 설정"""
        self.trigger_callback = callback_func
        print("✓ 트리거 콜백 함수 등록됨")
    
    async def scan_for_pico(self, timeout=10):
        """Pico 디바이스 스캔"""
        print(f"🔍 {self.target_name} 스캔 중... (최대 {timeout}초)")
        
        devices = await BleakScanner.discover(timeout=timeout)
        
        for device in devices:
            if device.name and self.target_name in device.name:
                self.device_address = device.address
                print(f"✅ {self.target_name} 발견!")
                print(f"📍 주소: {device.address}")
                print(f"📶 신호강도: {device.rssi}dBm")
                return True
        
        print(f"❌ {self.target_name}를 찾을 수 없습니다")
        return False
    
    def parse_trigger_data(self, data):
        """수신된 트리거 데이터 파싱"""
        try:
            json_str = data.decode('utf-8')
            trigger_data = json.loads(json_str)
            
            # 데이터 검증
            if trigger_data.get('type') == 'security_trigger':
                return trigger_data
            else:
                print(f"⚠️ 알 수 없는 데이터 타입: {trigger_data.get('type')}")
                return None
                
        except Exception as e:
            print(f"❌ 데이터 파싱 오류: {e}")
            return None
    
    def notification_handler(self, sender, data):
        """BLE 알림 핸들러"""
        receive_time = datetime.now()
        
        print(f"\n🔔 BLE 신호 수신: {receive_time.strftime('%H:%M:%S')}")
        
        # 데이터 파싱
        trigger_data = self.parse_trigger_data(data)
        
        if trigger_data:
            print(f"📊 트리거 데이터:")
            print(f"   PIR: {trigger_data.get('pir')}")
            print(f"   소음레벨: {trigger_data.get('sound_level')}")
            print(f"   타임스탬프: {trigger_data.get('timestamp')}")
            print(f"   디바이스: {trigger_data.get('device')}")
            
            # 콜백 함수 호출 (카메라/마이크/스피커/디스플레이 제어)
            if self.trigger_callback:
                self.trigger_callback(trigger_data)
        else:
            print("❌ 유효하지 않은 트리거 데이터")
    
    async def connect_and_listen(self):
        """BLE 연결 및 수신 대기"""
        if not self.device_address:
            if not await self.scan_for_pico():
                return False
        
        try:
            print(f"🔗 {self.device_address}에 연결 중...")
            
            async with BleakClient(self.device_address) as client:
                self.client = client
                print(f"✅ 연결 성공!")
                
                # 서비스 확인
                services = await client.get_services()
                print(f"📋 사용 가능한 서비스: {len(services)}개")
                
                # 알림 구독
                await client.start_notify(self.target_char_uuid, self.notification_handler)
                print(f"🔔 알림 구독 시작")
                print("📡 트리거 신호 대기 중...")
                
                # 무한 대기 (Ctrl+C로 중단)
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    print("\n👋 사용자에 의해 중단됨")
                
        except Exception as e:
            print(f"❌ 연결 오류: {e}")
            return False
        finally:
            print("🔌 BLE 연결 해제")
