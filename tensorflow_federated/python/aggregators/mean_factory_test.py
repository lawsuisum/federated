# Copyright 2020, The TensorFlow Federated Authors.
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

import collections
import math
from absl.testing import parameterized
import tensorflow as tf

from tensorflow_federated.python.aggregators import factory
from tensorflow_federated.python.aggregators import mean_factory
from tensorflow_federated.python.aggregators import test_utils as aggregators_test_utils
from tensorflow_federated.python.core.api import computation_types
from tensorflow_federated.python.core.api import placements
from tensorflow_federated.python.core.api import test_case
from tensorflow_federated.python.core.backends.native import execution_contexts
from tensorflow_federated.python.core.templates import aggregation_process
from tensorflow_federated.python.core.templates import measured_process

M_CONST = aggregators_test_utils.MEASUREMENT_CONSTANT

_test_struct_type = ((tf.float32, (2,)), tf.float64)


class MeanFactoryComputationTest(test_case.TestCase, parameterized.TestCase):

  @parameterized.named_parameters(
      ('float', tf.float32),
      ('struct', _test_struct_type),
  )
  def test_type_properties_unweighted(self, value_type):
    factory_ = mean_factory.MeanFactory()
    self.assertIsInstance(factory_, factory.UnweightedAggregationFactory)
    value_type = computation_types.to_type(value_type)
    process = factory_.create_unweighted(value_type)
    self.assertIsInstance(process, aggregation_process.AggregationProcess)

    param_value_type = computation_types.FederatedType(value_type,
                                                       placements.CLIENTS)
    result_value_type = computation_types.FederatedType(value_type,
                                                        placements.SERVER)
    expected_state_type = expected_measurements_type = computation_types.at_server(
        collections.OrderedDict(value_sum_process=()))

    expected_initialize_type = computation_types.FunctionType(
        parameter=None, result=expected_state_type)
    self.assertTrue(
        process.initialize.type_signature.is_equivalent_to(
            expected_initialize_type))

    expected_next_type = computation_types.FunctionType(
        parameter=collections.OrderedDict(
            state=expected_state_type, value=param_value_type),
        result=measured_process.MeasuredProcessOutput(
            expected_state_type, result_value_type, expected_measurements_type))
    self.assertTrue(
        process.next.type_signature.is_equivalent_to(expected_next_type))

  @parameterized.named_parameters(
      ('float_value_float32_weight', tf.float32, tf.float32),
      ('struct_value_float32_weight', _test_struct_type, tf.float32),
      ('float_value_float64_weight', tf.float32, tf.float64),
      ('struct_value_float64_weight', _test_struct_type, tf.float64),
      ('float_value_int32_weight', tf.float32, tf.int32),
      ('struct_value_int32_weight', _test_struct_type, tf.int32),
      ('float_value_int64_weight', tf.float32, tf.int64),
      ('struct_value_int64_weight', _test_struct_type, tf.int64),
  )
  def test_type_properties_weighted(self, value_type, weight_type):
    factory_ = mean_factory.MeanFactory()
    self.assertIsInstance(factory_, factory.WeightedAggregationFactory)
    value_type = computation_types.to_type(value_type)
    weight_type = computation_types.to_type(weight_type)
    process = factory_.create_weighted(value_type, weight_type)
    self.assertIsInstance(process, aggregation_process.AggregationProcess)

    param_value_type = computation_types.FederatedType(value_type,
                                                       placements.CLIENTS)
    result_value_type = computation_types.FederatedType(value_type,
                                                        placements.SERVER)
    expected_state_type = expected_measurements_type = computation_types.at_server(
        collections.OrderedDict(value_sum_process=(), weight_sum_process=()))

    expected_initialize_type = computation_types.FunctionType(
        parameter=None, result=expected_state_type)
    self.assertTrue(
        process.initialize.type_signature.is_equivalent_to(
            expected_initialize_type))

    expected_next_type = computation_types.FunctionType(
        parameter=collections.OrderedDict(
            state=expected_state_type,
            value=param_value_type,
            weight=computation_types.at_clients(weight_type)),
        result=measured_process.MeasuredProcessOutput(
            expected_state_type, result_value_type, expected_measurements_type))
    self.assertTrue(
        process.next.type_signature.is_equivalent_to(expected_next_type))

  @parameterized.named_parameters(
      ('float', tf.float32),
      ('struct', _test_struct_type),
  )
  def test_type_properties_with_inner_factory_unweighted(self, value_type):
    sum_factory = aggregators_test_utils.SumPlusOneFactory()
    factory_ = mean_factory.MeanFactory(value_sum_factory=sum_factory)
    self.assertIsInstance(factory_, factory.UnweightedAggregationFactory)
    value_type = computation_types.to_type(value_type)
    process = factory_.create_unweighted(value_type)
    self.assertIsInstance(process, aggregation_process.AggregationProcess)

    param_value_type = computation_types.FederatedType(value_type,
                                                       placements.CLIENTS)
    result_value_type = computation_types.FederatedType(value_type,
                                                        placements.SERVER)
    expected_state_type = expected_measurements_type = computation_types.FederatedType(
        collections.OrderedDict(value_sum_process=tf.int32), placements.SERVER)

    expected_initialize_type = computation_types.FunctionType(
        parameter=None, result=expected_state_type)
    self.assertTrue(
        process.initialize.type_signature.is_equivalent_to(
            expected_initialize_type))

    expected_next_type = computation_types.FunctionType(
        parameter=collections.OrderedDict(
            state=expected_state_type, value=param_value_type),
        result=measured_process.MeasuredProcessOutput(
            expected_state_type, result_value_type, expected_measurements_type))
    self.assertTrue(
        process.next.type_signature.is_equivalent_to(expected_next_type))

  @parameterized.named_parameters(
      ('float_value_float32_weight', tf.float32, tf.float32),
      ('struct_value_float32_weight', _test_struct_type, tf.float32),
      ('float_value_float64_weight', tf.float32, tf.float64),
      ('struct_value_float64_weight', _test_struct_type, tf.float64),
      ('float_value_int32_weight', tf.float32, tf.int32),
      ('struct_value_int32_weight', _test_struct_type, tf.int32),
      ('float_value_int64_weight', tf.float32, tf.int64),
      ('struct_value_int64_weight', _test_struct_type, tf.int64),
  )
  def test_type_properties_with_inner_factory_weighted(self, value_type,
                                                       weight_type):
    sum_factory = aggregators_test_utils.SumPlusOneFactory()
    factory_ = mean_factory.MeanFactory(
        value_sum_factory=sum_factory, weight_sum_factory=sum_factory)
    self.assertIsInstance(factory_, factory.WeightedAggregationFactory)
    value_type = computation_types.to_type(value_type)
    weight_type = computation_types.to_type(weight_type)
    process = factory_.create_weighted(value_type, weight_type)
    self.assertIsInstance(process, aggregation_process.AggregationProcess)

    param_value_type = computation_types.FederatedType(value_type,
                                                       placements.CLIENTS)
    result_value_type = computation_types.FederatedType(value_type,
                                                        placements.SERVER)
    expected_state_type = expected_measurements_type = computation_types.FederatedType(
        collections.OrderedDict(
            value_sum_process=tf.int32, weight_sum_process=tf.int32),
        placements.SERVER)

    expected_initialize_type = computation_types.FunctionType(
        parameter=None, result=expected_state_type)
    self.assertTrue(
        process.initialize.type_signature.is_equivalent_to(
            expected_initialize_type))

    expected_next_type = computation_types.FunctionType(
        parameter=collections.OrderedDict(
            state=expected_state_type,
            value=param_value_type,
            weight=computation_types.at_clients(weight_type)),
        result=measured_process.MeasuredProcessOutput(
            expected_state_type, result_value_type, expected_measurements_type))
    self.assertTrue(
        process.next.type_signature.is_equivalent_to(expected_next_type))

  @parameterized.named_parameters(
      ('federated_type',
       computation_types.FederatedType(tf.float32, placements.SERVER)),
      ('function_type', computation_types.FunctionType(None, ())),
      ('sequence_type', computation_types.SequenceType(tf.float32)))
  def test_incorrect_create_type_raises(self, wrong_type):
    factory_ = mean_factory.MeanFactory()
    correct_type = computation_types.to_type(tf.float32)
    with self.assertRaises(TypeError):
      factory_.create_unweighted(wrong_type)
    with self.assertRaises(TypeError):
      factory_.create_weighted(wrong_type, correct_type)
    with self.assertRaises(TypeError):
      factory_.create_weighted(correct_type, wrong_type)


