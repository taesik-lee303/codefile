import RPi.GPIO as GPIO
import pyaudio
import speech_recognition as sr
import threading
import time
import queue
import numpy as np
from datetime import datetime

class NoiseTriggeredVoiceRecognition:
    """소음 감지 시 음성 인식을 수행하는 시스템"""
    
    def __init__(self, noise_sensor_pin=17, silence_timeout=10):
        # GPIO 설정
        self.noise_sensor_pin = noise_sensor_pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.noise_sensor_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        # 음성 인식 설정
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # PyAudio 설정
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_recording = False
        
        # 타이밍 설정
        self.silence_timeout = silence_timeout  # 10초
        self.last_noise_time = 0
        
        # 스레드 제어
        self.running = True
        self.recording_thread = None
        self.audio_queue = queue.Queue()
        
        # 음성 인식 결과 저장
        self.recognized_text = []
        
        # 상태 표시
        self.mic_active = False
        
        # 초기 마이크 캘리브레이션
        print("마이크 캘리브레이션 중...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
        print("캘리브레이션 완료!")
        
    def check_noise_sensor(self):
        """소음 센서 상태 확인"""
        return GPIO.input(self.noise_sensor_pin)
    
    def start_recording(self):
        """마이크 켜기 및 녹음 시작"""
        if not self.mic_active:
            self.mic_active = True
            self.is_recording = True
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🎤 마이크 ON - 음성 인식 시작")
            
            # 오디오 스트림 열기
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )
            
            # 녹음 스레드 시작
            self.recording_thread = threading.Thread(target=self.record_audio)
            self.recording_thread.start()
    
    def stop_recording(self):
        """마이크 끄기 및 녹음 중지"""
        if self.mic_active:
            self.mic_active = False
            self.is_recording = False
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔴 마이크 OFF")
            
            # 스트림 닫기
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            
            # 녹음 스레드 종료 대기
            if self.recording_thread:
                self.recording_thread.join()
    
    def record_audio(self):
        """오디오 녹음 (별도 스레드)"""
        audio_frames = []
        
        while self.is_recording and self.stream:
            try:
                # 오디오 데이터 읽기
                data = self.stream.read(1024, exception_on_overflow=False)
                audio_frames.append(data)
                
                # 일정 크기가 모이면 인식 시도
                if len(audio_frames) >= 30:  # 약 1초 분량
                    # 오디오 데이터 결합
                    audio_data = b''.join(audio_frames)
                    self.audio_queue.put(audio_data)
                    audio_frames = []
                    
            except Exception as e:
                print(f"녹음 오류: {e}")
                break
        
        # 남은 오디오 처리
        if audio_frames:
            audio_data = b''.join(audio_frames)
            self.audio_queue.put(audio_data)
    
    def process_audio(self):
        """오디오 처리 및 음성 인식 (별도 스레드)"""
        while self.running:
            try:
                # 큐에서 오디오 데이터 가져오기
                audio_data = self.audio_queue.get(timeout=1)
                
                # numpy 배열로 변환
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                
                # 음성 인식을 위한 AudioData 객체 생성
                audio = sr.AudioData(audio_data, 16000, 2)
                
                # 음성 인식 시도
                try:
                    # Google Speech Recognition 사용
                    text = self.recognizer.recognize_google(audio, language='ko-KR')
                    
                    if text:
                        print(f"\n💬 인식된 텍스트: {text}")
                        self.recognized_text.append({
                            'time': datetime.now().strftime('%H:%M:%S'),
                            'text': text
                        })
                        
                        # 파일에 저장
                        self.save_to_file(text)
                        
                except sr.UnknownValueError:
                    # 음성을 인식하지 못함
                    pass
                except sr.RequestError as e:
                    print(f"음성 인식 서비스 오류: {e}")
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"오디오 처리 오류: {e}")
    
    def save_to_file(self, text):
        """인식된 텍스트를 파일로 저장"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open('recognized_text.txt', 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {text}\n")
    
    def monitor_noise(self):
        """소음 센서 모니터링 메인 루프"""
        print("\n=== 소음 감지 음성 인식 시스템 시작 ===")
        print("소음이 감지되면 자동으로 음성 인식을 시작합니다.")
        print("종료하려면 Ctrl+C를 누르세요.\n")
        
        # 오디오 처리 스레드 시작
        audio_processor = threading.Thread(target=self.process_audio)
        audio_processor.start()
        
        try:
            while self.running:
                # 소음 센서 상태 확인
                noise_detected = self.check_noise_sensor()
                
                if noise_detected:
                    # 소음 감지됨
                    self.last_noise_time = time.time()
                    
                    if not self.mic_active:
                        # 마이크가 꺼져있으면 켜기
                        self.start_recording()
                    else:
                        # 이미 켜져있으면 시간만 업데이트
                        print(".", end="", flush=True)
                
                else:
                    # 소음 없음
                    if self.mic_active:
                        # 마이크가 켜져있고 타임아웃 확인
                        silence_duration = time.time() - self.last_noise_time
                        
                        if silence_duration >= self.silence_timeout:
                            # 10초 이상 조용하면 마이크 끄기
                            self.stop_recording()
                
                # CPU 부하 감소를 위한 짧은 대기
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n\n프로그램 종료 중...")
        finally:
            self.cleanup()
            audio_processor.join()
    
    def cleanup(self):
        """리소스 정리"""
        self.running = False
        
        # 녹음 중지
        if self.mic_active:
            self.stop_recording()
        
        # PyAudio 종료
        self.audio.terminate()
        
        # GPIO 정리
        GPIO.cleanup()
        
        # 최종 결과 출력
        print("\n=== 인식된 텍스트 요약 ===")
        for item in self.recognized_text[-10:]:  # 최근 10개
            print(f"[{item['time']}] {item['text']}")
        
        print(f"\n총 {len(self.recognized_text)}개의 음성이 인식되었습니다.")
        print("recognized_text.txt 파일에 저장되었습니다.")


# 간단한 테스트용 버전 (GPIO 없이)
class MockNoiseTriggeredVoiceRecognition(NoiseTriggeredVoiceRecognition):
    """GPIO 없이 테스트하는 Mock 버전"""
    
    def __init__(self, silence_timeout=10):
        # GPIO 설정 스킵
        self.noise_sensor_pin = None
        
        # 나머지는 동일
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_recording = False
        self.silence_timeout = silence_timeout
        self.last_noise_time = 0
        self.running = True
        self.recording_thread = None
        self.audio_queue = queue.Queue()
        self.recognized_text = []
        self.mic_active = False
        
        # 마이크 캘리브레이션
        print("마이크 캘리브레이션 중...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
        print("캘리브레이션 완료!")
    
    def check_noise_sensor(self):
        """키보드 입력으로 소음 시뮬레이션 (스페이스바)"""
        # 실제로는 키보드 입력을 사용
        import sys, select
        
        # 논블로킹 입력 확인
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            line = sys.stdin.readline()
            return True
        return False
    
    def cleanup(self):
        """리소스 정리 (GPIO 제외)"""
        self.running = False
        
        if self.mic_active:
            self.stop_recording()
        
        self.audio.terminate()
        
        print("\n=== 인식된 텍스트 요약 ===")
        for item in self.recognized_text[-10:]:
            print(f"[{item['time']}] {item['text']}")
        
        print(f"\n총 {len(self.recognized_text)}개의 음성이 인식되었습니다.")


if __name__ == "__main__":
    import sys
    
    # 명령줄 인자 확인
    if len(sys.argv) > 1 and sys.argv[1] == "--mock":
        # GPIO 없이 테스트
        print("Mock 모드로 실행 (GPIO 없음)")
        print("Enter 키를 눌러 소음을 시뮬레이션하세요.")
        system = MockNoiseTriggeredVoiceRecognition()
    else:
        # 실제 GPIO 사용
        try:
            system = NoiseTriggeredVoiceRecognition(
                noise_sensor_pin=17,  # GPIO 17번 핀
                silence_timeout=10    # 10초
            )
        except Exception as e:
            print(f"GPIO 초기화 실패: {e}")
            print("Mock 모드로 전환합니다.")
            system = MockNoiseTriggeredVoiceRecognition()
    
    # 시스템 실행
    system.monitor_noise()