from picamera2 import Picamera2
import cv2
import numpy as np

# AI 카메라 초기화
picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"format": 'XRGB8888', "size": (640, 480)}
)
picam2.configure(config)
picam2.start()

# AI 모델 설정 (예: MobileNet)
picam2.set_controls({
    "AiModel": "mobilenet_v2",
    "AiEnabled": True
})

while True:
    # 프레임과 AI 결과 가져오기
    frame = picam2.capture_array()
    metadata = picam2.capture_metadata()
    
    # AI 추론 결과
    if 'AiResult' in metadata:
        detections = metadata['AiResult']
        
        for detection in detections:
            # 바운딩 박스 그리기
            x, y, w, h = detection['bbox']
            label = detection['label']
            confidence = detection['confidence']
            
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, f"{label}: {confidence:.2f}", 
                       (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.5, (0, 255, 0), 2)
    
    cv2.imshow('AI Camera', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

picam2.stop()
cv2.destroyAllWindows()
