from braket.circuits import Circuit
from braket.devices import LocalSimulator

circuit = Circuit().h(0).cnot(0, 1)

device = LocalSimulator()
task = device.run(circuit, shots=0)
result = task.result()

print(result.measurement_counts)

# import cirq

# # Create two qubits
# q0, q1 = cirq.LineQubit.range(2)

# # Create a circuit
# circuit = cirq.Circuit(
#     cirq.H(q0),  # Hadamard gate on q0
#     cirq.CNOT(q0, q1),  # CNOT gate with q0 as control and q1 as target
#     cirq.measure(q0, q1, key='result')  # Measure both qubits
# )


# # Create a simulator
# simulator = cirq.Simulator(seed=2)

# # Run the circuit and get results
# result = simulator.run(circuit, repetitions=0)

# # Print the measurement results
# print(result.histogram(key='result'))
