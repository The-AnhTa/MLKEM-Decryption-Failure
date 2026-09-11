#include "toy_mlkem/ring.hpp"

#include <stdexcept>

namespace toy {

int mod_q(long long value, int q) {
    const auto r = static_cast<int>(value % q);
    return r < 0 ? r + q : r;
}

int centered(int value, int q) {
    const int r = mod_q(value, q);
    return r > q / 2 ? r - q : r;
}

static void same_size(const Poly& a, const Poly& b) {
    if (a.size() != b.size() || a.empty()) throw std::invalid_argument("polynomial size mismatch");
}

Poly add(const Poly& a, const Poly& b, int q) {
    same_size(a, b);
    Poly out(a.size());
    for (std::size_t i = 0; i < a.size(); ++i) out[i] = mod_q(a[i] + b[i], q);
    return out;
}

Poly sub(const Poly& a, const Poly& b, int q) {
    same_size(a, b);
    Poly out(a.size());
    for (std::size_t i = 0; i < a.size(); ++i) out[i] = mod_q(a[i] - b[i], q);
    return out;
}

Poly negacyclic_mul(const Poly& a, const Poly& b, int q) {
    same_size(a, b);
    const std::size_t n = a.size();
    std::vector<long long> raw(n, 0);
    for (std::size_t i = 0; i < n; ++i) {
        for (std::size_t j = 0; j < n; ++j) {
            const std::size_t degree = i + j;
            const long long product = static_cast<long long>(a[i]) * b[j];
            if (degree < n) raw[degree] += product;
            else raw[degree - n] -= product;
        }
    }
    Poly out(n);
    for (std::size_t i = 0; i < n; ++i) out[i] = mod_q(raw[i], q);
    return out;
}

Poly dot(const ModuleVector& a, const ModuleVector& b, int q) {
    if (a.size() != b.size() || a.empty()) throw std::invalid_argument("module-vector size mismatch");
    Poly out(a.front().size(), 0);
    for (std::size_t i = 0; i < a.size(); ++i) out = add(out, negacyclic_mul(a[i], b[i], q), q);
    return out;
}

ModuleVector mat_vec(const Matrix& a, const ModuleVector& x, const ModuleVector& error, int q) {
    if (a.empty() || a.size() != error.size()) throw std::invalid_argument("matrix size mismatch");
    ModuleVector out;
    out.reserve(a.size());
    for (std::size_t i = 0; i < a.size(); ++i) out.push_back(add(dot(a[i], x, q), error[i], q));
    return out;
}

ModuleVector transpose_mat_vec(const Matrix& a, const ModuleVector& x, const ModuleVector& error, int q) {
    if (a.empty() || a.size() != x.size() || a.size() != error.size()) throw std::invalid_argument("matrix size mismatch");
    ModuleVector out(a.size(), Poly(error.front().size(), 0));
    for (std::size_t column = 0; column < a.size(); ++column) {
        for (std::size_t row = 0; row < a.size(); ++row) {
            out[column] = add(out[column], negacyclic_mul(a[row][column], x[row], q), q);
        }
        out[column] = add(out[column], error[column], q);
    }
    return out;
}

} // namespace toy

