import math

def xgate(qc):
    qc.x(qc.qubits)  # Apply U gate on qubit 0
    return qc


def ugate(qc):
    theta = math.pi / 3  # angle of vector in ZX plane
    phi = 0  # angle of vector in XY plane
    lambd = 0
    qc.u(theta, phi, lambd, qc.qubits)  # Apply U gate on qubit 0
    return qc


def igate(qc):
    qc.id(qc.qubits)
    return qc


def hgate(qc):
    qc.h(qc.qubits)
    return qc