class MeanFactoryExecutionTest(test_case.TestCase):

  def test_scalar_value_unweighted(self):
    factory_ = mean_factory.MeanFactory()
    value_type = computation_types.to_type(tf.float32)

    process = factory_.create_unweighted(value_type)
    expected_state = expected_measurements = collections.OrderedDict(
        value_sum_process=())

    state = process.initialize()
    self.assertAllEqual(expected_state, state)

    client_data = [1.0, 2.0, 3.0]
    output = process.next(state, client_data)
    self.assertAllClose(2.0, output.result)

    self.assertAllEqual(expected_state, output.state)
    self.assertEqual(expected_measurements, output.measurements)

  def test_scalar_value_weighted(self):
    factory_ = mean_factory.MeanFactory()
    value_type = computation_types.to_type(tf.float32)

    weight_type = computation_types.to_type(tf.float32)
    process = factory_.create_weighted(value_type, weight_type)
    expected_state = expected_measurements = collections.OrderedDict(
        value_sum_process=(), weight_sum_process=())

    state = process.initialize()
    self.assertAllEqual(expected_state, state)

    client_data = [1.0, 2.0, 3.0]
    weights = [3.0, 2.0, 1.0]
    output = process.next(state, client_data, weights)
    self.assertAllClose(10. / 6., output.result)

    self.assertAllEqual(expected_state, output.state)
    self.assertEqual(expected_measurements, output.measurements)

  def test_structure_value_unweighted(self):
    factory_ = mean_factory.MeanFactory()
    value_type = computation_types.to_type(_test_struct_type)
    process = factory_.create_unweighted(value_type)
    expected_state = expected_measurements = collections.OrderedDict(
        value_sum_process=())

    state = process.initialize()
    self.assertAllEqual(expected_state, state)

    client_data = [((1.0, 2.0), 3.0), ((2.0, 5.0), 4.0), ((3.0, 0.0), 5.0)]
    output = process.next(state, client_data)

    self.assertAllEqual(expected_state, output.state)
    self.assertAllClose(((2.0, 7 / 3), 4.0), output.result)
    self.assertEqual(expected_measurements, output.measurements)

  def test_structure_value_weighted(self):
    factory_ = mean_factory.MeanFactory()
    value_type = computation_types.to_type(_test_struct_type)
    weight_type = computation_types.to_type(tf.float32)
    process = factory_.create_weighted(value_type, weight_type)
    expected_state = expected_measurements = collections.OrderedDict(
        value_sum_process=(), weight_sum_process=())

    state = process.initialize()
    self.assertAllEqual(expected_state, state)

    client_data = [((1.0, 2.0), 3.0), ((2.0, 5.0), 4.0), ((3.0, 0.0), 5.0)]
    weights = [3.0, 2.0, 1.0]
    output = process.next(state, client_data, weights)
    self.assertAllEqual(expected_state, output.state)
    self.assertAllClose(((10. / 6., 16. / 6.), 22. / 6.), output.result)
    self.assertEqual(expected_measurements, output.measurements)

  def test_weight_arg(self):
    factory_ = mean_factory.MeanFactory()
    value_type = computation_types.to_type(tf.float32)
    weight_type = computation_types.to_type(tf.float32)
    process = factory_.create_weighted(value_type, weight_type)

    state = process.initialize()
    client_data = [1.0, 2.0, 3.0]
    weights = [1.0, 1.0, 1.0]
    self.assertEqual(2.0, process.next(state, client_data, weights).result)
    weights = [0.1, 0.1, 0.1]
    self.assertEqual(2.0, process.next(state, client_data, weights).result)
    weights = [6.0, 3.0, 1.0]
    self.assertEqual(1.5, process.next(state, client_data, weights).result)

  def test_weight_arg_all_zeros_nan_division(self):
    factory_ = mean_factory.MeanFactory(no_nan_division=False)
    value_type = computation_types.to_type(tf.float32)
    weight_type = computation_types.to_type(tf.float32)
    process = factory_.create_weighted(value_type, weight_type)

    state = process.initialize()
    client_data = [1.0, 2.0, 3.0]
    weights = [0.0, 0.0, 0.0]
    # Division by zero resulting in NaN/Inf *should* occur.
    self.assertFalse(
        math.isfinite(process.next(state, client_data, weights).result))

  def test_weight_arg_all_zeros_no_nan_division(self):
    factory_ = mean_factory.MeanFactory(no_nan_division=True)
    value_type = computation_types.to_type(tf.float32)
    weight_type = computation_types.to_type(tf.float32)
    process = factory_.create_weighted(value_type, weight_type)

    state = process.initialize()
    client_data = [1.0, 2.0, 3.0]
    weights = [0.0, 0.0, 0.0]
    # Division by zero resulting in NaN/Inf *should not* occur.
    self.assertEqual(0.0, process.next(state, client_data, weights).result)

  def test_inner_value_sum_factory_unweighted(self):
    sum_factory = aggregators_test_utils.SumPlusOneFactory()
    factory_ = mean_factory.MeanFactory(value_sum_factory=sum_factory)
    value_type = computation_types.to_type(tf.float32)
    process = factory_.create_unweighted(value_type)

    state = process.initialize()
    self.assertAllEqual(collections.OrderedDict(value_sum_process=0), state)

    client_data = [1.0, 2.0, 3.0]
    # Values will be summed to 7.0.
    output = process.next(state, client_data)
    self.assertAllEqual(
        collections.OrderedDict(value_sum_process=1), output.state)
    self.assertAllClose(7 / 3, output.result)
    self.assertEqual(
        collections.OrderedDict(value_sum_process=M_CONST), output.measurements)

  def test_inner_value_sum_factory_weighted(self):
    sum_factory = aggregators_test_utils.SumPlusOneFactory()
    factory_ = mean_factory.MeanFactory(value_sum_factory=sum_factory)
    value_type = computation_types.to_type(tf.float32)
    weight_type = computation_types.to_type(tf.float32)
    process = factory_.create_weighted(value_type, weight_type)

    state = process.initialize()
    self.assertAllEqual(
        collections.OrderedDict(value_sum_process=0, weight_sum_process=()),
        state)

    client_data = [1.0, 2.0, 3.0]
    weights = [3.0, 2.0, 1.0]
    # Weighted values will be summed to 11.0.
    output = process.next(state, client_data, weights)
    self.assertAllEqual(
        collections.OrderedDict(value_sum_process=1, weight_sum_process=()),
        output.state)
    self.assertAllClose(11 / 6, output.result)
    self.assertEqual(
        collections.OrderedDict(
            value_sum_process=M_CONST, weight_sum_process=()),
        output.measurements)

  def test_inner_weight_sum_factory(self):
    sum_factory = aggregators_test_utils.SumPlusOneFactory()
    factory_ = mean_factory.MeanFactory(weight_sum_factory=sum_factory)
    value_type = computation_types.to_type(tf.float32)
    weight_type = computation_types.to_type(tf.float32)
    process = factory_.create_weighted(value_type, weight_type)

    state = process.initialize()
    self.assertAllEqual(
        collections.OrderedDict(value_sum_process=(), weight_sum_process=0),
        state)

    client_data = [1.0, 2.0, 3.0]
    weights = [1.0, 1.0, 1.0]
    # Weights will be summed to 4.0.
    output = process.next(state, client_data, weights)
    self.assertAllEqual(
        collections.OrderedDict(value_sum_process=(), weight_sum_process=1),
        output.state)
    self.assertAllClose(1.5, output.result)
    self.assertEqual(
        collections.OrderedDict(
            value_sum_process=(), weight_sum_process=M_CONST),
        output.measurements)

  def test_inner_value_and_weight_sum_factory(self):
    sum_factory = aggregators_test_utils.SumPlusOneFactory()
    factory_ = mean_factory.MeanFactory(
        value_sum_factory=sum_factory, weight_sum_factory=sum_factory)
    value_type = computation_types.to_type(tf.float32)
    weight_type = computation_types.to_type(tf.float32)
    process = factory_.create_weighted(value_type, weight_type)

    state = process.initialize()
    self.assertAllEqual(
        collections.OrderedDict(value_sum_process=0, weight_sum_process=0),
        state)

    client_data = [1.0, 2.0, 3.0]
    weights = [1.0, 1.0, 1.0]
    # Weighted values will be summed to 7.0 and weights will be summed to 4.0.
    output = process.next(state, client_data, weights)
    self.assertAllEqual(
        collections.OrderedDict(value_sum_process=1, weight_sum_process=1),
        output.state)
    self.assertAllClose(7 / 4, output.result)
    self.assertEqual(
        collections.OrderedDict(
            value_sum_process=M_CONST, weight_sum_process=M_CONST),
        output.measurements)


if __name__ == '__main__':
  execution_contexts.set_local_execution_context()
  test_case.main()
