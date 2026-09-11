#include "toy_mlkem/cbd.hpp"

#include <algorithm>
#include <iomanip>
#include <ostream>
#include <sstream>
#include <stdexcept>

namespace toy {

Weight::Weight(std::uint64_t value) {
    while (value) {
        limbs_.push_back(static_cast<std::uint32_t>(value % base_));
        value /= base_;
    }
}

void Weight::normalize() {
    while (!limbs_.empty() && limbs_.back() == 0) limbs_.pop_back();
}

bool operator<(const Weight& a, const Weight& b) {
    if (a.limbs_.size() != b.limbs_.size()) return a.limbs_.size() < b.limbs_.size();
    return std::lexicographical_compare(a.limbs_.rbegin(), a.limbs_.rend(), b.limbs_.rbegin(), b.limbs_.rend());
}

Weight operator+(const Weight& a, const Weight& b) {
    Weight out;
    const std::size_t size = std::max(a.limbs_.size(), b.limbs_.size());
    out.limbs_.resize(size);
    std::uint64_t carry = 0;
    for (std::size_t i = 0; i < size; ++i) {
        const std::uint64_t av = i < a.limbs_.size() ? a.limbs_[i] : 0;
        const std::uint64_t bv = i < b.limbs_.size() ? b.limbs_[i] : 0;
        const std::uint64_t sum = av + bv + carry;
        out.limbs_[i] = static_cast<std::uint32_t>(sum % Weight::base_);
        carry = sum / Weight::base_;
    }
    if (carry) out.limbs_.push_back(static_cast<std::uint32_t>(carry));
    return out;
}

Weight operator-(const Weight& a, const Weight& b) {
    if (a < b) throw std::underflow_error("negative exact weight");
    Weight out = a;
    std::int64_t borrow = 0;
    for (std::size_t i = 0; i < out.limbs_.size(); ++i) {
        std::int64_t value = static_cast<std::int64_t>(out.limbs_[i]) -
                             (i < b.limbs_.size() ? b.limbs_[i] : 0) - borrow;
        if (value < 0) { value += Weight::base_; borrow = 1; } else borrow = 0;
        out.limbs_[i] = static_cast<std::uint32_t>(value);
    }
    out.normalize();
    return out;
}

Weight operator*(const Weight& a, const Weight& b) {
    if (a.limbs_.empty() || b.limbs_.empty()) return Weight{};
    Weight out;
    out.limbs_.assign(a.limbs_.size() + b.limbs_.size(), 0);
    for (std::size_t i = 0; i < a.limbs_.size(); ++i) {
        std::uint64_t carry = 0;
        for (std::size_t j = 0; j < b.limbs_.size(); ++j) {
            const std::uint64_t value = out.limbs_[i + j] +
                static_cast<std::uint64_t>(a.limbs_[i]) * b.limbs_[j] + carry;
            out.limbs_[i + j] = static_cast<std::uint32_t>(value % Weight::base_);
            carry = value / Weight::base_;
        }
        std::size_t position = i + b.limbs_.size();
        while (carry) {
            if (position == out.limbs_.size()) out.limbs_.push_back(0);
            const std::uint64_t value = out.limbs_[position] + carry;
            out.limbs_[position] = static_cast<std::uint32_t>(value % Weight::base_);
            carry = value / Weight::base_;
            ++position;
        }
    }
    out.normalize();
    return out;
}

std::string Weight::str() const {
    if (limbs_.empty()) return "0";
    std::ostringstream out;
    out << limbs_.back();
    for (auto it = limbs_.rbegin() + 1; it != limbs_.rend(); ++it)
        out << std::setw(9) << std::setfill('0') << *it;
    return out.str();
}

Weight::operator long double() const {
    long double out = 0;
    for (auto it = limbs_.rbegin(); it != limbs_.rend(); ++it) out = out * base_ + *it;
    return out;
}

std::ostream& operator<<(std::ostream& out, const Weight& value) { return out << value.str(); }

Weight checked_add(Weight a, Weight b) {
    return a + b;
}

Weight checked_mul(Weight a, Weight b) {
    return a * b;
}

static Weight binomial(int n, int k) {
    if (k < 0 || k > n) return 0;
    if (k > n - k) k = n - k;
    std::uint64_t out = 1;
    for (int i = 1; i <= k; ++i) out = out * static_cast<std::uint64_t>(n - k + i) / static_cast<std::uint64_t>(i);
    return Weight{out};
}

std::vector<std::pair<int, Weight>> cbd_coefficients(int eta) {
    if (eta <= 0) throw std::invalid_argument("eta must be positive");
    std::vector<std::pair<int, Weight>> out;
    for (int x = -eta; x <= eta; ++x) out.emplace_back(x, binomial(2 * eta, eta + x));
    return out;
}

std::vector<WeightedPoly> cbd_polynomials(std::size_t n, int eta, int q) {
    const auto coefficients = cbd_coefficients(eta);
    std::vector<WeightedPoly> states{{Poly{}, 1}};
    for (std::size_t i = 0; i < n; ++i) {
        std::vector<WeightedPoly> next;
        next.reserve(states.size() * coefficients.size());
        for (const auto& state : states) {
            for (const auto& [x, weight] : coefficients) {
                auto value = state.value;
                value.push_back(mod_q(x, q));
                next.push_back({std::move(value), checked_mul(state.weight, weight)});
            }
        }
        states = std::move(next);
    }
    return states;
}

} // namespace toy
