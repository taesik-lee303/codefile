#!/usr/bin/env python3
"""
모든 센서 동시에 실행 - 라즈베리파이 5 호환
"""

import time
import threading
import signal
import sys

print("🚀 라즈베리파이 5 호환 다중 센서 시스템 시작...")

# 센서 클래스 임포트
try:
    from infrared_sensor import InfraredSensor
    from sound_sensor import SoundSensor
    from dht_sensor import DHTSensor
    print("✓ 모든 센서 모듈 로드 완료")
except ImportError as e:
    print(f"✗ 센서 모듈 로드 실패: {e}")
    sys.exit(1)

# 센서 인스턴스 생성
sensors = {}

def initialize_sensors():
    """센서 초기화"""
    print("\n🔧 센서 초기화 중...")
    
    try:
        sensors["infrared"] = InfraredSensor()
        print("✓ 적외선 센서 초기화 완료")
    except Exception as e:
        print(f"✗ 적외선 센서 초기화 실패: {e}")
    
    try:
        sensors["sound"] = SoundSensor()
        print("✓ 소음 센서 초기화 완료")
    except Exception as e:
        print(f"✗ 소음 센서 초기화 실패: {e}")
    
    try:
        sensors["dht"] = DHTSensor()
        print("✓ 온습도 센서 초기화 완료")
    except Exception as e:
        print(f"✗ 온습도 센서 초기화 실패: {e}")
    
    print(f"📊 총 {len(sensors)}개 센서 초기화 완료\n")

# 종료 핸들러
def signal_handler(sig, frame):
    print("\n🛑 모든 센서 종료 중...")
    for name, sensor in sensors.items():
        try:
            print(f"   🔄 {name} 센서 종료 중...")
            sensor.stop()
            print(f"   ✓ {name} 센서 종료 완료")
        except Exception as e:
            print(f"   ✗ {name} 센서 종료 실패: {e}")
    print("👋 시스템 종료 완료")
    sys.exit(0)

# 메인 함수
def main():
    print("=" * 60)
    print("🏥 DeepCare 다중 센서 모니터링 시스템")
    print("🔧 라즈베리파이 5 호환 버전")
    print("=" * 60)
    print("📡 GPIO 17: 적외선 센서")
    print("🔊 GPIO 27: 소음 센서")
    print("🌡️ GPIO 22: 온습도 센서")
    print("=" * 60)
    
    # 센서 초기화
    initialize_sensors()
    
    if not sensors:
        print("✗ 사용 가능한 센서가 없습니다.")
        return
    
    # 모든 센서 시작
    started_sensors = []
    for name, sensor in sensors.items():
        print(f"🚀 {name} 센서 시작 중...")
        try:
            if sensor.start():
                started_sensors.append(name)
                print(f"✓ {name} 센서 시작 성공")
            else:
                print(f"✗ {name} 센서 시작 실패")
        except Exception as e:
            print(f"✗ {name} 센서 시작 오류: {e}")
    
    if not started_sensors:
        print("✗ 시작된 센서가 없습니다.")
        return
    
    print(f"\n🎉 {len(started_sensors)}개 센서가 성공적으로 시작되었습니다!")
    print("📊 시작된 센서:", ", ".join(started_sensors))
    
    # 종료 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("\n🔄 모든 센서가 실행 중입니다...")
    print("⚠️  Ctrl+C로 종료하세요.")
    print("=" * 60)
    
    # 상태 모니터링
    start_time = time.time()
    
    try:
        while True:
            time.sleep(10)  # 10초마다 상태 출력
            
            # 실행 시간 계산
            elapsed = int(time.time() - start_time)
            hours = elapsed // 3600
            minutes = (elapsed % 3600) // 60
            seconds = elapsed % 60
            
            # 센서 상태 확인
            active_count = sum(1 for name in started_sensors if sensors[name].running)
            
            print(f"⏰ 실행 시간: {hours:02d}:{minutes:02d}:{seconds:02d} | "
                  f"활성 센서: {active_count}/{len(started_sensors)}")
            
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()
