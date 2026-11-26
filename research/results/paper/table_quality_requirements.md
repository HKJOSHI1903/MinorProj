Limit = where accuracy falls more than 5 percentage points below clean.

| Degradation | E8_best_ft_qaa_plantdoc | E1_mnv2_frozen_std | E2_mnv2_ft_std | E3_mnv2_ft_qaa | E4_effv2b0_ft_qaa |
|---|---|---|---|---|---|
| brightness_high | 2.89 -> brightness 236 | 1.76 -> brightness 201 | 1.58 -> brightness 188 | 2.58 -> brightness 231 | 2.94 -> brightness 237 |
| brightness_high_overexposed | 2.89 -> overexposed 0.676 | 1.76 -> overexposed 0.293 | 1.58 -> overexposed 0.163 | 2.58 -> overexposed 0.61 | 2.94 -> overexposed 0.687 |
| brightness_low | 0.1 (whole range ok) -> brightness 12.3 | 0.57 -> brightness 69.9 | 0.598 -> brightness 73.3 | 0.1 (whole range ok) -> brightness 12.3 | 0.1 (whole range ok) -> brightness 12.3 |
| brightness_low_underexposed | 0.1 (whole range ok) -> underexposed 0.0505 | 0.57 -> underexposed 0 | 0.598 -> underexposed 0 | 0.1 (whole range ok) -> underexposed 0.0505 | 0.1 (whole range ok) -> underexposed 0.0505 |
| color_cast_high | 0.5 (whole range ok) | 0.288 | 0.215 | 0.5 (whole range ok) | 0.5 (whole range ok) |
| color_cast_low | -0.5 (whole range ok) | -0.226 | -0.191 | -0.5 (whole range ok) | -0.5 (whole range ok) |
| contrast_low | 0.15 -> contrast 6.03 | 0.591 -> contrast 23.8 | 0.661 -> contrast 26.6 | 0.178 -> contrast 7.17 | 0.1 (whole range ok) -> contrast 4.03 |
| gamma_high_brightness | 4 (whole range ok) -> brightness 22.4 | 2.23 -> brightness 58.5 | 2.62 -> brightness 46.6 | 4 (whole range ok) -> brightness 22.4 | 4 (whole range ok) -> brightness 22.4 |
| gamma_low_brightness | 0.3 (whole range ok) -> brightness 201 | 0.486 -> brightness 175 | 0.49 -> brightness 175 | 0.3 (whole range ok) -> brightness 201 | 0.3 (whole range ok) -> brightness 201 |
| gaussian_blur_high_sharpness | 4.35 -> sharpness 1.07 | 1.19 -> sharpness 25.4 | 1.06 -> sharpness 31.7 | 4.09 -> sharpness 1.14 | 4.58 -> sharpness 1.01 |
| gaussian_noise_high | 72.8 -> noise 63.8 | 5.98 -> noise 7.67 | 11.1 -> noise 12.1 | 51.2 -> noise 48.4 | 80 (whole range ok) -> noise 68.6 |
| jpeg_low | 9.55 | 41.4 | 24.1 | 9.97 | 9.1 |
| motion_blur_high_sharpness | 15.2 -> sharpness 27.1 | 3.31 -> sharpness 152 | 4.39 -> sharpness 111 | 11.3 -> sharpness 37.3 | 19.2 -> sharpness 21.2 |
| resolution_low | 29.5 | 90.6 | 95.5 | 36.8 | 27.9 |
| salt_pepper_high_noise | 0.131 -> noise 42.6 | 0.0014 -> noise 4.59 | 0.00947 -> noise 7.61 | 0.0262 -> noise 13.7 | 0.14 -> noise 44.7 |
| speckle_high_noise | 0.5 (whole range ok) -> noise 68.8 | 0.00338 -> noise 7.09 | 0.0112 -> noise 13.6 | 0.185 -> noise 47.7 | 0.5 (whole range ok) -> noise 68.8 |
