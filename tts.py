import pyttsx3
import os
from gtts import gTTS
import pygame
import tempfile

class TextToSpeech:
    def __init__(self):
        """TTS 엔진 초기화"""
        self.pyttsx_engine = pyttsx3.init()
        
    def speak_with_pyttsx3(self, text, rate=200, volume=0.9):
        """
        pyttsx3를 사용한 음성 출력 (오프라인)
        
        Args:
            text (str): 변환할 텍스트
            rate (int): 말하기 속도 (기본값: 200)
            volume (float): 음량 (0.0 ~ 1.0, 기본값: 0.9)
        """
        try:
            # 속도 설정
            self.pyttsx_engine.setProperty('rate', rate)
            
            # 음량 설정
            self.pyttsx_engine.setProperty('volume', volume)
            
            # 음성 출력
            self.pyttsx_engine.say(text)
            self.pyttsx_engine.runAndWait()
            
        except Exception as e:
            print(f"pyttsx3 오류: {e}")
    
    def speak_with_gtts(self, text, lang='ko', slow=False):
        """
        Google TTS를 사용한 음성 출력 (온라인 필요)
        
        Args:
            text (str): 변환할 텍스트
            lang (str): 언어 코드 ('ko': 한국어, 'en': 영어)
            slow (bool): 느린 속도 여부
        """
        try:
            # TTS 객체 생성
            tts = gTTS(text=text, lang=lang, slow=slow)
            
            # 임시 파일에 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                temp_filename = tmp_file.name
                tts.save(temp_filename)
            
            # pygame으로 재생
            pygame.mixer.init()
            pygame.mixer.music.load(temp_filename)
            pygame.mixer.music.play()
            
            # 재생 완료까지 대기
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
            
            # 임시 파일 삭제
            os.unlink(temp_filename)
            
        except Exception as e:
            print(f"gTTS 오류: {e}")
    
    def get_available_voices(self):
        """사용 가능한 음성 목록 반환"""
        voices = self.pyttsx_engine.getProperty('voices')
        for i, voice in enumerate(voices):
            print(f"{i}: {voice.name} - {voice.languages}")
        return voices
    
    def set_voice(self, voice_index):
        """음성 설정"""
        voices = self.pyttsx_engine.getProperty('voices')
        if 0 <= voice_index < len(voices):
            self.pyttsx_engine.setProperty('voice', voices[voice_index].id)
        else:
            print("잘못된 음성 인덱스입니다.")

def main():
    """메인 함수"""
    tts = TextToSpeech()
    
    while True:
        print("\n=== 텍스트 음성 변환 프로그램 ===")
        print("1. pyttsx3로 음성 출력 (오프라인)")
        print("2. Google TTS로 음성 출력 (온라인)")
        print("3. 사용 가능한 음성 목록 보기")
        print("4. 음성 변경")
        print("5. 종료")
        
        choice = input("\n선택하세요 (1-5): ").strip()
        
        if choice == '1':
            text = input("변환할 텍스트를 입력하세요: ").strip()
            if text:
                rate = input("말하기 속도 (기본값: 200): ").strip()
                rate = int(rate) if rate.isdigit() else 200
                
                volume = input("음량 (0.0-1.0, 기본값: 0.9): ").strip()
                try:
                    volume = float(volume) if volume else 0.9
                    volume = max(0.0, min(1.0, volume))  # 0.0-1.0 범위로 제한
                except ValueError:
                    volume = 0.9
                
                print("음성 출력 중...")
                tts.speak_with_pyttsx3(text, rate, volume)
        
        elif choice == '2':
            text = input("변환할 텍스트를 입력하세요: ").strip()
            if text:
                lang = input("언어 (ko: 한국어, en: 영어, 기본값: ko): ").strip()
                lang = lang if lang in ['ko', 'en', 'ja', 'zh'] else 'ko'
                
                slow = input("느린 속도로 재생하시겠습니까? (y/n, 기본값: n): ").strip().lower()
                slow = slow == 'y'
                
                print("음성 출력 중...")
                tts.speak_with_gtts(text, lang, slow)
        
        elif choice == '3':
            print("\n사용 가능한 음성 목록:")
            tts.get_available_voices()
        
        elif choice == '4':
            print("\n사용 가능한 음성 목록:")
            voices = tts.get_available_voices()
            try:
                voice_index = int(input("음성 번호를 선택하세요: "))
                tts.set_voice(voice_index)
                print("음성이 변경되었습니다.")
            except ValueError:
                print("잘못된 입력입니다.")
        
        elif choice == '5':
            print("프로그램을 종료합니다.")
            break
        
        else:
            print("잘못된 선택입니다. 1-5 중에서 선택해주세요.")

# 간단한 사용 예제
def simple_example():
    """간단한 사용 예제"""
    tts = TextToSpeech()
    
    # 한국어 텍스트 음성 출력 (pyttsx3)
    print("pyttsx3로 한국어 출력...")
    tts.speak_with_pyttsx3("안녕하세요. 텍스트 음성 변환 테스트입니다.")
    
    # 영어 텍스트 음성 출력 (Google TTS)
    print("Google TTS로 영어 출력...")
    tts.speak_with_gtts("Hello, this is a text to speech test.", lang='en')

if __name__ == "__main__":
    # 필요한 라이브러리 설치 안내
    print("필요한 라이브러리:")
    print("pip install pyttsx3 gtts pygame")
    print()
    
    try:
        # 간단한 예제 실행 또는 메인 프로그램 실행
        choice = input("1: 간단한 예제 실행, 2: 대화형 프로그램 실행 (1/2): ").strip()
        
        if choice == '1':
            simple_example()
        else:
            main()
            
    except KeyboardInterrupt:
        print("\n프로그램이 중단되었습니다.")
    except ImportError as e:
        print(f"필요한 라이브러리가 설치되지 않았습니다: {e}")
        print("다음 명령어로 설치해주세요:")
        print("pip install pyttsx3 gtts pygame")