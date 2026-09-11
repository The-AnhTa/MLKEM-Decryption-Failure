#include "toy_mlkem/pke.hpp"

#include <algorithm>
#include <limits>
#include <stdexcept>

namespace toy {

ModuleVector keygen(const Params& p, const Matrix& a, const ModuleVector& s, const ModuleVector& e) {
    return mat_vec(a, s, e, p.q);
}

RawCiphertext encrypt_raw(const Params& p, const Matrix& a, const ModuleVector& t,
                          const ModuleVector& y, const ModuleVector& e1,
                          const Poly& e2, const Bits& message) {
    if (message.size() != p.n || e2.size() != p.n) throw std::invalid_argument("message or e2 length mismatch");
    RawCiphertext out;
    out.u = transpose_mat_vec(a, y, e1, p.q);
    out.v = add(dot(t, y, p.q), e2, p.q);
    for (std::size_t i = 0; i < p.n; ++i) {
        if (message[i] != 0 && message[i] != 1) throw std::invalid_argument("message must contain bits");
        out.v[i] = mod_q(out.v[i] + decompress_coeff(message[i], 1, p.q), p.q);
    }
    return out;
}

Ciphertext compress_ciphertext(const Params& p, const RawCiphertext& raw) {
    Ciphertext out;
    out.u.reserve(raw.u.size());
    for (const auto& poly : raw.u) out.u.push_back(compress_poly(poly, p.du, p.q));
    out.v = compress_poly(raw.v, p.dv, p.q);
    return out;
}

Ciphertext encrypt(const Params& p, const Matrix& a, const ModuleVector& t,
                   const ModuleVector& y, const ModuleVector& e1,
                   const Poly& e2, const Bits& message) {
    return compress_ciphertext(p, encrypt_raw(p, a, t, y, e1, e2, message));
}

static Bits decode_from_reconstructed(const Params& p, const ModuleVector& s,
                                      const ModuleVector& reconstructed_u, const Poly& reconstructed_v) {
    const Poly w = sub(reconstructed_v, dot(s, reconstructed_u, p.q), p.q);
    Bits out(p.n);
    for (std::size_t i = 0; i < p.n; ++i) out[i] = compress_coeff(w[i], 1, p.q);
    return out;
}

Bits decrypt(const Params& p, const ModuleVector& s, const Ciphertext& ciphertext) {
    ModuleVector uhat;
    uhat.reserve(ciphertext.u.size());
    for (const auto& poly : ciphertext.u) uhat.push_back(decompress_poly(poly, p.du, p.q));
    return decode_from_reconstructed(p, s, uhat, decompress_poly(ciphertext.v, p.dv, p.q));
}

Bits decrypt_uncompressed(const Params& p, const ModuleVector& s, const RawCiphertext& ciphertext) {
    return decode_from_reconstructed(p, s, ciphertext.u, ciphertext.v);
}

bool failure(const Bits& expected, const Bits& actual) { return expected != actual; }

static int cyclic_distance(int a, int b, int q) {
    const int direct = std::abs(a - b);
    return std::min(direct, q - direct);
}

int signed_decoding_margin(int residue, int expected_bit, int q) {
    residue = mod_q(residue, q);
    const bool correct = compress_coeff(residue, 1, q) == expected_bit;
    int distance = std::numeric_limits<int>::max();
    for (int candidate = 0; candidate < q; ++candidate) {
        const bool candidate_correct = compress_coeff(candidate, 1, q) == expected_bit;
        if (candidate_correct != correct) distance = std::min(distance, cyclic_distance(residue, candidate, q));
    }
    if (distance == std::numeric_limits<int>::max()) throw std::logic_error("decoder has no boundary");
    return correct ? distance : -distance;
}

int minimum_margin(const Params& p, const ModuleVector& s, const Ciphertext& ciphertext,
                   const Bits& expected) {
    ModuleVector uhat;
    for (const auto& poly : ciphertext.u) uhat.push_back(decompress_poly(poly, p.du, p.q));
    const Poly w = sub(decompress_poly(ciphertext.v, p.dv, p.q), dot(s, uhat, p.q), p.q);
    int result = std::numeric_limits<int>::max();
    for (std::size_t i = 0; i < p.n; ++i) result = std::min(result, signed_decoding_margin(w[i], expected[i], p.q));
    return result;
}

} // namespace toy

