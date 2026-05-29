import gradio as gr
import numpy as np
import tensorflow as tf
import cv2
from PIL import Image

# 1. Configuration & Model Loading
SEG_MODEL_PATH = './model/unet/best_unet.keras'
CLS_MODEL_PATH = './model/mobilenetv2/best_mobilenetv2_model.keras'

# Load models with compile=False for faster loading (inference only)
print("Loading Segmentation Model...")
seg_model = tf.keras.models.load_model(SEG_MODEL_PATH, compile=False)
print("Loading Classification Model...")
cls_model = tf.keras.models.load_model(CLS_MODEL_PATH, compile=False)

# Constants
SEG_IMG_SIZE = (512, 512)
CLS_IMG_SIZE = (224, 224)

def combined_predict(input_img, progress=gr.Progress()):
    if input_img is None:
        return None, None, None

    # --- STEP 1: TB CLASSIFICATION ---
    progress(0.1, desc="Loading for TB Classifier...")
    # Preprocessing for Classification (MobileNetV2 expects 224x224 RGB)
    cls_img = cv2.resize(input_img, CLS_IMG_SIZE)
    if len(cls_img.shape) == 2: # if grayscale
        cls_img = cv2.cvtColor(cls_img, cv2.COLOR_GRAY2RGB)
    
    cls_input = cls_img.astype(np.float32) / 255.0
    cls_input = np.expand_dims(cls_input, axis=0)
    
    # Inference Classification
    cls_preds = cls_model.predict(cls_input, verbose=0)
    tb_prob = float(cls_preds[0][0])
    normal_prob = 1.0 - tb_prob
    
    # --- STEP 2: LUNG SEGMENTATION ---
    progress(0.5, desc="Loading for Lung Segmentation...")
    # Preprocessing for Segmentation (U-Net expects 512x512 Grayscale)
    if len(input_img.shape) == 3:
        seg_gray = cv2.cvtColor(input_img, cv2.COLOR_RGB2GRAY)
    else:
        seg_gray = input_img
        
    seg_resized = cv2.resize(seg_gray, SEG_IMG_SIZE)
    seg_input = seg_resized.astype(np.float32) / 255.0
    seg_input = np.expand_dims(seg_input, axis=(0, -1))
    
    # Inference Segmentation
    seg_preds = seg_model.predict(seg_input, verbose=0)
    mask = np.squeeze(seg_preds)
    binary_mask = (mask > 0.5).astype(np.uint8) * 255
    
    # Visualization Overlay
    original_rgb = cv2.resize(input_img, SEG_IMG_SIZE)
    if len(original_rgb.shape) == 2:
        original_rgb = cv2.cvtColor(original_rgb, cv2.COLOR_GRAY2RGB)
        
    colored_mask = np.zeros_like(original_rgb)
    colored_mask[:, :, 1] = binary_mask # Green channel for lungs
    
    overlay = cv2.addWeighted(original_rgb, 0.7, colored_mask, 0.3, 0)
    
    progress(1.0, desc="Finalizing Results")
    
    # Confidence Score Result
    confidence_results = {
        "Normal": normal_prob,
        "Tuberculosis": tb_prob
    }
    
    return confidence_results, binary_mask, overlay

# 2. Gradio Interface
with gr.Blocks(title="TB Detection & Lung Segmentation") as demo:
    gr.Markdown("# 🫁 Combined TB Analysis Tool")
    gr.Markdown("This tool provides both TB Classification (Confidence Score) and Lung Segmentation in one flow.")
    
    with gr.Row():
        with gr.Column():
            input_image = gr.Image(label="Input Chest X-ray")
            execute_btn = gr.Button("🚀 Execute Analysis", variant="primary")
            
        with gr.Column():
            gr.Markdown("### Analysis Results")
            confidence_out = gr.Label(label="TB Classification Score")
            with gr.Tabs():
                with gr.TabItem("Mask Overlay"):
                    overlay_out = gr.Image(label="Lung Segmentation Overlay")
                with gr.TabItem("Binary Mask"):
                    mask_out = gr.Image(label="Lung Segmentation Mask")

    # Flow: Click -> Classification -> Segmentation -> Output
    execute_btn.click(
        fn=combined_predict, 
        inputs=input_image, 
        outputs=[confidence_out, mask_out, overlay_out]
    )

if __name__ == "__main__":
    demo.launch()
