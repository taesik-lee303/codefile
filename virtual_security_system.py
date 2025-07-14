#!/usr/bin/env python3
"""
Pi5 가상 보안 시스템 - 블루투스 테스트용
실제 하드웨어 명령어 대신 가상으로 상태만 표시
"""

import asyncio
import json
import time
from datetime import datetime
from bleak import BleakScanner, BleakClient
import threading
import signal
import sys

class VirtualHardwareController:
    """가상 하드웨어 제어기 - 실제 명령어 대신 상태만 표시"""
    
    def __init__(self):
        self.camera_active = False
        self.microphone_active = False
        self.speaker_active = False
        self.display_active = False
        
        # 상태 표시용 타이머들
        self.status_timers = {}
        
        print("🔧 가상 하드웨어 제어기 초기화")
        self.show_hardware_status()
    
    def show_hardware_status(self):
        """현재 하드웨어 상태 표시"""
        print("\n📊 현재 하드웨어 상태:")
        print(f"   📷 카메라: {'🟢 ON' if self.camera_active else '🔴 OFF'}")
        print(f"   🎤 마이크: {'🟢 ON' if self.microphone_active else '🔴 OFF'}")
        print(f"   🔊 스피커: {'🟢 ON' if self.speaker_active else '🔴 OFF'}")
        print(f"   🖥️ 디스플레이: {'🟢 ON' if self.display_active else '🔴 OFF'}")
    
    def turn_on_camera(self):
        """가상 카메라 켜기"""
        if not self.camera_active:
            print("📷 [가상] 카메라 활성화 시뮬레이션")
            print("   └─ libcamera-hello 실행 시뮬레이션")
            self.camera_active = True
            print("   ✅ 카메라 가상 활성화 완료")
    
    def turn_off_camera(self):
        """가상 카메라 끄기"""
        if self.camera_active:
            print("📷 [가상] 카메라 비활성화 시뮬레이션")
            print("   └─ pkill libcamera-hello 시뮬레이션")
            self.camera_active = False
            print("   ✅ 카메라 가상 비활성화 완료")
    
    def turn_on_microphone(self):
        """가상 마이크 켜기"""
        if not self.microphone_active:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            recording_file = f"/tmp/virtual_recording_{timestamp}.wav"
            
            print("🎤 [가상] 마이크 활성화 시뮬레이션")
            print(f"   └─ arecord 녹음 시작 시뮬레이션: {recording_file}")
            self.microphone_active = True
            self.virtual_recording_file = recording_file
            print("   ✅ 마이크 가상 활성화 완료")
    
    def turn_off_microphone(self):
        """가상 마이크 끄기"""
        if self.microphone_active:
            print("🎤 [가상] 마이크 비활성화 시뮬레이션")
            print("   └─ pkill arecord 시뮬레이션")
            if hasattr(self, 'virtual_recording_file'):
                print(f"   └─ 가상 녹음 파일: {self.virtual_recording_file}")
            self.microphone_active = False
            print("   ✅ 마이크 가상 비활성화 완료")
    
    def turn_on_speaker(self):
        """가상 스피커 켜기"""
        print("🔊 [가상] 스피커 활성화 시뮬레이션")
        print("   └─ speaker-test 보안 알림음 재생 시뮬레이션")
        print("   └─ ♪♪♪ 경고음: 1500Hz ♪♪♪")
        self.speaker_active = True
        
        # 5초 후 자동 종료 시뮬레이션
        def auto_off():
            time.sleep(5)
            if self.speaker_active:
                self.turn_off_speaker()
        
        threading.Thread(target=auto_off, daemon=True).start()
        print("   ✅ 스피커 가상 활성화 완료 (5초 후 자동 종료)")
    
    def turn_off_speaker(self):
        """가상 스피커 끄기"""
        if self.speaker_active:
            print("🔊 [가상] 스피커 비활성화 시뮬레이션")
            print("   └─ pkill speaker-test 시뮬레이션")
            self.speaker_active = False
            print("   ✅ 스피커 가상 비활성화 완료")
    
    def turn_on_display(self):
        """가상 디스플레이 켜기"""
        if not self.display_active:
            print("🖥️ [가상] 디스플레이 활성화 시뮬레이션")
            print("   └─ vcgencmd display_power 1 시뮬레이션")
            self.display_active = True
            print("   ✅ 디스플레이 가상 활성화 완료")
    
    def turn_off_display(self):
        """가상 디스플레이 끄기"""
        if self.display_active:
            print("🖥️ [가상] 디스플레이 비활성화 시뮬레이션")
            print("   └─ vcgencmd display_power 0 시뮬레이션")
            self.display_active = False
            print("   ✅ 디스플레이 가상 비활성화 완료")
    
    def activate_all_devices(self, signal_data):
        """모든 장치 가상 활성화"""
        print(f"\n🚨🚨🚨 보안 시스템 활성화! 🚨🚨🚨")
        print("="*50)
        print(f"📊 수신 데이터:")
        print(f"   PIR: {signal_data.get('pir')}")
        print(f"   소음레벨: {signal_data.get('sound_level')}")
        print(f"   타임스탬프: {signal_data.get('timestamp')}")
        print(f"   디바이스: {signal_data.get('device')}")
        print(f"⏰ 수신 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*50)
        
        print("\n🔄 모든 장치 가상 활성화 중...")
        
        # 순차적으로 모든 장치 활성화
        self.turn_on_camera()
        time.sleep(0.5)
        self.turn_on_microphone()
        time.sleep(0.5)
        self.turn_on_speaker()
        time.sleep(0.5)
        self.turn_on_display()
        
        print("\n✅ 모든 장치 가상 활성화 완료!")
        self.show_hardware_status()
        print("📡 Pico에서 비활성화 신호 대기 중...")
    
    def deactivate_all_devices(self, signal_data):
        """모든 장치 가상 비활성화"""
        print(f"\n😴😴😴 보안 시스템 비활성화! 😴😴😴")
        print("="*50)
        print(f"📊 수신 데이터:")
        print(f"   조용한 지속시간: {signal_data.get('quiet_duration')}초")
        print(f"   타임스탬프: {signal_data.get('timestamp')}")
        print(f"   디바이스: {signal_data.get('device')}")
        print(f"⏰ 수신 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*50)
        
        print("\n🔄 모든 장치 가상 비활성화 중...")
        
        # 순차적으로 모든 장치 비활성화
        self.turn_off_camera()
        time.sleep(0.5)
        self.turn_off_microphone()
        time.sleep(0.5)
        self.turn_off_speaker()
        time.sleep(0.5)
        self.turn_off_display()
        
        print("\n✅ 모든 장치 가상 비활성화 완료!")
        self.show_hardware_status()
        print("📡 다음 활성화 신호 대기 중...")
    
    def cleanup(self):
        """가상 시스템 정리"""
        print("\n🧹 가상 하드웨어 제어기 정리 중...")
        
        # 모든 장치 끄기
        self.turn_off_camera()
        self.turn_off_microphone()
        self.turn_off_speaker()
        self.turn_off_display()
        
        print("✅ 가상 시스템 정리 완료")


class BluetoothReceiver:
    """블루투스 수신기"""
    
    def __init__(self):
        self.device_address = None
        self.client = None
        self.activate_callback = None
        self.deactivate_callback = None
        
        # 타겟 디바이스 정보
        self.target_name = "PicoSecurity"
        self.target_service_uuid = "12345678-1234-1234-1234-123456789abc"
        self.target_char_uuid = "87654321-4321-4321-4321-cba987654321"
        
        # 연결 통계
        self.connection_attempts = 0
        self.successful_connections = 0
        self.received_messages = 0
        
        print("🔧 블루투스 수신기 초기화")
    
    def set_callbacks(self, activate_func, deactivate_func):
        """콜백 함수들 설정"""
        self.activate_callback = activate_func
        self.deactivate_callback = deactivate_func
        print("✓ 활성화/비활성화 콜백 함수 등록됨")
    
    async def scan_for_devices(self, timeout=10):
        """블루투스 디바이스 스캔"""
        print(f"\n🔍 블루투스 디바이스 스캔 중... (최대 {timeout}초)")
        print("   찾는 디바이스: PicoSecurity")
        
        try:
            devices = await BleakScanner.discover(timeout=timeout)
            
            print(f"\n📱 발견된 디바이스: {len(devices)}개")
            
            target_found = False
            for i, device in enumerate(devices, 1):
                device_name = device.name or "Unknown"
                print(f"   {i}. {device_name} ({device.address}) - {device.rssi}dBm")
                
                if device.name and self.target_name in device.name:
                    self.device_address = device.address
                    target_found = True
                    print(f"   🎯 타겟 디바이스 발견!")
            
            if target_found:
                print(f"✅ {self.target_name} 발견!")
                print(f"📍 주소: {self.device_address}")
                return True
            else:
                print(f"❌ {self.target_name}를 찾을 수 없습니다")
                print(f"💡 Pico가 실행 중인지 확인하세요")
                return False
                
        except Exception as e:
            print(f"❌ 스캔 오류: {e}")
            return False
    
    def parse_signal_data(self, data):
        """수신된 신호 데이터 파싱"""
        try:
            json_str = data.decode('utf-8')
            signal_data = json.loads(json_str)
            
            print(f"\n📦 원본 데이터: {json_str}")
            
            # 데이터 타입 확인
            signal_type = signal_data.get('type')
            if signal_type in ['security_activate', 'security_deactivate']:
                return signal_data
            else:
                print(f"⚠️ 알 수 없는 신호 타입: {signal_type}")
                return None
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 오류: {e}")
            print(f"📦 원본 데이터: {data}")
            return None
        except Exception as e:
            print(f"❌ 데이터 파싱 오류: {e}")
            return None
    
    def notification_handler(self, sender, data):
        """BLE 알림 핸들러"""
        self.received_messages += 1
        receive_time = datetime.now()
        
        print(f"\n🔔🔔🔔 BLE 신호 수신! 🔔🔔🔔")
        print(f"📅 수신 시간: {receive_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        print(f"📊 수신 카운트: {self.received_messages}")
        print(f"📍 송신자: {sender}")
        print(f"📦 데이터 크기: {len(data)} bytes")
        
        # 데이터 파싱
        signal_data = self.parse_signal_data(data)
        
        if signal_data:
            signal_type = signal_data.get('type')
            
            if signal_type == 'security_activate':
                print(f"\n🚨 활성화 신호 수신 확인!")
                print(f"📊 상세 정보:")
                print(f"   - PIR 상태: {signal_data.get('pir')}")
                print(f"   - 소음 레벨: {signal_data.get('sound_level')}")
                print(f"   - 타임스탬프: {signal_data.get('timestamp')}")
                print(f"   - 송신 디바이스: {signal_data.get('device')}")
                
                # 활성화 콜백 호출
                if self.activate_callback:
                    self.activate_callback(signal_data)
                    
            elif signal_type == 'security_deactivate':
                print(f"\n😴 비활성화 신호 수신 확인!")
                print(f"📊 상세 정보:")
                print(f"   - 조용한 지속시간: {signal_data.get('quiet_duration')}초")
                print(f"   - 타임스탬프: {signal_data.get('timestamp')}")
                print(f"   - 송신 디바이스: {signal_data.get('device')}")
                
                # 비활성화 콜백 호출
                if self.deactivate_callback:
                    self.deactivate_callback(signal_data)
        else:
            print("❌ 유효하지 않은 신호 데이터")
    
    async def connect_and_listen(self):
        """BLE 연결 및 수신 대기"""
        self.connection_attempts += 1
        
        if not self.device_address:
            if not await self.scan_for_devices():
                return False
        
        try:
            print(f"\n🔗 연결 시도 #{self.connection_attempts}")
            print(f"📍 타겟: {self.device_address}")
            
            async with BleakClient(self.device_address) as client:
                self.client = client
                self.successful_connections += 1
                
                print(f"✅ BLE 연결 성공!")
                print(f"📊 연결 통계: {self.successful_connections}/{self.connection_attempts}")
                
                # 연결된 디바이스 정보
                device_info = await client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
                print(f"📱 디바이스명: {device_info.decode()}")
                
                # 서비스 확인
                services = await client.get_services()
                print(f"📋 사용 가능한 서비스: {len(services)}개")
                
                # 알림 구독
                print(f"🔔 알림 구독 중...")
                await client.start_notify(self.target_char_uuid, self.notification_handler)
                print(f"✅ 알림 구독 완료!")
                
                print("\n" + "="*60)
                print("📡 실시간 신호 수신 대기 중...")
                print("💡 Pico에서 PIR + 소음센서 트리거하세요!")
                print("⌨️  Ctrl+C로 종료")
                print("="*60)
                
                # 무한 대기 (Ctrl+C로 중단)
                try:
                    while True:
                        await asyncio.sleep(1)
                        
                        # 주기적 상태 출력 (30초마다)
                        if time.time() % 30 < 1:
                            print(f"📊 상태: 연결됨, 수신: {self.received_messages}개")
                            
                except KeyboardInterrupt:
                    print(f"\n👋 사용자에 의해 중단됨")
                
        except Exception as e:
            print(f"❌ 연결 오류: {e}")
            print(f"💡 해결 방법:")
            print(f"   1. Pico가 실행 중인지 확인")
            print(f"   2. 블루투스가 활성화되어 있는지 확인")
            print(f"   3. 거리가 너무 멀지 않은지 확인")
            return False
        finally:
            print("🔌 BLE 연결 해제")
            print(f"📊 최종 통계: 수신 메시지 {self.received_messages}개")


class VirtualSecuritySystem:
    """가상 보안 시스템 메인 클래스"""
    
    def __init__(self):
        self.receiver = BluetoothReceiver()
        self.controller = VirtualHardwareController()
        
        # 콜백 등록
        self.receiver.set_callbacks(
            self.controller.activate_all_devices,    # 활성화 콜백
            self.controller.deactivate_all_devices   # 비활성화 콜백
        )
        
        print("🚀 가상 보안 시스템 초기화 완료")
    
    def signal_handler(self, signum, frame):
        """시그널 핸들러 (Ctrl+C 처리)"""
        print(f"\n🛑 종료 신호 수신됨 (signal {signum})")
        self.cleanup()
        sys.exit(0)
    
    def cleanup(self):
        """시스템 정리"""
        print("🧹 가상 보안 시스템 종료 중...")
        self.controller.cleanup()
        print("✅ 가상 보안 시스템 종료 완료")
    
    async def run(self):
        """메인 실행 함수"""
        print("\n" + "="*70)
        print("🛡️ Pi5 가상 보안 시스템 (블루투스 테스트)")
        print("="*70)
        print("📋 기능:")
        print("   - Pico로부터 BLE 신호 수신 테스트")
        print("   - 가상 하드웨어 제어 시뮬레이션")
        print("   - 실시간 상태 모니터링")
        print("")
        print("🔧 테스트 환경:")
        print("   - 실제 하드웨어 명령어 실행 안함")
        print("   - 모든 동작을 가상으로 시뮬레이션")
        print("   - 블루투스 연결 및 데이터 수신만 실제 동작")
        print("="*70)
        
        # 시그널 핸들러 등록
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            # BLE 수신 시작
            success = await self.receiver.connect_and_listen()
            if not success:
                print("❌ 블루투스 연결 실패")
                return False
        except Exception as e:
            print(f"❌ 시스템 오류: {e}")
        finally:
            self.cleanup()


def main():
    """메인 실행 함수"""
    print("🎯 Pi5 가상 보안 시스템 시작")
    
    try:
        system = VirtualSecuritySystem()
        asyncio.run(system.run())
    except KeyboardInterrupt:
        print("\n👋 프로그램 종료")
    except Exception as e:
        print(f"❌ 실행 오류: {e}")


if __name__ == "__main__":
    main()
