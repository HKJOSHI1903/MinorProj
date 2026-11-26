**Temperature scaling fitted on the PlantVillage validation set (before → after): it fixes lab calibration but worsens field calibration**

| Model | Temperature | PV ECE | PV answered at 0.7 % | PV acc. when answered % | PlantDoc ECE | PlantDoc answered at 0.7 % | PlantDoc acc. when answered % |
|---|---|---|---|---|---|---|---|
| MobileNetV2 (frozen) | 0.505 | 0.150 → 0.013 | 71 → 91 | 98.8 → 96.4 | 0.163 → 0.403 | 14 → 47 | 47.1 → 35.5 |
| MobileNetV2 (fine-tuned) | 0.579 | 0.094 → 0.003 | 98 → 99 | 99.7 → 99.5 | 0.226 → 0.453 | 31 → 61 | 50.0 → 42.4 |
| MobileNetV2 (fine-tuned) + QAA | 0.560 | 0.099 → 0.003 | 96 → 99 | 99.6 → 99.2 | 0.188 → 0.393 | 31 → 66 | 52.1 → 43.9 |
| EfficientNetV2-B0 (fine-tuned) + QAA | 0.519 | 0.094 → 0.002 | 99 → 100 | 99.9 → 99.7 | 0.265 → 0.508 | 44 → 79 | 51.0 → 39.8 |
| MobileNetV3-L (fine-tuned) + QAA | 0.546 | 0.095 → 0.002 | 99 → 100 | 99.8 → 99.6 | 0.224 → 0.460 | 33 → 70 | 48.1 → 43.3 |
| ResNet50V2 (fine-tuned) + QAA | 0.539 | 0.095 → 0.004 | 95 → 99 | 99.7 → 98.9 | 0.253 → 0.492 | 30 → 64 | 46.5 → 35.3 |
| DenseNet121 (fine-tuned) + QAA | 0.499 | 0.101 → 0.002 | 95 → 99 | 99.8 → 99.3 | 0.202 → 0.478 | 21 → 61 | 55.1 → 35.4 |
| EfficientNetV2-B0 (fine-tuned) + QAA + PlantDoc | 0.547 | 0.095 → 0.002 | 99 → 100 | 99.9 → 99.7 | 0.136 → 0.260 | 65 → 83 | 74.3 → 68.0 |
