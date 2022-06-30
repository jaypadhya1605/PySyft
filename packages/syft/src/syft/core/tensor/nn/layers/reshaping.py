# third party
import numpy as np

# relative
from ....common.serde.serializable import serializable
from ...autodp.phi_tensor import PhiTensor
from .base import Layer


@serializable(recursive_serde=True)
class Flatten(Layer):
    __attr_allowlist__ = ("outdim", "last_input_shape", "out_shape")

    def __init__(self, outdim=2):
        self.outdim = outdim
        if outdim < 1:
            raise ValueError("Dim must be >0, was %i", outdim)

        self.last_input_shape = None
        self.out_shape = None

    def connect_to(self, prev_layer):
        assert len(prev_layer.out_shape) > 2

        to_flatten = np.prod(prev_layer.out_shape[self.outdim - 1 :])
        flattened_shape = prev_layer.out_shape[: self.outdim - 1] + (to_flatten,)

        self.out_shape = flattened_shape

    def forward(self, input: PhiTensor, *args, **kwargs):
        self.last_input_shape = input.shape

        flattened_shape = input.shape[: self.outdim - 1] + (-1,)
        return input.reshape(flattened_shape)

    def backward(self, pre_grad: PhiTensor, *args, **kwargs):
        return pre_grad.reshape(self.last_input_shape)