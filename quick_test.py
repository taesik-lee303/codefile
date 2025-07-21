# quick_test.py
try:
    import bleak
    print("✅ Bleak 임포트 성공")
    
    from bleak import BleakClient, BleakScanner
    print("✅ 주요 클래스 임포트 성공")
    
    # 버전 정보 (가능한 방법들)
    version_info = []
    
    if hasattr(bleak, '__version__'):
        version_info.append(f"__version__: {bleak.__version__}")
    
    if hasattr(bleak, 'VERSION'):
        version_info.append(f"VERSION: {bleak.VERSION}")
    
    if version_info:
        print("버전 정보:")
        for info in version_info:
            print(f"  {info}")
    else:
        print("⚠️ 버전 정보를 찾을 수 없음 (구버전일 가능성)")
    
    print("✅ Bleak 기본 테스트 통과")
    
except Exception as e:
    print(f"❌ Bleak 테스트 실패: {e}")
