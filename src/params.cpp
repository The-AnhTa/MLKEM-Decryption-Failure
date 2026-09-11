#include "toy_mlkem/params.hpp"

#include <sstream>
#include <stdexcept>

namespace toy {

void Params::validate() const {
    if (n == 0 || (n & (n - 1)) != 0) throw std::invalid_argument("n must be a positive power of two");
    if (k == 0) throw std::invalid_argument("k must be positive");
    if (q <= 2 || (q % 2) == 0) throw std::invalid_argument("q must be an odd integer greater than two");
    if (eta1 <= 0 || eta2 <= 0 || eta1 > 15 || eta2 > 15)
        throw std::invalid_argument("CBD parameters must be in 1..15");
    if (du <= 0 || dv <= 0 || du > 16 || dv > 16)
        throw std::invalid_argument("compression widths must be in 1..16");
    if ((1ULL << du) > static_cast<unsigned long long>(q) ||
        (1ULL << dv) > static_cast<unsigned long long>(q)) {
        throw std::invalid_argument("this implementation requires 2^d <= q");
    }
}

std::string Params::id() const {
    std::ostringstream out;
    out << "n" << n << "-k" << k << "-q" << q << "-e" << eta1 << "_" << eta2
        << "-d" << du << "_" << dv;
    return out.str();
}

Params Params::e0() { return {2, 1, 17, 1, 1, 3, 2}; }

Params Params::preset(const std::string& name) {
    if (name == "e0") return e0();
    if (name == "e1") return {2, 1, 97, 1, 1, 5, 3};
    if (name == "e2") return {4, 1, 3329, 2, 2, 10, 4};
    if (name == "e3") return {2, 2, 3329, 2, 2, 10, 4};
    if (name == "e4") return {4, 1, 3329, 3, 2, 10, 4};
    if (name == "e5") return {8, 1, 3329, 1, 1, 10, 4};
    throw std::invalid_argument("unknown parameter preset: " + name);
}

} // namespace toy
