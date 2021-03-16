import tensorflow as tf
import tensorflow.keras.backend as K


def focal_crossentropy(
        y_true,
        y_pred,
        alpha=0.25,
        gamma=2.0,
        from_logits: bool = False):
    y_pred = tf.convert_to_tensor(y_pred)
    y_true = tf.convert_to_tensor(y_true, dtype=y_pred.dtype)

    if from_logits:
        pred_prob = tf.sigmoid(y_pred)
    else:
        pred_prob = y_pred

    # Get the cross_entropy for each entry. ignore where label is -1
    ce = - y_true * 0.5 * (y_true + 1) * tf.math.log(pred_prob) \
         - (1 - y_true) * (y_true + 1) * tf.math.log(1 - pred_prob)

    p_t = (y_true * 0.5 * (y_true + 1) * pred_prob) + \
          ((1 - y_true) * (y_true + 1) * (1 - pred_prob))
    alpha_factor = 1.0
    modulating_factor = 1.0

    if alpha:
        alpha = tf.convert_to_tensor(alpha, dtype=K.floatx())
        alpha_factor = y_true * 0.5 * (y_true + 1) * alpha \
                       + (1 - y_true) * (y_true + 1) * (1 - alpha)
    if gamma:
        gamma = tf.convert_to_tensor(gamma, dtype=K.floatx())
        modulating_factor = tf.pow((1.0 - p_t), gamma)

    return tf.reduce_sum(alpha_factor * modulating_factor * ce, axis=-1)
