import pyttsx3
import os
from gtts import gTTS
import pygame
import tempfile

class TextToSpeech:
    def __init__(self):
        """TTS 엔진 초기화"""
        self.pyttsx_engine = pyttsx3.init()
        # 고정된 설정 적용
        self.pyttsx_engine.setProperty('rate', 200)  # 말하기 속도 고정
        self.pyttsx_engine.setProperty('volume', 1.0)  # 음량 고정        
    def speak_with_pyttsx3(self, text):
        """
        pyttsx3를 사용한 음성 출력 (오프라인)
        
        Args:
            text (str): 변환할 텍스트
        """
        try:
            # 음성 출력
            self.pyttsx_engine.say(text)
            self.pyttsx_engine.runAndWait()
            
        except Exception as e:
            print(f"pyttsx3 오류: {e}")
    
    def speak_with_gtts(self, text, lang='ko'):
        """
        Google TTS를 사용한 음성 출력 (온라인 필요)
        
        Args:
            text (str): 변환할 텍스트
            lang (str): 언어 코드 ('ko': 한국어, 'en': 영어)
        """
        try:
            # TTS 객체 생성 (slow=False로 고정)
            tts = gTTS(text=text, lang=lang, slow=False)
            
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

def main():
    """메인 함수"""
    tts = TextToSpeech()
    
    print("=== 텍스트 음성 변환 프로그램 ===")
    print("텍스트를 입력하면 음성으로 출력됩니다.")
    print("종료하려면 'quit' 또는 'exit'를 입력하세요.\n")
    
    while True:
        text = input("텍스트 입력: ").strip()
        
        if text.lower() in ['quit', 'exit', '종료']:
            print("프로그램을 종료합니다.")
            break
        
        if text:
            print("🔊 음성 출력 중...")
            tts.speak_with_pyttsx3(text)
        else:
            print("텍스트를 입력해주세요.")

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
        # 대화형 프로그램 실행
        main()
            
    except KeyboardInterrupt:
        print("\n프로그램이 중단되었습니다.")
    except ImportError as e:
        print(f"필요한 라이브러리가 설치되지 않았습니다: {e}")
        print("다음 명령어로 설치해주세요:")
        print("pip install pyttsx3 gtts pygame")
