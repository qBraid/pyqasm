# Copyright 2025 qBraid
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# # Write the benchmarking functions here.
# # See "Writing benchmarks" in the asv docs for more information.


# class TimeSuite:
#     """
#     An example benchmark that times the performance of various kinds
#     of iterating over dictionaries in Python.
#     """

#     def setup(self):
#         self.d = {}
#         for x in range(500):
#             self.d[x] = None

#     def time_keys(self):
#         for key in self.d.keys():
#             pass

#     def time_values(self):
#         for value in self.d.values():
#             pass

#     def time_range(self):
#         d = self.d
#         for key in range(500):
#             d[key]


# class MemSuite:
#     def mem_list(self):
#         return [0] * 256
