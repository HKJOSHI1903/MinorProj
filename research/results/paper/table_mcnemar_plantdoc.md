**McNemar's test p-values on the PlantDoc test (* = significant at 0.05)**

| Model | MobileNetV2 (frozen) | MobileNetV2 (fine-tuned) | MobileNetV2 (fine-tuned) + QAA | EfficientNetV2-B0 (fine-tuned) + QAA | MobileNetV3-L (fine-tuned) + QAA | ResNet50V2 (fine-tuned) + QAA | DenseNet121 (fine-tuned) + QAA | EfficientNetV2-B0 (fine-tuned) + QAA + PlantDoc | Handcrafted + Random Forest | Handcrafted + SVM |
|---|---|---|---|---|---|---|---|---|---|---|
| MobileNetV2 (frozen) | – | 3.3e-01 | 5.3e-04* | 1.5e-02* | 6.6e-02 | 6.5e-01 | 8.8e-01 | 1.1e-15* | 3.9e-12* | 8.5e-13* |
| MobileNetV2 (fine-tuned) | 3.3e-01 | – | 7.2e-03* | 1.4e-01 | 4.0e-01 | 6.5e-01 | 4.5e-01 | 4.7e-14* | 1.8e-12* | 1.5e-14* |
| MobileNetV2 (fine-tuned) + QAA | 5.3e-04* | 7.2e-03* | – | 3.1e-01 | 5.2e-02 | 4.7e-04* | 2.8e-04* | 1.3e-10* | 4.4e-17* | 6.2e-19* |
| EfficientNetV2-B0 (fine-tuned) + QAA | 1.5e-02* | 1.4e-01 | 3.1e-01 | – | 4.6e-01 | 2.1e-02* | 4.1e-03* | 2.7e-13* | 7.4e-15* | 5.6e-17* |
| MobileNetV3-L (fine-tuned) + QAA | 6.6e-02 | 4.0e-01 | 5.2e-02 | 4.6e-01 | – | 1.1e-01 | 4.5e-02* | 2.7e-13* | 1.9e-14* | 2.7e-16* |
| ResNet50V2 (fine-tuned) + QAA | 6.5e-01 | 6.5e-01 | 4.7e-04* | 2.1e-02* | 1.1e-01 | – | 8.4e-01 | 1.2e-15* | 1.3e-11* | 1.1e-13* |
| DenseNet121 (fine-tuned) + QAA | 8.8e-01 | 4.5e-01 | 2.8e-04* | 4.1e-03* | 4.5e-02* | 8.4e-01 | – | 6.4e-17* | 1.7e-11* | 3.1e-13* |
| EfficientNetV2-B0 (fine-tuned) + QAA + PlantDoc | 1.1e-15* | 4.7e-14* | 1.3e-10* | 2.7e-13* | 2.7e-13* | 1.2e-15* | 6.4e-17* | – | 1.2e-29* | 1.8e-31* |
| Handcrafted + Random Forest | 3.9e-12* | 1.8e-12* | 4.4e-17* | 7.4e-15* | 1.9e-14* | 1.3e-11* | 1.7e-11* | 1.2e-29* | – | 5.8e-01 |
| Handcrafted + SVM | 8.5e-13* | 1.5e-14* | 6.2e-19* | 5.6e-17* | 2.7e-16* | 1.1e-13* | 3.1e-13* | 1.8e-31* | 5.8e-01 | – |
