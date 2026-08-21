"""
Quantum Key Distribution (BB84) + Quantum One-Time Pad (QOTP) Encryption
--------------------------------------------------------------------------
This implements two real, published quantum-cryptography protocols, not a
"toy" reversible circuit demo:

1. BB84 (Bennett & Brassard, 1984) -- quantum key distribution.
   Alice and Bob generate a shared secret random bit string using quantum
   states. Security comes from a genuine physical principle: measuring a
   qubit in a basis different from how it was prepared disturbs it. A
   spot-check of a random sample of the sifted key reveals an elevated
   error rate whenever an eavesdropper (Eve) has intercepted and
   re-measured the qubits, so tampering is statistically detectable.

2. Quantum One-Time Pad, QOTP (Ambainis, Mosca, Tapp, de Wolf, 2000,
   "Private Quantum Channels"). Every qubit of the message is masked with
   a random Pauli operator X^a Z^b drawn from the secret key (2 key bits
   per qubit). If the key is truly random, kept secret, and used only
   once -- exactly the classical one-time-pad requirements -- the
   resulting ciphertext state is provably maximally mixed: an
   eavesdropper who intercepts it gains literally zero information about
   the plaintext, regardless of computing power (including a quantum
   computer). This is information-theoretic security, not "hard to
   break," and it is what makes this a real encryption scheme instead of
   a reversible-circuit party trick.

Why the earlier version wasn't real encryption
------------------------------------------------
The earlier script applied a FIXED, PUBLIC circuit and inverted it with
cipher.inverse(). Anyone reading the source could reproduce the exact
same inverse -- there was no secret. That's a valid demonstration of
quantum reversibility, but not encryption in the security sense. Here,
the mask applied to each qubit is derived from a secret key that only
Alice and Bob possess (via BB84), so decryption is impossible without it.

Important honesty note (please read this)
--------------------------------------------
This script SIMULATES both protocols on a classical machine using
Qiskit's exact statevector math -- it is not sending real photons over a
real optical/quantum channel. The protocol logic (bases, measurement
disturbance, Pauli masking, sifting, spot-checking) is exactly what a
real photonic BB84+QOTP deployment runs. But because everything happens
inside one Python process here, there is no physically separate,
untrusted channel for a real Eve to attack -- the "eavesdropper" is a
function we call ourselves to demonstrate detection. Treat this as a
correct reference implementation of the protocols' math and logic, not
as a deployed secure communication system. Real-world QKD requires
actual quantum hardware (single-photon sources/detectors or trapped
ions) and a physical channel between separately-trusted parties.

Requires: pip install qiskit numpy
"""

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
import numpy as np


# ============================================================
# PART 1: BB84 Quantum Key Distribution
# ============================================================

def bb84_prepare_qubit(bit: int, basis: int) -> QuantumCircuit:
    """
    Alice prepares one qubit encoding `bit` in `basis`.
    basis 0 = Z basis (computational: |0>, |1>)
    basis 1 = X basis (Hadamard: |+>, |->)
    """
    qc = QuantumCircuit(1)
    if bit == 1:
        qc.x(0)
    if basis == 1:
        qc.h(0)
    return qc


def bb84_measure(state: Statevector, basis: int, rng: np.random.Generator) -> int:
    """
    Measures a single-qubit state in the given basis and returns the
    classical outcome, sampled according to the true Born-rule
    probabilities -- a genuine quantum measurement, not a deterministic
    readout.
    """
    qc = QuantumCircuit(1)
    if basis == 1:
        qc.h(0)  # rotate the X-basis into the Z-basis before reading out
    measured_state = state.evolve(qc)
    probs = measured_state.probabilities()
    return int(rng.choice([0, 1], p=probs))


