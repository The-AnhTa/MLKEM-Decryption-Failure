#include "toy_mlkem/cbd.hpp"
#include "toy_mlkem/compress.hpp"
#include "toy_mlkem/enumerate.hpp"
#include "toy_mlkem/pke.hpp"
#include "toy_mlkem/ring.hpp"

#include <cstdlib>
#include <numeric>
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

void test_scalable_features_are_deterministic() {
    const toy::Params p = toy::Params::e0();
    const toy::Matrix a{{toy::Poly{1, 16}}};
    const toy::ModuleVector t{{2, 3}};
    const toy::Ciphertext c{{toy::Poly{0, 7}}, toy::Poly{0, 3}};
    require(toy::feature_at_norm_pair(a, t, p.q) == "A=2|t=13", "A,t norm pair");
    require(toy::feature_at_correlations(a, t, p.q) == "-1.1", "A,t correlations");
    require(toy::feature_hist_u(c, 8) == "1.0.0.0.0.0.0.1.", "u histogram");
    require(toy::feature_hist_v(c, 4) == "1.0.0.1.", "v histogram");
    require(toy::feature_extreme_symbol_counts(c, 8, 4) == "1.1.1.1", "extreme symbols");
    require(toy::feature_entropy_1024(c, 8, 4) == "1024.1024", "entropy quantization");
}

void test_normalized_ciphertext_histogram() {
    for (const char* preset : {"e0", "e1a", "n4q19d43", "n4q29d43"}) {
        const auto p = toy::Params::preset(preset);
        for (int d : {p.du, p.dv}) for (int symbol = 0; symbol < (1 << d); ++symbol) {
            const int residue = toy::decompress_coeff(symbol, d, p.q);
            const int bin = toy::normalized_coordinate_bin(residue, p.q);
            require(bin >= 0 && bin < 4, "normalized coordinate bin range");
            const int value = toy::centered(residue, p.q);
            if (bin == 0) require(4LL * value < -p.q, "normalized bin zero interval");
            if (bin == 1) require(4LL * value >= -p.q && value < 0, "normalized bin one interval");
            if (bin == 2) require(value >= 0 && 4LL * value < p.q, "normalized bin two interval");
            if (bin == 3) require(4LL * value >= p.q, "normalized bin three interval");
        }
    }
    const auto p = toy::Params::e0();
    const toy::Ciphertext c{{toy::Poly{0, 7}}, toy::Poly{0, 3}};
    const auto joint = toy::normalized_joint_histogram(c, p.du, p.dv, p.q);
    require(std::accumulate(joint.begin(), joint.end(), 0) == static_cast<int>(p.n),
            "normalized joint count mass");
    const auto u = toy::normalized_u_marginal(joint);
    const auto v = toy::normalized_v_marginal(joint);
    require(std::accumulate(u.begin(), u.end(), 0) == static_cast<int>(p.n), "normalized u mass");
    require(std::accumulate(v.begin(), v.end(), 0) == static_cast<int>(p.n), "normalized v mass");
    require(toy::encode_normalized_histogram(joint) == "0.0.0.0.0.1.0.0.0.0.1.0.0.0.0.0",
            "normalized histogram encoding");
    require(toy::feature_symbol_histogram_margin(c, p.du, p.dv, -2) ==
            "U=1.0.0.0.0.0.0.1|V=1.0.0.1|M=-2", "mechanism histogram encoding");
}

