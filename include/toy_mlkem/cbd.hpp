#pragma once

#include <cstdint>
#include <iosfwd>
#include <string>
#include <utility>
#include <vector>

#include "toy_mlkem/ring.hpp"

namespace toy {

class Weight {
public:
    Weight(std::uint64_t value = 0);
    std::string str() const;
    explicit operator long double() const;
    friend bool operator==(const Weight&, const Weight&) = default;
    friend bool operator<(const Weight& a, const Weight& b);
    friend bool operator>(const Weight& a, const Weight& b) { return b < a; }
    friend bool operator<=(const Weight& a, const Weight& b) { return !(b < a); }
    friend bool operator>=(const Weight& a, const Weight& b) { return !(a < b); }
    friend Weight operator+(const Weight& a, const Weight& b);
    friend Weight operator-(const Weight& a, const Weight& b);
    friend Weight operator*(const Weight& a, const Weight& b);
    friend std::ostream& operator<<(std::ostream& out, const Weight& value);

private:
    static constexpr std::uint32_t base_ = 1'000'000'000U;
    std::vector<std::uint32_t> limbs_;
    void normalize();
};

struct WeightedPoly {
    Poly value;
    Weight weight{};
};

std::vector<std::pair<int, Weight>> cbd_coefficients(int eta);
std::vector<WeightedPoly> cbd_polynomials(std::size_t n, int eta, int q);
Weight checked_add(Weight a, Weight b);
Weight checked_mul(Weight a, Weight b);

} // namespace toy
