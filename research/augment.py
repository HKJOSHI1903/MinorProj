"""Training augmentation, run inside tf.data (CPU) whatever Keras backend trains the model.

standard  the app's current recipe: flips, rotation, zoom, contrast (kisan/disease/train.py)
robust    "quality-aware augmentation" (QAA): standard geometry plus the photo defects
          farmers' phones actually produce, in camera-pipeline order:
          exposure -> contrast/gamma -> white balance -> blur/low resolution -> noise -> JPEG.

Images enter and leave as float32 0..255, (H, W, 3). Motion blur, speckle and
salt-and-pepper noise are deliberately absent: research/degradations.py uses
them as corruptions the model has never seen.
"""

from __future__ import annotations

import math

import tensorflow as tf

# QAA ranges (the robustness sweeps test wider ranges than these, to measure extrapolation).
BRIGHTNESS = (0.25, 2.2)      # log-uniform exposure factor
CONTRAST = (0.4, 1.8)
GAMMA = (0.5, 2.0)
CAST = 0.25                   # red/blue gain shift
SATURATION = (0.6, 1.4)
NOISE_SIGMA = (0.0, 35.0)
BLUR_SIGMA = (0.3, 2.5)
LOW_RES_SIDE = (40, 200)
JPEG_QUALITY = (15, 95)
P_ANY = 0.7                   # 30% of photos stay clean, so clean accuracy is not traded away


def geometric(robust: bool):
    """A function applying the geometric layers one by one. Keras preprocessing layers
    switch to TensorFlow ops inside tf.data whatever the backend; a Sequential wrapper
    would not, so the layers are not wrapped in one."""
    from keras import layers

    steps = [layers.RandomFlip("horizontal_and_vertical", seed=1, dtype="float32"),
             layers.RandomRotation(0.15, fill_mode="reflect", seed=2, dtype="float32"),
             layers.RandomZoom(0.15, fill_mode="reflect", seed=3, dtype="float32")]
    if robust:
        steps.append(layers.RandomTranslation(0.1, 0.1, fill_mode="reflect", seed=4, dtype="float32"))
    else:
        steps.append(layers.RandomContrast(0.15, seed=4, dtype="float32"))

    def apply(image, training=True):
        for layer in steps:
            image = layer(image, training=training)
        return tf.cast(image, tf.float32)

    return apply


def _maybe(p, fn, image):
    return tf.cond(tf.random.uniform([]) < p, lambda: fn(image), lambda: image)


def _luma_mean(image):
    return tf.reduce_mean(0.299 * image[..., 0] + 0.587 * image[..., 1] + 0.114 * image[..., 2])


def _brightness(image):
    factor = tf.exp(tf.random.uniform([], math.log(BRIGHTNESS[0]), math.log(BRIGHTNESS[1])))
    return image * factor


def _contrast(image):
    mean = _luma_mean(image)
    return mean + tf.random.uniform([], *CONTRAST) * (image - mean)


def _gamma(image):
    g = tf.exp(tf.random.uniform([], math.log(GAMMA[0]), math.log(GAMMA[1])))
    return 255.0 * tf.pow(tf.clip_by_value(image, 0, 255) / 255.0, g)


def _color(image):
    k = tf.random.uniform([], -CAST, CAST)
    image = image * tf.stack([1 + k, 1.0, 1 - k])
    image = tf.image.adjust_saturation(tf.clip_by_value(image, 0, 255) / 255.0,
                                       tf.random.uniform([], *SATURATION)) * 255.0
    return image


def _gaussian_kernel(sigma, size: int = 15):
    x = tf.range(size, dtype=tf.float32) - (size - 1) / 2
    k = tf.exp(-(x ** 2) / (2.0 * sigma ** 2))
    return k / tf.reduce_sum(k)


def _blur(image):
    k = _gaussian_kernel(tf.random.uniform([], *BLUR_SIGMA))
    kx = tf.tile(tf.reshape(k, [1, -1, 1, 1]), [1, 1, 3, 1])
    ky = tf.tile(tf.reshape(k, [-1, 1, 1, 1]), [1, 1, 3, 1])
    x = tf.pad(image[None], [[0, 0], [7, 7], [7, 7], [0, 0]], mode="REFLECT")
    x = tf.nn.depthwise_conv2d(x, kx, [1, 1, 1, 1], "VALID")
    x = tf.nn.depthwise_conv2d(x, ky, [1, 1, 1, 1], "VALID")
    return x[0]


def _low_res(image):
    size = tf.shape(image)[:2]
    side = tf.random.uniform([], LOW_RES_SIDE[0], LOW_RES_SIDE[1] + 1, dtype=tf.int32)
    small = tf.image.resize(image, [side, side], method="area")
    return tf.image.resize(small, size, method="bilinear")


def _noise(image):
    sigma = tf.random.uniform([], *NOISE_SIGMA)
    return image + tf.random.normal(tf.shape(image), stddev=sigma)


def _jpeg(image):
    quality = tf.random.uniform([], JPEG_QUALITY[0], JPEG_QUALITY[1] + 1, dtype=tf.int32)
    out = tf.image.adjust_jpeg_quality(tf.clip_by_value(image, 0, 255) / 255.0, quality) * 255.0
    return tf.reshape(out, tf.shape(image))


def quality_aware(image):
    """Random photo defects, each with its own probability, applied to ~70% of photos."""
    def degrade(x):
        x = _maybe(0.5, _brightness, x)
        x = _maybe(0.4, _contrast, x)
        x = _maybe(0.2, _gamma, x)
        x = _maybe(0.3, _color, x)
        x = tf.clip_by_value(x, 0, 255)
        x = _maybe(0.2, _blur, x)
        x = _maybe(0.2, _low_res, x)
        x = _maybe(0.3, _noise, x)
        x = tf.clip_by_value(x, 0, 255)
        x = _maybe(0.25, _jpeg, x)
        return x

    image = tf.cast(image, tf.float32)
    out = _maybe(P_ANY, degrade, image)
    out = tf.clip_by_value(out, 0, 255)
    out.set_shape(image.shape)
    return out
