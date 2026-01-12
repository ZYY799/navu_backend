"""
YOLO视觉识别服务
"""
from typing import List, Dict
from config.settings import settings
from app.models.schemas import ObstacleInfo
import base64
import io
import sys
try:
    import numpy as np
except Exception:
    np = None
from PIL import Image
import tempfile
import os
from pathlib import Path
import urllib.request

if sys.platform == 'win32' and hasattr(sys.stdout, 'buffer'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


class YOLOService:

    def __init__(self):
        self.model_path = settings.YOLO_MODEL_PATH
        self.confidence = settings.YOLO_CONFIDENCE
        self.device = settings.YOLO_DEVICE
        self.mock_mode = settings.MOCK_MODE
        self.model = None
        self._device_auto: str = ""
        self._fail_streak: int = 0

    def _weights_path(self) -> str:
        return self.model_path

    def _ensure_weights(self) -> bool:
        path = Path(self._weights_path())
        if path.exists():
            return True

        url = getattr(settings, "YOLO_MODEL_URL", None) or os.getenv(
            "YOLO_MODEL_URL",
            "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt"
        )

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            print(f"[YOLO] weights not found, downloading: {url} -> {path}")
            urllib.request.urlretrieve(url, str(path))
            print("[YOLO] download done.")
            return True
        except Exception as e:
            print(f"[YOLO] download failed: {e}")
            return False
        
    def _load_model(self):

        try:
            if not self._ensure_weights():
                raise RuntimeError("weights not available")

            try:
                import torch
                auto_dev = "cuda" if torch.cuda.is_available() else "cpu"
            except Exception:
                auto_dev = "cpu"

            dev = (self.device or "").strip().lower()
            if dev in ["cuda", "cpu", "mps"]:
                self._device_auto = dev
            else:
                self._device_auto = auto_dev

            from ultralytics import YOLO
            self.model = YOLO(self.model_path)
            print(f"YOLO模型加载成功: {self.model_path}  device={self._device_auto}")
        except Exception as e:
            print(f"YOLO模型加载失败: {e}")
            print("将使用模拟模式")
            self.mock_mode = True
            self.model = None
    
    async def detect_batch(self, images_base64: List[str]) -> List[Dict]:

        if (not self.mock_mode) and (self.model is None):
            self._load_model()

        if self.mock_mode:
            return self._mock_detection(len(images_base64))

        results: List[Dict] = []
        any_infer_ok: bool = False

        for idx, img_b64 in enumerate(images_base64, 1):
            temp_file = None
            try:
                b64 = (img_b64 or "").strip()

                if b64.startswith("data:") and "," in b64:
                    b64 = b64.split(",", 1)[1].strip()

                pad = (-len(b64)) % 4
                if pad:
                    b64 = b64 + ("=" * pad)

                img_data = base64.b64decode(b64)

                image = Image.open(io.BytesIO(img_data))
                image.load()

                if image.mode != "RGB":
                    image = image.convert("RGB")

                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                image.save(temp_file.name, "JPEG")
                temp_file.close()

                detections = self.model(
                    temp_file.name,
                    conf=self.confidence,
                    device=(getattr(self, "_device_auto", "") or None),
                    verbose=False
                )[0]

                obstacles = []
                if hasattr(detections, "boxes") and len(detections.boxes) > 0:
                    for det in detections.boxes.data:
                        x1, y1, x2, y2, conf, cls = det
                        obstacles.append({
                            "class": int(cls),
                            "confidence": float(conf),
                            "bbox": [float(x1), float(y1), float(x2), float(y2)]
                        })

                results.append({"obstacles": obstacles})
                any_infer_ok = True
                print(f"图片 {idx} 检测完成: 发现 {len(obstacles)} 个对象")

            except Exception as e:
                print(f"图片 {idx} 检测失败: {e}")
                import traceback
                traceback.print_exc()
                results.append({"obstacles": []})

            finally:
                if temp_file and os.path.exists(temp_file.name):
                    try:
                        os.unlink(temp_file.name)
                    except Exception:
                        pass

        if not any_infer_ok:
            print("本轮 3 张均推理失败 -> fallback mock_detection(本轮)")
            return self._mock_detection(len(images_base64))

        return results

    
    def _mock_detection(self, count: int) -> List[Dict]:
        return [
            {
                "obstacles": [
                    {
                        "class": 0,  # 台阶
                        "confidence": 0.85,
                        "bbox": [100, 200, 300, 400]
                    },
                    {
                        "class": 2,  # 障碍物
                        "confidence": 0.75,
                        "bbox": [400, 150, 500, 350]
                    }
                ]
            }
            for _ in range(count)
        ]
    
    def aggregate_obstacles(self, detections: List[Dict]) -> List[ObstacleInfo]:

        all_obs: List[ObstacleInfo] = []

        for detection in detections:
            for obs in detection.get("obstacles", []):
                obstacle_type = self._map_class_to_type(obs["class"])
                distance = self._estimate_distance(obs["bbox"])
                direction = self._estimate_direction(obs["bbox"])

                all_obs.append(ObstacleInfo(
                    type=obstacle_type,
                    distance=distance,
                    direction=direction,
                    confidence=obs["confidence"]
                ))

        dedup = {}
        for o in all_obs:
            dist_bucket = round(o.distance * 2) / 2
            key = (o.type, o.direction, dist_bucket)
            if key not in dedup or (o.confidence > dedup[key].confidence):
                dedup[key] = o

        merged = list(dedup.values())
        merged.sort(key=lambda x: x.distance)
        return merged[:5]
    
    @staticmethod
    def _map_class_to_type(class_id: int) -> str:

        mapping = {
            0: "stairs",
            1: "curb",
            2: "obstacle",
            3: "blind_path_broken",
            4: "slope"
        }
        return mapping.get(class_id, "obstacle")
    
    @staticmethod
    def _estimate_distance(bbox: List[float]) -> float:

        x1, y1, x2, y2 = bbox
        area = (x2 - x1) * (y2 - y1)

        norm_area = area / (640 * 480)

        distance = 10 / (norm_area * 100 + 0.1)
        return round(distance, 1)
    
    @staticmethod
    def _estimate_direction(bbox: List[float]) -> str:

        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2

        if center_x < 213:
            return "左前方"
        elif center_x > 427:
            return "右前方"
        else:
            return "正前方"
    
    def calculate_safety_level(self, obstacles: List[ObstacleInfo]) -> int:

        if not obstacles:
            return 5

        closest = min(obs.distance for obs in obstacles)
        
        if closest < 2:
            return 1
        elif closest < 5:
            return 2
        elif closest < 10:
            return 3
        elif closest < 20:
            return 4
        else:
            return 5
    
    def describe_road_condition(self, obstacles: List[ObstacleInfo]) -> str:

        if not obstacles:
            return "道路通畅，无明显障碍"

        type_cn = {
            "stairs": "台阶",
            "curb": "路沿",
            "obstacle": "障碍物",
            "blind_path_broken": "盲道中断",
            "slope": "坡道"
        }

        top = sorted(obstacles, key=lambda x: x.distance)[:2]

        parts = []
        for o in top:
            parts.append(f"{o.direction}{o.distance}米{type_cn.get(o.type, '障碍物')}")

        if len(obstacles) >= 3:
            return f"前方障碍较多（{len(obstacles)}处），最近：{'; '.join(parts)}"

        return f"前方：{'; '.join(parts)}"
        
    def generate_warning_text(self, obstacles: List[ObstacleInfo]) -> str:

        if not obstacles:
            return ""
        
        closest = obstacles[0]
        type_cn = {
            "stairs": "台阶",
            "curb": "路沿",
            "obstacle": "障碍物",
            "blind_path_broken": "盲道中断",
            "slope": "坡道"
        }.get(closest.type, "障碍物")
        
        return f"注意！{closest.direction}{closest.distance}米处有{type_cn}"
