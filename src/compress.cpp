#include "toy_mlkem/compress.hpp"

#include <stdexcept>

namespace toy {

int compress_coeff(int x, int d, int q) {
    if (d <= 0 || d >= 31) throw std::invalid_argument("invalid compression width");
    const long long scale = 1LL << d;
    const long long rounded = (scale * mod_q(x, q) + q / 2) / q;
    return static_cast<int>(rounded & (scale - 1));
}

int decompress_coeff(int y, int d, int q) {
    if (d <= 0 || d >= 31 || y < 0 || y >= (1 << d)) throw std::invalid_argument("invalid compressed symbol");
    return static_cast<int>((static_cast<long long>(q) * y + (1LL << (d - 1))) >> d);
}

Poly compress_poly(const Poly& x, int d, int q) {
    Poly out(x.size());
    for (std::size_t i = 0; i < x.size(); ++i) out[i] = compress_coeff(x[i], d, q);
    return out;
}

Poly decompress_poly(const Poly& y, int d, int q) {
    Poly out(y.size());
    for (std::size_t i = 0; i < y.size(); ++i) out[i] = decompress_coeff(y[i], d, q);
    return out;
}

} // namespace toy

