import base64
import io
from contextlib import asynccontextmanager

import numpy as np
from ai_edge_litert.interpreter import Interpreter
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel

# ASL Alphabet labels (29 classes)
CLASS_LABELS = [
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J",
    "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
    "U", "V", "W", "X", "Y", "Z", "del", "nothing", "space",
]

INPUT_SIZE = 128

# Global interpreter reference
interpreter: Interpreter | None = None
input_index: int = 0
output_index: int = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the TFLite model once at startup."""
    global interpreter, input_index, output_index

    interpreter = Interpreter(model_path="model/asl_alphabet_model_fp16.tflite")
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    input_index = input_details[0]["index"]
    output_index = output_details[0]["index"]

    print(f"✅ Model loaded — input shape: {input_details[0]['shape']}, "
          f"output shape: {output_details[0]['shape']}")
    yield


app = FastAPI(title="ASL Sign Language Recognition API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictRequest(BaseModel):
    image: str  # base64-encoded JPEG or PNG


class PredictResponse(BaseModel):
    prediction: str
    confidence: float


def preprocess_image(base64_str: str) -> np.ndarray:
    """Decode base64 image → resize to 128×128 → normalize to [0, 1] float32."""
    # Handle data URI prefix (e.g. "data:image/jpeg;base64,...")
    if "," in base64_str:
        base64_str = base64_str.split(",", 1)[1]

    img_bytes = base64.b64decode(base64_str)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img = img.resize((INPUT_SIZE, INPUT_SIZE), Image.BILINEAR)

    arr = np.array(img, dtype=np.float32) / 255.0
    return arr.reshape(1, INPUT_SIZE, INPUT_SIZE, 3)


@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest):
    """Run ASL alphabet inference on a single frame."""
    input_data = preprocess_image(req.image)

    interpreter.set_tensor(input_index, input_data)
    interpreter.invoke()

    output_data = interpreter.get_tensor(output_index)[0]  # shape (29,)

    predicted_idx = int(np.argmax(output_data))
    confidence = float(output_data[predicted_idx])

    return PredictResponse(
        prediction=CLASS_LABELS[predicted_idx],
        confidence=round(confidence, 4),
    )


@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": interpreter is not None}
