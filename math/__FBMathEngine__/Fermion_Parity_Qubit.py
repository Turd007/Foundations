# FB-QENGINE-001: Subproject 1 – Fermion Parity-Based Qubit Schema

class FermionParityQubit:
    def __init__(self, initial_parity: int = 0):
        assert initial_parity in [0, 1], "Parity must be 0 or 1."
        self.parity = initial_parity

    def braid(self, external_quasiparticle: int):
        assert external_quasiparticle == 1, "Only one e/4 quasiparticle can braid at a time."
        self.parity ^= 1

    def measure(self):
        return self.parity

    def get_state_vector(self):
        return [+1] if self.parity == 0 else [-1]
