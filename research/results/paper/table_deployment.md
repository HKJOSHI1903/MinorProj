**Deployment cost: model size, single-photo CPU latency and quantization**

| Model | Format | Size (MB) | CPU latency (ms/photo) | Accuracy % (50/class subset) | Agreement with float32 % |
|---|---|---|---|---|---|
| MobileNetV2 (frozen) | Keras float32 | 9.4 | 113.3 | 92.27 | 100.00 |
| MobileNetV2 (frozen) | TFLite float32 | 8.64 | 2.0 | 92.27 | 100.00 |
| MobileNetV2 (frozen) | TFLite float16 | 4.35 | 2.0 | 92.17 | 99.57 |
| MobileNetV2 (frozen) | TFLite dynamic int8 | 2.44 | 32.3 | 91.79 | 97.21 |
| MobileNetV2 (frozen) | TFLite full int8 | 2.63 | 2.2 | 91.09 | 94.96 |
| MobileNetV2 (fine-tuned) | Keras float32 | 9.4 | 119.4 | 98.66 | 100.00 |
| MobileNetV2 (fine-tuned) + QAA | Keras float32 | 9.4 | 120.5 | 98.44 | 100.00 |
| MobileNetV2 (fine-tuned) + QAA | TFLite float32 | 8.64 | 2.0 | 98.44 | 100.00 |
| MobileNetV2 (fine-tuned) + QAA | TFLite float16 | 4.35 | 2.0 | 98.50 | 99.95 |
| MobileNetV2 (fine-tuned) + QAA | TFLite dynamic int8 | 2.44 | 32.9 | 98.61 | 99.73 |
| MobileNetV2 (fine-tuned) + QAA | TFLite full int8 | 2.63 | 2.1 | 98.44 | 99.46 |
| EfficientNetV2-B0 (fine-tuned) + QAA | Keras float32 | 23.7 | 242.8 | 99.20 | 100.00 |
| MobileNetV3-L (fine-tuned) + QAA | Keras float32 | 12.2 | 140.6 | 99.52 | 100.00 |
| ResNet50V2 (fine-tuned) + QAA | Keras float32 | 90.8 | 204.0 | 98.34 | 100.00 |
| DenseNet121 (fine-tuned) + QAA | Keras float32 | 28.4 | 380.3 | 98.71 | 100.00 |
| EfficientNetV2-B0 (fine-tuned) + QAA + PlantDoc | Keras float32 | 23.7 | 242.6 | 99.46 | 100.00 |
| EfficientNetV2-B0 (fine-tuned) + QAA + PlantDoc | TFLite float32 | 22.52 | 5.5 | 99.46 | 100.00 |
| EfficientNetV2-B0 (fine-tuned) + QAA + PlantDoc | TFLite float16 | 11.33 | 5.8 | 99.46 | 100.00 |
| EfficientNetV2-B0 (fine-tuned) + QAA + PlantDoc | TFLite dynamic int8 | 6.34 | 12.5 | 99.36 | 99.89 |
| EfficientNetV2-B0 (fine-tuned) + QAA + PlantDoc | TFLite full int8 | 6.85 | 4.8 | 99.30 | 99.73 |