def bb84_key_exchange(n_raw_bits: int, eavesdrop: bool = False,
                       sample_fraction: float = 0.3, seed=None) -> dict:
    """
    Runs a full BB84 exchange. Returns a dict with:
      key                  -- shared secret bits after sifting + spot-check removal
      qber                 -- estimated quantum bit error rate from the public sample
      eavesdropper_detected -- True if qber exceeds the standard ~11% abort threshold
      sifted_bits, final_key_length -- bookkeeping
    """
    rng = np.random.default_rng(seed)

    alice_bits = rng.integers(0, 2, n_raw_bits).tolist()
    alice_bases = rng.integers(0, 2, n_raw_bits).tolist()

    sent_states = [Statevector.from_instruction(bb84_prepare_qubit(b, ba))
                   for b, ba in zip(alice_bits, alice_bases)]

    if eavesdrop:
        eve_bases = rng.integers(0, 2, n_raw_bits).tolist()
        resent_states = []
        for state, eb in zip(sent_states, eve_bases):
            outcome = bb84_measure(state, eb, rng)
            resent_states.append(Statevector.from_instruction(bb84_prepare_qubit(outcome, eb)))
        channel_states = resent_states
    else:
        channel_states = sent_states

    bob_bases = rng.integers(0, 2, n_raw_bits).tolist()
    bob_results = [bb84_measure(s, bb, rng) for s, bb in zip(channel_states, bob_bases)]

    sifted_alice, sifted_bob = [], []
    for a_bit, a_base, b_base, b_bit in zip(alice_bits, alice_bases, bob_bases, bob_results):
        if a_base == b_base:
            sifted_alice.append(a_bit)
            sifted_bob.append(b_bit)

    n_sift = len(sifted_alice)
    n_sample = max(1, int(n_sift * sample_fraction)) if n_sift else 0
    sample_idx = set(rng.choice(n_sift, size=n_sample, replace=False)) if n_sift else set()

    mismatches = sum(1 for i in sample_idx if sifted_alice[i] != sifted_bob[i])
    qber = mismatches / n_sample if n_sample else 0.0

    final_key = [sifted_alice[i] for i in range(n_sift) if i not in sample_idx]
    eavesdropper_detected = qber > 0.11  # standard BB84 abort threshold

    return {
        "key": final_key,
        "qber": qber,
        "eavesdropper_detected": eavesdropper_detected,
        "raw_bits_sent": n_raw_bits,
        "sifted_bits": n_sift,
        "final_key_length": len(final_key),
    }


# ============================================================
# PART 2: Quantum One-Time Pad message encryption
# ============================================================

def text_to_bits(text: str) -> list:
    return [int(b) for char in text for b in format(ord(char), "08b")]


def bits_to_text(bits: list) -> str:
    chars = []
    for i in range(0, len(bits), 8):
        byte = bits[i:i + 8]
        if len(byte) < 8:
            break
        char_code = int("".join(map(str, byte)), 2)
        chars.append(chr(char_code))
    return "".join(chars)


def int_to_qubit_ordered_bits(value: int, n_qubits: int) -> list:
    big_endian_str = format(value, f"0{n_qubits}b")
    return [int(b) for b in big_endian_str[::-1]]


def build_qotp_circuit(n_qubits: int, key_bits: list) -> QuantumCircuit:
    """
    Builds the Quantum One-Time Pad masking circuit. key_bits must have
    length 2 * n_qubits: for qubit i, key_bits[2i] controls an X (bit
    flip) and key_bits[2i+1] controls a Z (phase flip). Applying a random
    secret X^a Z^b independently to each qubit is the QOTP construction
    with the published security proof.
    """
    if len(key_bits) < 2 * n_qubits:
        raise ValueError(f"Need {2 * n_qubits} key bits, got {len(key_bits)}")
    qc = QuantumCircuit(n_qubits, name="qotp")
    for i in range(n_qubits):
        a = key_bits[2 * i]
        b = key_bits[2 * i + 1]
        if b == 1:
            qc.z(i)
        if a == 1:
            qc.x(i)
    return qc


def qotp_encrypt(plaintext: str, key_bits: list):
    """Encrypts plaintext using the Quantum One-Time Pad with the given key."""
    plain_bits = text_to_bits(plaintext)
    n_qubits = len(plain_bits)

    base_qc = QuantumCircuit(n_qubits)
    for i, bit in enumerate(plain_bits):
        if bit == 1:
            base_qc.x(i)
    initial_state = Statevector.from_instruction(base_qc)

    pad_circuit = build_qotp_circuit(n_qubits, key_bits)
    encrypted_state = initial_state.evolve(pad_circuit)
    return encrypted_state, pad_circuit, n_qubits


def qotp_decrypt(encrypted_state: Statevector, pad_circuit: QuantumCircuit, n_qubits: int):
    """Decrypts using the exact inverse of the pad circuit. Requires the same key."""
    inverse_circuit = pad_circuit.inverse()
    recovered_state = encrypted_state.evolve(inverse_circuit)
    probs = recovered_state.probabilities()
    measured_int = int(np.argmax(probs))
    confidence = probs[measured_int]
    recovered_bits = int_to_qubit_ordered_bits(measured_int, n_qubits)
    return bits_to_text(recovered_bits), confidence