void test_noise_support_certificates() {
    require(!toy::noise_support_bound(toy::Params::e0()).failure_impossible,
            "E0 bound must not exclude observed failures");
    for (const char* preset : {"e2", "e3", "e4", "e5"}) {
        const auto bound = toy::noise_support_bound(toy::Params::preset(preset));
        require(bound.total < bound.decoding_margin, "large-q toy failure support certificate");
        require(bound.failure_impossible, "large-q toy failure impossible");
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
        const auto& coordinates = fast.pk_coordinate_laws.at(key);
        for (const auto& coordinate : coordinates)
            require(coordinate.total == other.total, "per-pk coordinate marginal mass");
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
    for (const char* name : {"global", "ciphertext", "pk_ciphertext", "ciphertext_symbols",
                             "normalized_uv_margin", "mechanism_margin"}) {
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
    const auto screen = toy::enumerate_sampled_keys(p, 2, 12345, toy::Ablation::None, 20, true);
    require(screen.laws.at("global").cells() == a.laws.at("global").cells(), "screen global law equality");
    require(screen.laws.at("secret_key").cells() == a.laws.at("secret_key").cells(), "screen key law equality");
    require(screen.laws.find("pk") == screen.laws.end(), "screen excludes feature laws");
}

void test_frozen_public_matches_exact() {
    const toy::Params tiny{1, 1, 5, 1, 1, 2, 1};
    const auto exact = toy::enumerate_optimized_pk(tiny);
    const auto frozen = toy::enumerate_frozen_public(tiny);
    for (const char* feature : {"global", "t_norm2", "t_histogram", "t_autocorrelation",
                                "at_norm_pair", "at_pair_histogram", "at_correlations", "at_projections"})
        require(exact.laws.at(feature).cells() == frozen.laws.at(feature).cells(), "frozen public law equality");
}

void test_scalable_ciphertext_scope() {
    const toy::Params tiny{1, 1, 5, 1, 1, 2, 1};
    const auto complete = toy::enumerate_ciphertext_dp(tiny);
    const auto scalable = toy::enumerate_ciphertext_dp(tiny, toy::Ablation::None, 0, true);
    require(scalable.laws.find("ciphertext") == scalable.laws.end(), "scalable scope excludes exact ciphertext");
    require(scalable.laws.find("pk_ciphertext") == scalable.laws.end(), "scalable scope excludes exact joint lookup");
    for (const char* feature : {"hist_u", "hist_v", "extreme_symbols", "entropy_1024",
                                "decompressed_norms", "joint_uv_histogram", "normalized_uv_margin"})
        require(complete.laws.at(feature).cells() == scalable.laws.at(feature).cells(), "scalable ciphertext law equality");
}

void test_normalized_transfer_scope() {
    const toy::Params tiny{1, 1, 5, 1, 1, 2, 1};
    const auto complete = toy::enumerate_ciphertext_dp(tiny);
    const auto focused = toy::enumerate_ciphertext_dp(tiny, toy::Ablation::None, 0, false, true);
    require(focused.laws.size() == 2, "normalized transfer scope law count");
    require(focused.laws.at("global").cells() == complete.laws.at("global").cells(),
            "normalized transfer global equality");
    require(focused.laws.at("normalized_uv_margin").cells() ==
            complete.laws.at("normalized_uv_margin").cells(), "normalized transfer law equality");
}

void test_mechanism_reduction_scope() {
    const toy::Params tiny{1, 1, 5, 1, 1, 2, 1};
    const auto complete = toy::enumerate_ciphertext_dp(tiny);
    const auto focused = toy::enumerate_ciphertext_dp(tiny, toy::Ablation::None, 0, false, false, true);
    require(focused.laws.size() == 2, "mechanism reduction scope law count");
    require(focused.laws.at("global").cells() == complete.laws.at("global").cells(),
            "mechanism reduction global equality");
    require(focused.laws.at("mechanism_margin").cells() ==
            complete.laws.at("mechanism_margin").cells(), "mechanism reduction law equality");
}

void test_sampled_ciphertext_reproducibility() {
    const toy::Params p{2, 1, 17, 1, 1, 3, 2};
    const auto a = toy::enumerate_sampled_ciphertext_features(p, 2, 42, 20);
    const auto b = toy::enumerate_sampled_ciphertext_features(p, 2, 42, 20);
    require(a.laws.at("hist_v").cells() == b.laws.at("hist_v").cells(), "sampled ciphertext reproducibility");
    require(a.laws.at("normalized_uv_margin_by_key").cells() ==
            b.laws.at("normalized_uv_margin_by_key").cells(), "sampled sufficient-statistic reproducibility");
    for (const char* feature : {"normalized_uv_margin", "normalized_uv_margin_by_key"}) {
        require(a.laws.at(feature).total() == a.laws.at("global").total(), "sampled sufficient-statistic total mass");
        require(a.laws.at(feature).failures() == a.laws.at("global").failures(),
                "sampled sufficient-statistic failure mass");
    }
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
        test_scalable_features_are_deterministic();
        test_normalized_ciphertext_histogram();
        test_noise_support_certificates();
        test_reference_matches_optimized();
        test_ciphertext_dp_matches_reference();
        test_no_compression_ciphertext_dp();
        test_sampled_key_reproducibility();
        test_frozen_public_matches_exact();
        test_scalable_ciphertext_scope();
        test_normalized_transfer_scope();
        test_mechanism_reduction_scope();
        test_sampled_ciphertext_reproducibility();
        test_ablation_mass();
        test_universal_bound();
        std::cout << "all tests passed\n";
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::cerr << "test failure: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
