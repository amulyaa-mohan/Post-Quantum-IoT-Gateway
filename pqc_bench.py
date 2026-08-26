"""
PQC handshake + benchmark for the PQC-Resilient IoT Gateway.

Does two things:

1. HANDSHAKE DEMO -- runs one complete gateway session end to end:
   Kyber-768 (ML-KEM) key encapsulation -> HKDF-SHA256 session key
   -> Dilithium-3 (ML-DSA) signature on a telemetry packet
   -> AES-256-GCM encryption -> gateway decrypts and verifies.
   Includes a tamper test so you can show detection, not just success.

2. BENCHMARK -- times Kyber-768 and Dilithium-3 against RSA-2048 and
   ECDSA-P256 on the same machine, and reports wire sizes. These are the
   numbers that go on the "PQC vs Classical" slide.

Run:  pip install pqcrypto cryptography
      python pqc_bench.py

Note on naming: NIST standardised CRYSTALS-Kyber as ML-KEM (FIPS 203) and
CRYSTALS-Dilithium as ML-DSA (FIPS 204). Kyber-768 == ML-KEM-768,
Dilithium-3 == ML-DSA-65. Sizes below are the FIPS versions, which differ
slightly from the older round-3 CRYSTALS submissions.
"""

import json
import os
import statistics
import time

from pqcrypto.kem import ml_kem_768 as kyber768
from pqcrypto.sign import ml_dsa_65 as dilithium3

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

REPEATS = 100  # raise for tighter numbers; 100 is plenty for a review slide


def bench(fn, repeats=REPEATS):
    """Returns (median_ms, stdev_ms). Median resists scheduler noise better than mean."""
    samples = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000.0)
    return statistics.median(samples), statistics.pstdev(samples)


# ------------------------------------------------------------------
# PART 1 -- one full gateway session
# ------------------------------------------------------------------

def derive_session_key(shared_secret: bytes, device_id: str) -> bytes:
    """
    The Kyber shared secret is not used as an AES key directly. HKDF expands
    it into a keyed session secret bound to the device identity, so two
    devices never derive the same key from a colliding secret.
    """
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,                       # AES-256
        salt=None,
        info=f"pqc-iot-gateway|{device_id}".encode(),
    ).derive(shared_secret)


def run_handshake_demo():
    print("=" * 62)
    print("PART 1: Full PQC session -- device to gateway")
    print("=" * 62)

    # --- Gateway long-term KEM keypair (published to devices) ---
    gw_pk, gw_sk = kyber768.keygen()
    print(f"[gateway] Kyber-768 keypair generated "
          f"(pk {len(bytes(gw_pk))} B, sk {len(bytes(gw_sk))} B)")

    # --- Device long-term signing keypair (public key registered at gateway) ---
    dev_vk, dev_sk = dilithium3.keygen()
    print(f"[device ] Dilithium-3 keypair generated "
          f"(pk {len(bytes(dev_vk))} B)")

    # --- Handshake: device encapsulates against the gateway public key ---
    kem_ct, dev_secret = kyber768.encaps(gw_pk)
    gw_secret = kyber768.decaps(gw_sk, kem_ct)
    assert bytes(dev_secret) == bytes(gw_secret), "KEM shared secret mismatch"
    print(f"[both   ] Shared secret established, KEM ciphertext on wire: "
          f"{len(bytes(kem_ct))} B")

    device_id = "sensor-14"
    dev_key = derive_session_key(bytes(dev_secret), device_id)
    gw_key = derive_session_key(bytes(gw_secret), device_id)
    assert dev_key == gw_key
    print(f"[both   ] HKDF-SHA256 -> identical AES-256 session key "
          f"({dev_key.hex()[:16]}...)")

    # --- Telemetry packet: sign, then encrypt ---
    payload = json.dumps({
        "device_id": device_id,
        "ts": 1756080000,
        "temperature_c": 28.4,
        "humidity_pct": 61.2,
        "pressure_hpa": 1008.7,
    }, separators=(",", ":")).encode()

    signature = dilithium3.sign(dev_sk, payload)
    signed_packet = json.dumps({
        "payload": payload.decode(),
        "sig": bytes(signature).hex(),
    }).encode()

    nonce = os.urandom(12)
    ciphertext = AESGCM(dev_key).encrypt(nonce, signed_packet, None)
    print(f"[device ] Signed ({len(bytes(signature))} B sig) + AES-256-GCM "
          f"encrypted -> {len(nonce) + len(ciphertext)} B on wire")

    # --- Gateway side: decrypt, then verify ---
    recovered = json.loads(AESGCM(gw_key).decrypt(nonce, ciphertext, None))
    ok = dilithium3.verify(dev_vk, recovered["payload"].encode(),
                           bytes.fromhex(recovered["sig"]))
    print(f"[gateway] Decrypted OK, Dilithium signature valid: "
          f"{ok is None or ok is True}")
    print(f"[gateway] Telemetry accepted -> drift engine: "
          f"{json.loads(recovered['payload'])['temperature_c']} C")

    # --- Tamper test: flip one byte of the payload, keep the signature ---
    forged = json.loads(recovered["payload"])
    forged["temperature_c"] = 95.0            # attacker spoofs a reading
    forged_bytes = json.dumps(forged, separators=(",", ":")).encode()
    try:
        dilithium3.verify(dev_vk, forged_bytes, bytes.fromhex(recovered["sig"]))
        print("[gateway] TAMPER NOT DETECTED -- this should never print")
    except Exception:
        print("[gateway] Tampered packet REJECTED: signature verification failed")
        print("          -> packet dropped, trust score penalised, event logged")


# ------------------------------------------------------------------
# PART 2 -- PQC vs classical benchmark
# ------------------------------------------------------------------