def qotp_encrypt_message(plaintext: str, key_bits: list, chars_per_block: int = 2):
    """Blockwise QOTP so arbitrary-length messages don't blow up memory."""
    blocks = [plaintext[i:i + chars_per_block] for i in range(0, len(plaintext), chars_per_block)]
    encrypted_blocks = []
    key_cursor = 0
    for block in blocks:
        n_qubits_block = len(block) * 8
        needed = 2 * n_qubits_block
        block_key = key_bits[key_cursor: key_cursor + needed]
        if len(block_key) < needed:
            raise ValueError("Not enough key material for this message length.")
        key_cursor += needed
        enc_state, pad_circuit, n_qubits = qotp_encrypt(block, block_key)
        encrypted_blocks.append((enc_state, pad_circuit, n_qubits))
    return encrypted_blocks


def qotp_decrypt_message(encrypted_blocks) -> str:
    parts = []
    for enc_state, pad_circuit, n_qubits in encrypted_blocks:
        text, _ = qotp_decrypt(enc_state, pad_circuit, n_qubits)
        parts.append(text)
    return "".join(parts)


# ============================================================
# DEMO
# ============================================================

if __name__ == "__main__":
    message = "Hi Qiskit!"
    n_plain_bits = len(text_to_bits(message))
    key_bits_needed = 2 * n_plain_bits

    print("=== Step 1: BB84 Quantum Key Distribution ===")
    # Request extra raw qubits: sifting keeps ~50%, and the spot-check consumes more of those.
    raw_bits_to_send = key_bits_needed * 8

    print("\n-- Honest run (no eavesdropper) --")
    result = bb84_key_exchange(raw_bits_to_send, eavesdrop=False, seed=42)
    print(f"Raw qubits sent: {result['raw_bits_sent']}")
    print(f"Sifted bits: {result['sifted_bits']}")
    print(f"QBER (spot-check): {result['qber']:.4f}")
    print(f"Eavesdropper detected: {result['eavesdropper_detected']}")
    print(f"Final shared key length: {result['final_key_length']} bits")

    print("\n-- Run WITH an intercept-resend eavesdropper (Eve) --")
    eve_result = bb84_key_exchange(raw_bits_to_send, eavesdrop=True, seed=42)
    print(f"QBER (spot-check): {eve_result['qber']:.4f}  <- elevated because Eve disturbed the qubits")
    print(f"Eavesdropper detected: {eve_result['eavesdropper_detected']}")

    if result["final_key_length"] < key_bits_needed:
        raise RuntimeError("Not enough key bits generated; increase raw_bits_to_send.")

    shared_key = result["key"][:key_bits_needed]

    print("\n=== Step 2: Quantum One-Time Pad Encryption ===")
    print(f"Plaintext: '{message}'")
    encrypted_blocks = qotp_encrypt_message(message, shared_key, chars_per_block=2)
    print(f"Encrypted into {len(encrypted_blocks)} block(s) using the BB84-derived key")

    print("\n=== Step 3: Decryption (requires the same secret key) ===")
    recovered = qotp_decrypt_message(encrypted_blocks)
    print(f"Recovered: '{recovered}'")

    assert recovered == message, "Decryption mismatch!"
    print("\n[SUCCESS] BB84 key distribution + Quantum One-Time Pad round-trip verified.")

    print("\n--- What happens WITHOUT the correct key ---")
    wrong_key = (np.array(shared_key) ^ 1).tolist()  # flip every bit: simulates a wrong/guessed key
    wrong_blocks = qotp_encrypt_message(message, shared_key, chars_per_block=2)  # same ciphertext
    garbled_parts = []
    key_cursor = 0
    for (enc_state, _, n_qubits) in wrong_blocks:
        needed = 2 * n_qubits
        wrong_block_key = wrong_key[key_cursor: key_cursor + needed]
        key_cursor += needed
        wrong_pad = build_qotp_circuit(n_qubits, wrong_block_key)
        text, _ = qotp_decrypt(enc_state, wrong_pad, n_qubits)
        garbled_parts.append(text)
    print(f"Decrypting the SAME ciphertext with a WRONG key gives garbage: {repr(''.join(garbled_parts))}")