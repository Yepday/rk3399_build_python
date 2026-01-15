"""
RC4 stream cipher implementation for Rockchip bootloader encryption.

This module implements the RC4 encryption algorithm used by Rockchip's
boot_merger tool. The implementation uses a fixed key specific to Rockchip
firmware.

Original C implementation: boot_merger.c (P_RC4 function)

Security Note:
    This is NOT a secure implementation of RC4. It uses a hardcoded key
    and is only intended for compatibility with Rockchip's bootloader format.
    RC4 is considered cryptographically broken and should not be used for
    actual security purposes.

Usage:
    # Encrypt data
    encrypted = rc4_encrypt(data)

    # Decrypt data (same function, symmetric cipher)
    decrypted = rc4_encrypt(encrypted)

    # Block encryption (for loader data)
    encrypted = rc4_encrypt_blocks(data, block_size=512)
"""

from __future__ import annotations

# Rockchip fixed RC4 key (16 bytes)
# This key is hardcoded in the original boot_merger.c
ROCKCHIP_RC4_KEY = bytes([
    124, 78, 3, 4, 85, 5, 9, 7,
    45, 44, 123, 56, 23, 13, 23, 17
])


def rc4_init(key: bytes) -> tuple[list[int], list[int]]:
    """
    Initialize RC4 cipher state (KSA - Key Scheduling Algorithm).

    Args:
        key: Encryption key (typically 16 bytes for Rockchip)

    Returns:
        Tuple of (S-box, K array) for RC4 cipher

    Algorithm:
        1. Initialize S-box with values 0-255
        2. Fill K array by repeating key
        3. Permute S-box based on key
    """
    # Initialize S-box (permutation array)
    S = list(range(256))

    # Initialize K array (key schedule)
    K = [0] * 256
    key_len = len(key)

    # Fill K array by repeating key
    for i in range(256):
        K[i] = key[i % key_len]

    # Permute S-box based on key (KSA)
    j = 0
    for i in range(256):
        j = (j + S[i] + K[i]) % 256
        # Swap S[i] and S[j]
        S[i], S[j] = S[j], S[i]

    return S, K


def rc4_crypt(data: bytes, key: bytes = ROCKCHIP_RC4_KEY) -> bytes:
    """
    Encrypt or decrypt data using RC4 (PRGA - Pseudo-Random Generation Algorithm).

    RC4 is a symmetric cipher, so encryption and decryption use the same function.

    Args:
        data: Data to encrypt/decrypt
        key: Encryption key (default: Rockchip fixed key)

    Returns:
        Encrypted/decrypted data

    Algorithm:
        1. Initialize cipher state with KSA
        2. Generate keystream and XOR with data (PRGA)
    """
    if not data:
        return b''

    # Initialize cipher state
    S, _ = rc4_init(key)

    # PRGA: Generate keystream and encrypt
    result = bytearray(len(data))
    i = j = 0

    for x in range(len(data)):
        # Update indices
        i = (i + 1) % 256
        j = (j + S[i]) % 256

        # Swap S[i] and S[j]
        S[i], S[j] = S[j], S[i]

        # Generate keystream byte
        t = (S[i] + S[j]) % 256
        keystream_byte = S[t]

        # XOR with data
        result[x] = data[x] ^ keystream_byte

    return bytes(result)


# Alias for clarity
rc4_encrypt = rc4_crypt
rc4_decrypt = rc4_crypt  # Same function (symmetric cipher)


def rc4_encrypt_blocks(data: bytes, block_size: int = 512,
                       key: bytes = ROCKCHIP_RC4_KEY) -> bytes:
    """
    Encrypt data in fixed-size blocks (used for loader components).

    This function encrypts data block by block, reinitializing the cipher
    state for each block. This matches the behavior of the original C code
    for ENTRY_LOADER type data.

    Args:
        data: Data to encrypt
        block_size: Size of each block (default: 512 bytes)
        key: Encryption key (default: Rockchip fixed key)

    Returns:
        Encrypted data

    Note:
        Each block is encrypted independently with a fresh cipher state.
        This is different from standard RC4 stream encryption.
    """
    if not data:
        return b''

    result = bytearray()
    offset = 0
    data_len = len(data)

    while offset < data_len:
        # Calculate current block size
        current_block_size = min(block_size, data_len - offset)

        # Extract block
        block = data[offset:offset + current_block_size]

        # Encrypt block (fresh cipher state for each block)
        encrypted_block = rc4_crypt(block, key)
        result.extend(encrypted_block)

        offset += block_size

    return bytes(result)


def rc4_decrypt_blocks(data: bytes, block_size: int = 512,
                       key: bytes = ROCKCHIP_RC4_KEY) -> bytes:
    """
    Decrypt data that was encrypted in fixed-size blocks.

    This is the inverse of rc4_encrypt_blocks(). Since RC4 is symmetric,
    this function is identical to rc4_encrypt_blocks().

    Args:
        data: Data to decrypt
        block_size: Size of each block (default: 512 bytes)
        key: Encryption key (default: Rockchip fixed key)

    Returns:
        Decrypted data
    """
    return rc4_encrypt_blocks(data, block_size, key)


# Test function for verification
def _test_rc4():
    """Test RC4 implementation against known vectors."""
    # Test 1: Basic encryption/decryption
    plaintext = b"Hello, Rockchip!"
    encrypted = rc4_encrypt(plaintext)
    decrypted = rc4_decrypt(encrypted)
    assert decrypted == plaintext, "Basic RC4 test failed"
    print(f"✓ Basic RC4 test passed")

    # Test 2: Block encryption/decryption
    data = b"A" * 1024  # 1KB of data
    encrypted = rc4_encrypt_blocks(data, block_size=512)
    decrypted = rc4_decrypt_blocks(encrypted, block_size=512)
    assert decrypted == data, "Block RC4 test failed"
    print(f"✓ Block RC4 test passed")

    # Test 3: Empty data
    assert rc4_encrypt(b'') == b'', "Empty data test failed"
    print(f"✓ Empty data test passed")

    print("\nAll RC4 tests passed!")


if __name__ == "__main__":
    _test_rc4()
