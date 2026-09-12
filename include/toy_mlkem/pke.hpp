#pragma once

#include <vector>

#include "toy_mlkem/compress.hpp"
#include "toy_mlkem/params.hpp"

namespace toy {

using Bits = std::vector<int>;

struct Ciphertext {
    ModuleVector u;
    Poly v;
};

struct RawCiphertext {
    ModuleVector u;
    Poly v;
};

ModuleVector keygen(const Params& p, const Matrix& a, const ModuleVector& s, const ModuleVector& e);
RawCiphertext encrypt_raw(const Params& p, const Matrix& a, const ModuleVector& t,
                          const ModuleVector& y, const ModuleVector& e1,
                          const Poly& e2, const Bits& message);
Ciphertext compress_ciphertext(const Params& p, const RawCiphertext& raw);
Ciphertext encrypt(const Params& p, const Matrix& a, const ModuleVector& t,
                   const ModuleVector& y, const ModuleVector& e1,
                   const Poly& e2, const Bits& message);
Bits decrypt(const Params& p, const ModuleVector& s, const Ciphertext& ciphertext);
Bits decrypt_uncompressed(const Params& p, const ModuleVector& s, const RawCiphertext& ciphertext);
bool failure(const Bits& expected, const Bits& actual);
int signed_decoding_margin(int residue, int expected_bit, int q);
int minimum_margin(const Params& p, const ModuleVector& s, const Ciphertext& ciphertext,
                   const Bits& expected);

struct NoiseSupportBound {
    int ey{};
    int se1{};
    int e2{};
    int scu{};
    int cv{};
    int total{};
    int decoding_margin{};
    bool failure_impossible{};
};

NoiseSupportBound noise_support_bound(const Params& p);

} // namespace toy