def run_benchmark():
    print()
    print("=" * 62)
    print(f"PART 2: PQC vs classical  (median of {REPEATS} runs, this machine)")
    print("=" * 62)

    message = os.urandom(256)  # stand-in for a telemetry packet

    # --- Kyber-768 ---
    k_pk, k_sk = kyber768.keygen()
    k_ct, _ = kyber768.encaps(k_pk)
    kyber_keygen = bench(lambda: kyber768.keygen())
    kyber_encaps = bench(lambda: kyber768.encaps(k_pk))
    kyber_decaps = bench(lambda: kyber768.decaps(k_sk, k_ct))

    # --- Dilithium-3 ---
    d_vk, d_sk = dilithium3.keygen()
    d_sig = dilithium3.sign(d_sk, message)
    dil_keygen = bench(lambda: dilithium3.keygen())
    dil_sign = bench(lambda: dilithium3.sign(d_sk, message))
    dil_verify = bench(lambda: dilithium3.verify(d_vk, message, d_sig))

    # --- RSA-2048 (classical baseline; keygen is slow, so fewer repeats) ---
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_pad = padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                          salt_length=padding.PSS.MAX_LENGTH)
    rsa_sig = rsa_key.sign(message, rsa_pad, hashes.SHA256())
    rsa_keygen = bench(
        lambda: rsa.generate_private_key(public_exponent=65537, key_size=2048),
        repeats=5)
    rsa_sign = bench(lambda: rsa_key.sign(message, rsa_pad, hashes.SHA256()))
    rsa_verify = bench(
        lambda: rsa_key.public_key().verify(rsa_sig, message, rsa_pad,
                                            hashes.SHA256()))
    rsa_pk_size = len(rsa_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo))

    # --- ECDSA P-256 ---
    ec_key = ec.generate_private_key(ec.SECP256R1())
    ec_sig = ec_key.sign(message, ec.ECDSA(hashes.SHA256()))
    ec_keygen = bench(lambda: ec.generate_private_key(ec.SECP256R1()))
    ec_sign = bench(lambda: ec_key.sign(message, ec.ECDSA(hashes.SHA256())))
    ec_verify = bench(
        lambda: ec_key.public_key().verify(ec_sig, message,
                                           ec.ECDSA(hashes.SHA256())))
    ec_pk_size = len(ec_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo))

    def row(name, keygen, op_a, op_b, pk, wire, quantum_safe):
        print(f"{name:<22}{keygen[0]:>10.3f}{op_a[0]:>11.3f}{op_b[0]:>11.3f}"
              f"{pk:>9}{wire:>10}   {quantum_safe}")

    print()
    print("KEY EXCHANGE / ENCAPSULATION")
    print(f"{'Scheme':<22}{'keygen ms':>10}{'encaps ms':>11}{'decaps ms':>11}"
          f"{'pk B':>9}{'ct B':>10}   Quantum-safe")
    print("-" * 84)
    row("ML-KEM (Kyber-768)", kyber_keygen, kyber_encaps, kyber_decaps,
        len(bytes(k_pk)), len(bytes(k_ct)), "YES")
    print()
    print("DIGITAL SIGNATURES")
    print(f"{'Scheme':<22}{'keygen ms':>10}{'sign ms':>11}{'verify ms':>11}"
          f"{'pk B':>9}{'sig B':>10}   Quantum-safe")
    print("-" * 84)
    row("ML-DSA (Dilithium-3)", dil_keygen, dil_sign, dil_verify,
        len(bytes(d_vk)), len(bytes(d_sig)), "YES")
    row("RSA-2048 (PSS)", rsa_keygen, rsa_sign, rsa_verify,
        rsa_pk_size, len(rsa_sig), "no  (Shor)")
    row("ECDSA P-256", ec_keygen, ec_sign, ec_verify,
        ec_pk_size, len(ec_sig), "no  (Shor)")

    print()
    print("Read this off the table on the slide:")
    print(f"  - Wire cost is the headline. A Dilithium-3 signature is "
          f"{len(bytes(d_sig))} B vs {len(ec_sig)} B for ECDSA P-256 "
          f"(~{len(bytes(d_sig))/len(ec_sig):.0f}x)")
    print(f"    and {len(rsa_sig)} B for RSA-2048 "
          f"(~{len(bytes(d_sig))/len(rsa_sig):.0f}x). On a constrained node the")
    print("    bandwidth and MTU impact bites harder than the CPU time.")
    print(f"  - Kyber-768 is cheap on CPU: keygen {kyber_keygen[0]:.3f} ms, "
          f"encaps {kyber_encaps[0]:.3f} ms,")
    print(f"    decaps {kyber_decaps[0]:.3f} ms -- vs {rsa_keygen[0]:.0f} ms "
          "for a single RSA-2048 keygen.")
    print(f"  - Dilithium verify is fast ({dil_verify[0]:.3f} ms), which is what "
          "the gateway does per")
    print("    packet. Signing happens on the device, once per packet.")
    print()
    print("  CAVEAT -- state this if you put timings on a slide:")
    print(f"    Dilithium sign measures {dil_sign[0]:.2f} ms here. That is a "
          "portable reference")
    print("    build with no AVX2 acceleration, and ML-DSA signing uses "
          "rejection sampling,")
    print("    so it is variable-time by construction. An AVX2 liboqs build is "
          "roughly an")
    print("    order of magnitude faster. Present SIZES as hard numbers and "
          "TIMINGS as")
    print("    build-specific, or re-run this on the liboqs toolchain before "
          "quoting them.")


if __name__ == "__main__":
    run_handshake_demo()
    run_benchmark()
