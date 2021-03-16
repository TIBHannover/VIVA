from tensorflow import keras


class NBatchLogger(keras.callbacks.Callback):
    """
    A Logger that log average performance per `display` steps.
    """

    def __init__(self, display):
        self.step = 0
        self.epoch = 0
        self.display = display

    def on_batch_end(self, batch, logs=None):
        self.step += 1
        if self.step % self.display == 0:
            print('Epoch: {}/{} step: {}/{} - loss {:.6f}'.format(self.epoch, self.params['epochs'], self.step,
                                                                  self.params['steps'], logs["loss"]))

    def on_epoch_begin(self, epoch, logs=None):
        self.epoch += 1

    def on_epoch_end(self, _, logs=None):
        print('Epoch: {}/{} - val loss {:.6f}, mAP {:.4f}\n'.format(self.epoch, self.params['epochs'], logs['val_loss'],
                                                                    logs['mean_average_precision']))
        self.step = 0

    def on_train_end(self, logs=None):
        self.epoch = 0
