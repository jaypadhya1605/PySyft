# third party
import numpy as np

# relative
from ...common.serde.serializable import serializable
from .utils import dp_maximum


@serializable(recursive_serde=True)
class Optimizer:
    """Abstract optimizer base class.

    Parameters
    ----------
    clip : float
        If smaller than 0, do not apply parameter clip.
    lr : float
        The learning rate controlling the size of update steps
    decay : float
        Decay parameter for the moving average. Must lie in [0, 1) where
        lower numbers means a shorter “memory”.
    lr_min : float
        When adapting step rates, do not move below this value. Default is 0.
    lr_max : float
        When adapting step rates, do not move above this value. Default is inf.
    """

    __attr_allowlist__ = ("lr", "clip", "decay", "lr_min", "lr_max", "iterations")

    def __init__(self, lr=0.001, clip=-1, decay=0.0, lr_min=0.0, lr_max=np.inf):
        self.lr = lr
        self.clip = clip
        self.decay = decay
        self.lr_min = lr_min
        self.lr_max = lr_max

        self.iterations = 0

    def update(self, params, grads):
        self.iterations += 1

        self.lr *= 1.0 / 1 + self.decay * self.iterations
        self.lr = np.clip(self.lr, self.lr_min, self.lr_max)

    def __str__(self):
        return self.__class__.__name__


@serializable(recursive_serde=True)
class Adamax(Optimizer):
    """
    Parameters
    ----------
    beta1 : float
        Exponential decay rate for the first moment estimates.
    beta2 : float
        Exponential decay rate for the second moment estimates.
    epsilon : float
        Constant for numerical stability.
    References
    ----------
    .. [1] Kingma, Diederik, and Jimmy Ba (2014):
           Adam: A Method for Stochastic Optimization.
           arXiv preprint arXiv:1412.6980.
    """

    __attr_allowlist__ = (
        "beta1",
        "beta2",
        "epsilon",
        "ms",
        "vs",
        "lr",
        "iterations",
    )

    def __init__(
        self,
        learning_rate: float = 0.001,
        beta1=0.9,
        beta2=0.999,
        epsilon=1e-8,
        *args,
        **kwargs
    ):
        super(Adamax, self).__init__(*args, **kwargs)

        self.beta1 = beta1
        self.beta2 = beta2
        self.epsilon = epsilon

        self.ms = None
        self.vs = None

    def update(self, layers):

        # init
        self.iterations += 1
        a_t = self.lr / (1 - np.power(self.beta1, self.iterations))

        params = []
        grads = []
        for layer in layers:
            params += layer.params
            grads += layer.grads

        if self.ms is None:
            self.ms = [np.zeros(p.shape) for p in params]
        if self.vs is None:
            self.vs = [np.zeros(p.shape) for p in params]

        idx = 0
        for layer in layers:
            new_params = []
            for p, g in zip(layer.params, layer.grads):
                m = self.ms[idx]
                v = self.vs[idx]
                m = g * (1 - self.beta1) + m * self.beta1
                v = dp_maximum(g.abs(), v * self.beta2)
                p = (m * (-1.0 / (v + self.epsilon)) * a_t) + p
                new_params.append(p)

                self.ms[idx] = m
                self.vs[idx] = v
                idx += 1
            if new_params:
                layer.params = new_params