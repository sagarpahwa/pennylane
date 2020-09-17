# Copyright 2018-2020 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""This module contains an autograd implementation of the :class:`~.DefaultQubit`
reference plugin.
"""
from pennylane.operation import DiagonalOperation
from pennylane import numpy as np

from pennylane.devices import DefaultQubit
from pennylane.devices import autograd_ops


class DefaultQubitAutograd(DefaultQubit):
    """Simulator plugin based on ``"default.qubit"``, written using Autograd.

    **Short name:** ``default.qubit.autograd``

    This device provides a pure-state qubit simulator written using Autograd. As a result, it
    supports classical backpropagation as a means to compute the gradient. This can be faster than
    the parameter-shift rule for analytic quantum gradients when the number of parameters to be
    optimized is large.

    To use this device, you will need to install Autograd:

    .. code-block:: console

        pip install autograd

    **Example**

    The ``default.qubit.autograd`` is designed to be used with end-to-end classical backpropagation
    (``diff_method="backprop"``) with the Autograd interface. This is the default method of
    differentiation when creating a QNode with this device.

    Using this method, the created QNode is a 'white-box', and is
    tightly integrated with your Autograd computation:

    >>> dev = qml.device("default.qubit.autograd", wires=1)
    >>> @qml.qnode(dev, interface="autograd", diff_method="backprop")
    ... def circuit(x):
    ...     qml.RX(x[1], wires=0)
    ...     qml.Rot(x[0], x[1], x[2], wires=0)
    ...     return qml.expval(qml.PauliZ(0))
    >>> weights = np.array([0.2, 0.5, 0.1])
    >>> grad_fn = qml.grad(circuit)
    >>> print(grad_fn(weights))
    array([-2.2526717e-01 -1.0086454e+00  1.3877788e-17])

    There are a couple of things to keep in mind when using the ``"backprop"``
    differentiation method for QNodes:

    * You must use the ``"autograd"`` interface for classical backpropagation, as Autograd is
      used as the device backend.

    * Only exact expectation values, variances, and probabilities are differentiable.
      When instantiating the device with ``analytic=False``, differentiating QNode
      outputs will result in an error.

    Args:
        wires (int): the number of wires to initialize the device with
    """

    name = "Default qubit (Autograd) PennyLane plugin"
    short_name = "default.qubit.autograd"

    parametric_ops = {
        "PhaseShift": autograd_ops.PhaseShift,
        "RX": autograd_ops.RX,
        "RY": autograd_ops.RY,
        "RZ": autograd_ops.RZ,
        "Rot": autograd_ops.Rot,
        "CRX": autograd_ops.CRX,
        "CRY": autograd_ops.CRY,
        "CRZ": autograd_ops.CRZ,
    }

    C_DTYPE = np.complex128
    R_DTYPE = np.float64
    _asarray = staticmethod(np.tensor)
    _dot = staticmethod(np.dot)
    _abs = staticmethod(np.abs)
    _reduce_sum = staticmethod(lambda array, axes: np.sum(array, axis=tuple(axes)))
    _reshape = staticmethod(np.reshape)
    _flatten = staticmethod(lambda array: array.flatten())
    _gather = staticmethod(lambda array, indices: array[indices])
    _einsum = staticmethod(np.einsum)
    _cast = staticmethod(np.tensor)
    _transpose = staticmethod(np.transpose)
    _tensordot = staticmethod(np.tensordot)
    _conj = staticmethod(np.conj)
    _imag = staticmethod(np.imag)
    _roll = staticmethod(np.roll)
    _stack = staticmethod(np.stack)

    def __init__(self, wires, *, shots=1000, analytic=True):
        super().__init__(wires, shots=shots, analytic=analytic)

        # prevent using special apply methods for these gates due to slowdown in Autograd
        # implementation
        del self._apply_ops["PauliY"]
        del self._apply_ops["Hadamard"]
        del self._apply_ops["CZ"]

    @classmethod
    def capabilities(cls):
        capabilities = super().capabilities().copy()
        capabilities.update(
            passthru_interface="autograd",
            supports_reversible_diff=False,
        )
        return capabilities

    @staticmethod
    def _scatter(indices, array, new_dimensions):
        new_array = np.zeros(new_dimensions, dtype=array.dtype.type)
        new_array[indices] = array
        return new_array

    def _get_unitary_matrix(self, unitary):
        """Return the matrix representing a unitary operation.

        Args:
            unitary (~.Operation): a PennyLane unitary operation

        Returns:
            array[complex]: Returns a 2D matrix representation of
            the unitary in the computational basis, or, in the case of a diagonal unitary,
            a 1D array representing the matrix diagonal.
        """
        if unitary.name in self.parametric_ops:
            return self.parametric_ops[unitary.name](*unitary.parameters)

        if isinstance(unitary, DiagonalOperation):
            return unitary.eigvals

        return unitary.matrix
