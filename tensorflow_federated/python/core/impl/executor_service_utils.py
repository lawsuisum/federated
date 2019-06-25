# Lint as: python3
# Copyright 2019, The TensorFlow Federated Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""A set of utility methods for `executor_service.py` and its clients."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf

from google.protobuf import any_pb2

from tensorflow_federated.proto.v0 import executor_pb2
from tensorflow_federated.python.common_libs import py_typecheck
from tensorflow_federated.python.core.api import computation_types


def serialize_tensor_value(value, type_spec=None):
  """Serializes a tensor value into `executor_pb2.Value`.

  Args:
    value: A Numpy array or other object understood by `tf.make_tensor_proto`.
    type_spec: An optional type spec, a `tff.TensorType` or something
      convertible to it.

  Returns:
    An instance of `executor_pb2.Value` with the serialized content of `value`.

  Returns:
    TypeError: If the arguments are of the wrong types.
    ValueError: If the value is malformed.
  """
  if type_spec is not None:
    type_spec = computation_types.to_type(type_spec)
    py_typecheck.check_type(type_spec, computation_types.TensorType)
    tensor_proto = tf.make_tensor_proto(
        value, dtype=type_spec.dtype, shape=type_spec.shape, verify_shape=True)
  else:
    tensor_proto = tf.make_tensor_proto(value)
  any_pb = any_pb2.Any()
  any_pb.Pack(tensor_proto)
  return executor_pb2.Value(tensor=any_pb)


def deserialize_tensor_value(value_proto):
  """Deserializes a tensor value from `executor_pb2.Value`.

  Args:
    value_proto: An instance of `executor_pb2.Value`.

  Returns:
    A tuple `(value, type_spec)`, where `value` is a Numpy array that represents
    the deserialized value, and `type_spec` is an instance of `tff.TensorType`
    that represents its type.

  Returns:
    TypeError: If the arguments are of the wrong types.
    ValueError: If the value is malformed.
  """
  py_typecheck.check_type(value_proto, executor_pb2.Value)
  which_value = value_proto.WhichOneof('value')
  if which_value != 'tensor':
    raise ValueError('Not a tensor value: {}'.format(which_value))

  # TODO(b/134543154): Find some way of creating the `TensorProto` using a
  # proper public interface rather than creating a dummy value that we will
  # overwrite right away.
  tensor_proto = tf.make_tensor_proto(values=0)
  if not value_proto.tensor.Unpack(tensor_proto):
    raise ValueError('Unable to unpack the received tensor value.')

  tensor_value = tf.make_ndarray(tensor_proto)
  value_type = computation_types.TensorType(
      dtype=tf.DType(tensor_proto.dtype),
      shape=tf.TensorShape(tensor_proto.tensor_shape))

  return tensor_value, value_type