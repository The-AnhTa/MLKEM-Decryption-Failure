#include "toy_mlkem/cbd.hpp"
#include "toy_mlkem/compress.hpp"
#include "toy_mlkem/enumerate.hpp"
#include "toy_mlkem/pke.hpp"
#include "toy_mlkem/ring.hpp"

#include <cstdlib>
#include <iostream>
#include <stdexcept>

namespace {

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void test_params() {
    const auto p = toy::Params::e0();
    p.validate();
    require(p.id() == "n2-k1-q17-e1_1-d3_2", "parameter id");
    bool rejected = false;
    try { toy::Params{3, 1, 17, 1, 1, 3, 2}.validate(); } catch (const std::invalid_argument&) { rejected = true; }
    require(rejected, "invalid n must be rejected");
}

void test_ring_exhaustive() {
    constexpr int q = 17;
    for (int a0 = 0; a0 < q; ++a0) for (int a1 = 0; a1 < q; ++a1)
        for (int b0 = 0; b0 < q; ++b0) for (int b1 = 0; b1 < q; ++b1) {
            const auto c = toy::negacyclic_mul({a0, a1}, {b0, b1}, q);
            require(c[0] == toy::mod_q(a0 * b0 - a1 * b1, q), "n=2 product constant");
            require(c[1] == toy::mod_q(a0 * b1 + a1 * b0, q), "n=2 product linear");
        }
}

void test_compression_exhaustive() {
    const auto p = toy::Params::e0();
    for (int d : {p.du, p.dv, 1}) {
        for (int x = 0; x < p.q; ++x) {
            const int c = toy::compress_coeff(x, d, p.q);
            require(c >= 0 && c < (1 << d), "compression range");
        }
        for (int y = 0; y < (1 << d); ++y) {
            const int x = toy::decompress_coeff(y, d, p.q);
            require(x >= 0 && x < p.q, "decompression range");
            require(toy::compress_coeff(x, d, p.q) == y, "symbol round trip");
        }
    }
}

void test_cbd_mass() {
    for (int eta : {1, 2, 3}) for (std::size_t n : {1U, 2U, 4U}) {
        toy::Weight sum = 0;
        for (const auto& state : toy::cbd_polynomials(n, eta, 3329)) sum = toy::checked_add(sum, state.weight);
        toy::Weight expected = 1;
        for (std::size_t i = 0; i < 2 * static_cast<std::size_t>(eta) * n; ++i) expected = toy::checked_mul(expected, 2);
        require(sum == expected, "CBD mass");
    }
}

void test_arbitrary_precision_weight() {
    const toy::Weight trillion{1'000'000'000'000ULL};
    const auto square = toy::checked_mul(trillion, trillion);
    require(square.str() == "1000000000000000000000000", "arbitrary-precision multiplication");
    require((square - toy::Weight{1}).str() == "999999999999999999999999", "arbitrary-precision subtraction");
}

void test_pke_and_margin() {
    const auto p = toy::Params::e0();
    const toy::Matrix a{{toy::Poly{3, 4}}};
    const toy::ModuleVector s{{1, 16}}, e{{0, 1}}, y{{1, 0}}, e1{{0, 0}};
    const toy::Poly e2{0, 0};
    const toy::Bits m{0, 1};
    const auto t = toy::keygen(p, a, s, e);
    const auto c = toy::encrypt(p, a, t, y, e1, e2, m);
    const auto decoded = toy::decrypt(p, s, c);
    require(!toy::failure(m, decoded), "deterministic PKE round trip");
    require((toy::minimum_margin(p, s, c, m) <= 0) == toy::failure(m, decoded), "margin equivalence");
    for (int residue = 0; residue < p.q; ++residue) for (int bit = 0; bit <= 1; ++bit) {
        const bool fails = toy::compress_coeff(residue, 1, p.q) != bit;
        require((toy::signed_decoding_margin(residue, bit, p.q) <= 0) == fails, "coefficient margin equivalence");
    }
}

void test_reference_matches_optimized() {
    const toy::Params tiny{1, 1, 5, 1, 1, 2, 1};
    const auto brute = toy::enumerate_bruteforce(tiny, true);
    const auto fast = toy::enumerate_optimized_pk(tiny);
    require(brute.laws.at("global").total() == fast.laws.at("global").total(), "optimized total mass");
    require(brute.laws.at("global").failures() == fast.laws.at("global").failures(), "optimized failure mass");
    require(brute.laws.at("pk").cells().size() == fast.laws.at("pk").cells().size(), "pk cell count");
    for (const auto& [key, cell] : brute.laws.at("pk").cells()) {
        const auto& other = fast.laws.at("pk").cells().at(key);
        require(cell.total == other.total && cell.failures == other.failures, "pk law equality");
    }
    require(fast.laws.at("margin").total() == fast.laws.at("global").total(), "margin mass conservation");
    require(fast.laws.at("margin").failures() == fast.laws.at("global").failures(), "margin failure equivalence");
    for (std::size_t i = 0; i < tiny.n; ++i)
        require(fast.coordinate_total[i] == fast.laws.at("global").total(), "coordinate marginal mass");
}

void test_ciphertext_dp_matches_reference() {
    const toy::Params tiny{1, 1, 5, 1, 1, 2, 1};
    const auto brute = toy::enumerate_bruteforce(tiny, true);
    const auto dp = toy::enumerate_ciphertext_dp(tiny);
    for (const char* name : {"global", "ciphertext", "pk_ciphertext", "ciphertext_symbols"}) {
        require(brute.laws.at(name).total() == dp.laws.at(name).total(), "ciphertext DP total");
        require(brute.laws.at(name).failures() == dp.laws.at(name).failures(), "ciphertext DP failures");
        require(brute.laws.at(name).cells() == dp.laws.at(name).cells(), "ciphertext DP law");
    }
}

void test_no_compression_ciphertext_dp() {
    const toy::Params tiny{1, 1, 5, 1, 1, 2, 1};
    const auto pk = toy::enumerate_optimized_pk(tiny, toy::Ablation::NoCompression);
    const auto dp = toy::enumerate_ciphertext_dp(tiny, toy::Ablation::NoCompression);
    require(pk.laws.at("global").total() == dp.laws.at("global").total(), "raw ciphertext DP total");
    require(pk.laws.at("global").failures() == dp.laws.at("global").failures(), "raw ciphertext DP failures");
    require(dp.laws.find("ciphertext_symbols") == dp.laws.end(), "compressed-symbol feature absent without compression");
}

void test_sampled_key_reproducibility() {
    const toy::Params p{2, 2, 17, 1, 1, 3, 2};
    const auto a = toy::enumerate_sampled_keys(p, 2, 12345, toy::Ablation::None, 20);
    const auto b = toy::enumerate_sampled_keys(p, 2, 12345, toy::Ablation::None, 20);
    require(a.laws.at("pk").cells() == b.laws.at("pk").cells(), "sampled-key seed reproducibility");
}

void test_ablation_mass() {
    const toy::Params tiny{1, 1, 5, 1, 1, 2, 1};
    const auto baseline = toy::enumerate_optimized_pk(tiny, toy::Ablation::None);
    const auto no_compression = toy::enumerate_optimized_pk(tiny, toy::Ablation::NoCompression);
    const auto independent = toy::enumerate_optimized_pk(tiny, toy::Ablation::IndependentCompression);
    require(baseline.laws.at("global").total() == no_compression.laws.at("global").total(), "no-compression base mass");
    require(independent.laws.at("global").total() == baseline.laws.at("global").total() * 25, "independent-compression added q masses");
}

void test_universal_bound() {
    const toy::Params tiny{1, 1, 5, 1, 1, 2, 1};
    const auto result = toy::enumerate_optimized_pk(tiny);
    const auto& law = result.laws.at("pk");
    const long double n = static_cast<long double>(law.total());
    const long double e = static_cast<long double>(law.failures());
    for (const auto& [_, cell] : law.cells()) if (cell.failures != toy::Weight{0}) {
        const long double p = static_cast<long double>(cell.total) / n;
        const long double amplification = (static_cast<long double>(cell.failures) /
                                            static_cast<long double>(cell.total)) / (e / n);
        require(amplification <= 1.0L / p + 1e-12L, "universal post-selection bound");
    }
}

} // namespace

int main() {
    try {
        test_params();
        test_ring_exhaustive();
        test_compression_exhaustive();
        test_cbd_mass();
        test_arbitrary_precision_weight();
        test_pke_and_margin();
        test_reference_matches_optimized();
        test_ciphertext_dp_matches_reference();
        test_no_compression_ciphertext_dp();
        test_sampled_key_reproducibility();
        test_ablation_mass();
        test_universal_bound();
        std::cout << "all tests passed\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "test failure: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
