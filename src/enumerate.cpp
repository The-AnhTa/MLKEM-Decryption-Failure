#include "toy_mlkem/enumerate.hpp"

#include <algorithm>
#include <array>
#include <filesystem>
#include <fstream>
#include <functional>
#include <limits>
#include <numeric>
#include <random>
#include <stdexcept>
#include <tuple>
#include <unordered_map>

namespace toy {

static void add_public_features(ExperimentResult& result, const Matrix& a, const ModuleVector& t,
                                int q, Weight total, Weight failures) {
    result.laws["t_norm2"].add(feature_t_centered_norm(t, q), total, failures);
    result.laws["t_histogram"].add(feature_t_histogram(t, q), total, failures);
    result.laws["t_autocorrelation"].add(feature_t_autocorrelation(t, q), total, failures);
    result.laws["at_norm_pair"].add(feature_at_norm_pair(a, t, q), total, failures);
    result.laws["at_pair_histogram"].add(feature_at_pair_histogram(a, t, q), total, failures);
    result.laws["at_correlations"].add(feature_at_correlations(a, t, q), total, failures);
    result.laws["at_projections"].add(feature_at_projections(a, t, q), total, failures);
}

std::string ablation_name(Ablation mode) {
    switch (mode) {
        case Ablation::None: return "none";
        case Ablation::NoCompression: return "no-compression";
        case Ablation::IndependentCompression: return "independent-compression";
    }
    throw std::logic_error("unknown ablation");
}

Ablation parse_ablation(const std::string& name) {
    if (name == "none") return Ablation::None;
    if (name == "no-compression") return Ablation::NoCompression;
    if (name == "independent-compression") return Ablation::IndependentCompression;
    throw std::invalid_argument("unknown ablation: " + name);
}

static std::vector<Poly> uniform_polynomials(std::size_t n, int q) {
    std::vector<Poly> out{{}};
    for (std::size_t i = 0; i < n; ++i) {
        std::vector<Poly> next;
        next.reserve(out.size() * static_cast<std::size_t>(q));
        for (const auto& prefix : out) for (int x = 0; x < q; ++x) {
            auto value = prefix;
            value.push_back(x);
            next.push_back(std::move(value));
        }
        out = std::move(next);
    }
    return out;
}

static std::vector<Bits> messages(std::size_t n) {
    std::vector<Bits> out;
    if (n >= sizeof(std::size_t) * 8) throw std::invalid_argument("message dimension too large");
    const std::size_t count = std::size_t{1} << n;
    out.reserve(count);
    for (std::size_t mask = 0; mask < count; ++mask) {
        Bits bits(n);
        for (std::size_t i = 0; i < n; ++i) bits[i] = static_cast<int>((mask >> i) & 1U);
        out.push_back(std::move(bits));
    }
    return out;
}

static std::vector<std::pair<ModuleVector, Weight>> module_support(const std::vector<WeightedPoly>& polynomials,
                                                                   std::size_t k) {
    std::vector<std::pair<ModuleVector, Weight>> states{{ModuleVector{}, 1}};
    for (std::size_t i = 0; i < k; ++i) {
        std::vector<std::pair<ModuleVector, Weight>> next;
        next.reserve(states.size() * polynomials.size());
        for (const auto& [prefix, prefix_weight] : states) for (const auto& poly : polynomials) {
            auto value = prefix;
            value.push_back(poly.value);
            next.emplace_back(std::move(value), checked_mul(prefix_weight, poly.weight));
        }
        states = std::move(next);
    }
    return states;
}

static std::vector<WeightedPoly> compression_error_polynomials(std::size_t n, int d, int q) {
    std::map<int, Weight> coefficient_counts;
    for (int x = 0; x < q; ++x) {
        const int error = centered(decompress_coeff(compress_coeff(x, d, q), d, q) - x, q);
        coefficient_counts[error] = checked_add(coefficient_counts[error], 1);
    }
    std::vector<WeightedPoly> states{{Poly{}, 1}};
    for (std::size_t i = 0; i < n; ++i) {
        std::vector<WeightedPoly> next;
        for (const auto& state : states) for (const auto& [error, weight] : coefficient_counts) {
            auto value = state.value;
            value.push_back(mod_q(error, q));
            next.push_back({std::move(value), checked_mul(state.weight, weight)});
        }
        states = std::move(next);
    }
    return states;
}

// Tiny correctness oracle. Deliberately explicit over every random variable.
ExperimentResult enumerate_bruteforce(const Params& p, bool ciphertext_features) {
    p.validate();
    if (p.k != 1) throw std::invalid_argument("reference enumerator currently supports k=1");
    ExperimentResult result;
    result.metadata["enumeration"] = "global-bruteforce";
    result.coordinate_total.assign(p.n, 0);
    result.coordinate_correct.assign(p.n, 0);
    const auto uniform = uniform_polynomials(p.n, p.q);
    const auto cbd1 = cbd_polynomials(p.n, p.eta1, p.q);
    const auto cbd2 = cbd_polynomials(p.n, p.eta2, p.q);
    const auto msgs = messages(p.n);

    for (const auto& ap : uniform) {
        const Matrix a{{ap}};
        for (const auto& sw : cbd1) for (const auto& ew : cbd1) {
            const ModuleVector s{sw.value}, e{ew.value};
            const auto t = keygen(p, a, s, e);
            for (const auto& yw : cbd1) for (const auto& e1w : cbd2)
                for (const auto& e2w : cbd2) for (const auto& message : msgs) {
                    const Weight weight = checked_mul(checked_mul(checked_mul(checked_mul(sw.weight, ew.weight), yw.weight), e1w.weight), e2w.weight);
                    const ModuleVector y{yw.value}, e1{e1w.value};
                    const auto c = encrypt(p, a, t, y, e1, e2w.value, message);
                    const auto decoded = decrypt(p, s, c);
                    const Weight failed = failure(message, decoded) ? weight : 0;
                    result.laws["global"].add("all", weight, failed);
                    result.laws["pk"].add(feature_pk(a, t), weight, failed);
                    result.laws["secret_key"].add(feature_secret_key(a, s, e), weight, failed);
                    add_public_features(result, a, t, p.q, weight, failed);
                    const int margin = minimum_margin(p, s, c, message);
                    result.laws["margin"].add(std::to_string(margin), weight, failed);
                    if (ciphertext_features) {
                        result.laws["ciphertext"].add(feature_ciphertext(c), weight, failed);
                        result.laws["pk_ciphertext"].add(feature_pk_ciphertext(a, t, c), weight, failed);
                        result.laws["ciphertext_symbols"].add(feature_ciphertext_symbols(c, p.du, p.dv), weight, failed);
                        result.laws["normalized_uv_margin"].add(
                            feature_normalized_uv_margin(c, p.du, p.dv, p.q, margin), weight, failed);
                        result.laws["mechanism_margin"].add(
                            feature_symbol_histogram_margin(c, p.du, p.dv, margin), weight, failed);
                    }
                    for (std::size_t i = 0; i < p.n; ++i) {
                        result.coordinate_total[i] = checked_add(result.coordinate_total[i], weight);
                        if (decoded[i] == message[i]) result.coordinate_correct[i] = checked_add(result.coordinate_correct[i], weight);
                        auto& cells = result.pk_coordinate_laws[feature_pk(a, t)];
                        if (cells.empty()) cells.resize(p.n);
                        cells[i].total = checked_add(cells[i].total, weight);
                        if (decoded[i] != message[i]) cells[i].failures = checked_add(cells[i].failures, weight);
                    }
                }
        }
    }
    for (const auto& [_, law] : result.laws) law.validate();
    return result;
}

ExperimentResult enumerate_ciphertext_dp(const Params& p, Ablation mode, std::size_t max_outer_states,
                                         bool scalable_only, bool normalized_only, bool mechanism_only) {
    p.validate();
    if (p.k != 1) throw std::invalid_argument("ciphertext DP global enumerator currently supports k=1");
    if (mode == Ablation::IndependentCompression)
        throw std::invalid_argument("ciphertext observables are not defined for independent-compression mode");
    ExperimentResult result;
    result.metadata["enumeration"] = max_outer_states ? "deterministic-prefix-ciphertext-dp" : "global-ciphertext-dp";
    result.metadata["observable_scope"] = mechanism_only ? "mechanism-reduction" :
        (normalized_only ? "frozen-normalized-transfer" :
        (scalable_only ? "frozen-scalable-only" : "complete"));
    if (normalized_only && mechanism_only) throw std::invalid_argument("choose one focused ciphertext observer");
    if (max_outer_states) result.metadata["max_outer_states"] = std::to_string(max_outer_states);
    // This DP tracks the joint ciphertext/failure law, not coordinate marginals.
    const auto uniform = uniform_polynomials(p.n, p.q);
    const auto cbd1 = cbd_polynomials(p.n, p.eta1, p.q);
    const auto cbd2 = cbd_polynomials(p.n, p.eta2, p.q);
    const auto e2coeff = cbd_coefficients(p.eta2);
    std::size_t visited = 0;

    for (const auto& ap : uniform) {
        const Matrix a{{ap}};
        for (const auto& sw : cbd1) for (const auto& ew : cbd1) {
            const ModuleVector s{sw.value}, e{ew.value};
            const auto t = keygen(p, a, s, e);
            for (const auto& yw : cbd1) for (const auto& e1w : cbd2) {
                if (max_outer_states && visited >= max_outer_states) goto dp_finished;
                ++visited;
                const ModuleVector y{yw.value}, e1{e1w.value};
                const auto raw_u = transpose_mat_vec(a, y, e1, p.q);
                Ciphertext base_c;
                if (mode == Ablation::None) {
                    for (const auto& poly : raw_u) base_c.u.push_back(compress_poly(poly, p.du, p.q));
                } else {
                    base_c.u = raw_u;
                }
                const auto uhat = mode == Ablation::None
                    ? ModuleVector{decompress_poly(base_c.u[0], p.du, p.q)} : base_c.u;
                const Poly h = dot(s, uhat, p.q);
                const Poly ty = dot(t, y, p.q);
                using State = std::pair<std::vector<int>, int>;
                std::map<State, Weight> dp{{State{{}, std::numeric_limits<int>::max()}, 1}};
                for (std::size_t i = 0; i < p.n; ++i) {
                    std::map<State, Weight> next;
                    for (const auto& [state, state_weight] : dp)
                        for (const auto& [e2, e2weight] : e2coeff) for (int bit = 0; bit <= 1; ++bit) {
                            const int raw_v = mod_q(ty[i] + e2 + decompress_coeff(bit, 1, p.q), p.q);
                            const int vc = mode == Ablation::None ? compress_coeff(raw_v, p.dv, p.q) : raw_v;
                            const int reconstructed_v = mode == Ablation::None
                                ? decompress_coeff(vc, p.dv, p.q) : vc;
                            const int w = mod_q(reconstructed_v - h[i], p.q);
                            const int margin = signed_decoding_margin(w, bit, p.q);
                            auto symbols = state.first;
                            symbols.push_back(vc);
                            auto& weight = next[{std::move(symbols), std::min(state.second, margin)}];
                            weight = checked_add(weight, checked_mul(state_weight, e2weight));
                        }
                    dp = std::move(next);
                }
                const Weight outer = checked_mul(checked_mul(checked_mul(sw.weight, ew.weight), yw.weight), e1w.weight);
                for (const auto& [state, weight] : dp) {
                    Ciphertext c = base_c;
                    c.v = state.first;
                    const Weight scaled = checked_mul(outer, weight);
                    const Weight failed = state.second <= 0 ? scaled : 0;
                    result.laws["global"].add("all", scaled, failed);
                    if (!scalable_only && !normalized_only && !mechanism_only) {
                        result.laws["ciphertext"].add(feature_ciphertext(c), scaled, failed);
                        result.laws["pk_ciphertext"].add(feature_pk_ciphertext(a, t, c), scaled, failed);
                    }
                    if (mode == Ablation::None && !scalable_only && !normalized_only && !mechanism_only)
                        result.laws["ciphertext_symbols"].add(feature_ciphertext_symbols(c, p.du, p.dv), scaled, failed);
                    if (mode == Ablation::None && !normalized_only && !mechanism_only) {
                        result.laws["hist_u"].add(feature_hist_u(c, 1 << p.du), scaled, failed);
                        result.laws["hist_v"].add(feature_hist_v(c, 1 << p.dv), scaled, failed);
                        result.laws["extreme_symbols"].add(feature_extreme_symbol_counts(c, 1 << p.du, 1 << p.dv), scaled, failed);
                        result.laws["entropy_1024"].add(feature_entropy_1024(c, 1 << p.du, 1 << p.dv), scaled, failed);
                        result.laws["decompressed_norms"].add(feature_decompressed_norms(c, p.du, p.dv, p.q), scaled, failed);
                        result.laws["joint_uv_histogram"].add(feature_joint_uv_histogram(c), scaled, failed);
                        result.laws["normalized_uv_margin"].add(
                            feature_normalized_uv_margin(c, p.du, p.dv, p.q, state.second), scaled, failed);
                    }
                    if (mode == Ablation::None && normalized_only)
                        result.laws["normalized_uv_margin"].add(
                            feature_normalized_uv_margin(c, p.du, p.dv, p.q, state.second), scaled, failed);
                    if (mode == Ablation::None && mechanism_only)
                        result.laws["mechanism_margin"].add(
                            feature_symbol_histogram_margin(c, p.du, p.dv, state.second), scaled, failed);
                    if (mode == Ablation::None && !normalized_only && !mechanism_only)
                        result.laws["mechanism_margin"].add(
                            feature_symbol_histogram_margin(c, p.du, p.dv, state.second), scaled, failed);
                }
            }
        }
    }
dp_finished:
    for (const auto& [_, law] : result.laws) law.validate();
    return result;
}

struct InnerResult {
    Weight total{};
    Weight failures{};
    std::map<int, Weight> margins;
    std::vector<Weight> coordinate_total;
    std::vector<Weight> coordinate_correct;
};

static InnerResult evaluate_inner(const Params& p, Ablation mode, const ModuleVector& s,
                                  const RawCiphertext& base, Weight outer_weight) {
    const auto e2coeff = cbd_coefficients(p.eta2);
    std::vector<WeightedPoly> u_errors{{Poly(p.n, 0), 1}};
    std::vector<std::pair<int, Weight>> v_errors{{0, 1}};
    if (mode == Ablation::IndependentCompression) {
        u_errors = compression_error_polynomials(p.n, p.du, p.q);
        std::map<int, Weight> counts;
        for (int x = 0; x < p.q; ++x) {
            const int err = centered(decompress_coeff(compress_coeff(x, p.dv, p.q), p.dv, p.q) - x, p.q);
            counts[err] = checked_add(counts[err], 1);
        }
        v_errors.assign(counts.begin(), counts.end());
    }

    InnerResult aggregate;
    aggregate.coordinate_total.assign(p.n, 0);
    aggregate.coordinate_correct.assign(p.n, 0);
    for (const auto& uw : u_errors) {
        ModuleVector reconstructed_u;
        if (mode == Ablation::None) {
            for (const auto& raw_u : base.u) reconstructed_u.push_back(decompress_poly(compress_poly(raw_u, p.du, p.q), p.du, p.q));
        } else if (mode == Ablation::NoCompression) {
            reconstructed_u = base.u;
        } else {
            reconstructed_u = base.u;
            reconstructed_u[0] = add(reconstructed_u[0], uw.value, p.q);
        }
        const Poly h = dot(s, reconstructed_u, p.q);
        std::vector<std::map<int, Weight>> coordinate_margins(p.n);
        std::vector<Weight> coord_total(p.n, 0), coord_correct(p.n, 0);

        for (std::size_t i = 0; i < p.n; ++i) {
            for (const auto& [e2, e2weight] : e2coeff) for (int bit = 0; bit <= 1; ++bit)
                for (const auto& [verror, vweight] : v_errors) {
                    const int raw_v = mod_q(base.v[i] + e2 + decompress_coeff(bit, 1, p.q), p.q);
                    int reconstructed_v = raw_v;
                    if (mode == Ablation::None)
                        reconstructed_v = decompress_coeff(compress_coeff(raw_v, p.dv, p.q), p.dv, p.q);
                    else if (mode == Ablation::IndependentCompression)
                        reconstructed_v = mod_q(raw_v + verror, p.q);
                    const int w = mod_q(reconstructed_v - h[i], p.q);
                    const bool correct = compress_coeff(w, 1, p.q) == bit;
                    const int margin = signed_decoding_margin(w, bit, p.q);
                    const Weight weight = checked_mul(e2weight, vweight);
                    coord_total[i] = checked_add(coord_total[i], weight);
                    if (correct) coord_correct[i] = checked_add(coord_correct[i], weight);
                    coordinate_margins[i][margin] = checked_add(coordinate_margins[i][margin], weight);
                }
        }

        Weight inner_total = 1, inner_correct = 1;
        for (std::size_t i = 0; i < p.n; ++i) {
            inner_total = checked_mul(inner_total, coord_total[i]);
            inner_correct = checked_mul(inner_correct, coord_correct[i]);
        }
        const Weight u_weight = uw.weight;
        aggregate.total = checked_add(aggregate.total, checked_mul(u_weight, inner_total));
        aggregate.failures = checked_add(aggregate.failures, checked_mul(u_weight, inner_total - inner_correct));

        std::map<int, Weight> minimum_dp{{std::numeric_limits<int>::max(), 1}};
        for (const auto& margin_dist : coordinate_margins) {
            std::map<int, Weight> next;
            for (const auto& [old_min, old_weight] : minimum_dp)
                for (const auto& [margin, weight] : margin_dist)
                    next[std::min(old_min, margin)] = checked_add(next[std::min(old_min, margin)], checked_mul(old_weight, weight));
            minimum_dp = std::move(next);
        }
        for (const auto& [margin, weight] : minimum_dp)
            aggregate.margins[margin] = checked_add(aggregate.margins[margin], checked_mul(u_weight, weight));

        for (std::size_t i = 0; i < p.n; ++i) {
            Weight other = 1;
            for (std::size_t j = 0; j < p.n; ++j) if (j != i) other = checked_mul(other, coord_total[j]);
            aggregate.coordinate_total[i] = checked_add(aggregate.coordinate_total[i], checked_mul(u_weight, checked_mul(coord_total[i], other)));
            aggregate.coordinate_correct[i] = checked_add(aggregate.coordinate_correct[i], checked_mul(u_weight, checked_mul(coord_correct[i], other)));
        }
    }
    for (auto& value : aggregate.coordinate_total) value = checked_mul(value, outer_weight);
    for (auto& value : aggregate.coordinate_correct) value = checked_mul(value, outer_weight);
    return aggregate;
}

ExperimentResult enumerate_frozen_public(const Params& p, std::size_t max_keys) {
    p.validate();
    if (p.k != 1) throw std::invalid_argument("exact frozen-public enumerator currently supports k=1");
    ExperimentResult result;
    result.metadata["enumeration"] = max_keys ? "deterministic-key-prefix" : "global-exact";
    result.metadata["observable_scope"] = "frozen-public-features";
    if (max_keys) result.metadata["max_keys"] = std::to_string(max_keys);
    const auto uniform = uniform_polynomials(p.n, p.q);
    const auto cbd1 = cbd_polynomials(p.n, p.eta1, p.q);
    const auto cbd2 = cbd_polynomials(p.n, p.eta2, p.q);
    std::size_t key_count = 0;
    for (const auto& ap : uniform) {
        const Matrix a{{ap}};
        for (const auto& sw : cbd1) for (const auto& ew : cbd1) {
            if (max_keys && key_count >= max_keys) goto frozen_done;
            ++key_count;
            const ModuleVector s{sw.value}, e{ew.value};
            const auto t = keygen(p, a, s, e);
            Weight key_total = 0, key_failures = 0;
            for (const auto& yw : cbd1) for (const auto& e1w : cbd2) {
                const ModuleVector y{yw.value}, e1{e1w.value};
                RawCiphertext base{transpose_mat_vec(a, y, e1, p.q), dot(t, y, p.q)};
                const Weight outer = checked_mul(checked_mul(checked_mul(sw.weight, ew.weight), yw.weight), e1w.weight);
                const auto inner = evaluate_inner(p, Ablation::None, s, base, outer);
                key_total = checked_add(key_total, checked_mul(outer, inner.total));
                key_failures = checked_add(key_failures, checked_mul(outer, inner.failures));
            }
            result.laws["global"].add("all", key_total, key_failures);
            add_public_features(result, a, t, p.q, key_total, key_failures);
        }
    }
frozen_done:
    for (const auto& [_, law] : result.laws) law.validate();
    return result;
}

ExperimentResult enumerate_optimized_pk(const Params& p, Ablation mode, std::size_t max_outer_states) {
    p.validate();
    if (p.k != 1) throw std::invalid_argument("exact global enumerator currently supports k=1");
    if (mode == Ablation::IndependentCompression && p.k != 1) throw std::invalid_argument("independent compression currently supports k=1");
    ExperimentResult result;
    result.metadata["enumeration"] = max_outer_states ? "deterministic-prefix" : "global-exact";
    if (max_outer_states) result.metadata["max_outer_states"] = std::to_string(max_outer_states);
    result.coordinate_total.assign(p.n, 0);
    result.coordinate_correct.assign(p.n, 0);
    const auto uniform = uniform_polynomials(p.n, p.q);
    const auto cbd1 = cbd_polynomials(p.n, p.eta1, p.q);
    const auto cbd2 = cbd_polynomials(p.n, p.eta2, p.q);
    std::size_t visited = 0;

    for (const auto& ap : uniform) {
        const Matrix a{{ap}};
        for (const auto& sw : cbd1) for (const auto& ew : cbd1) {
            const ModuleVector s{sw.value}, e{ew.value};
            const auto t = keygen(p, a, s, e);
            const std::string pk = feature_pk(a, t);
            const std::string sk = feature_secret_key(a, s, e);
            for (const auto& yw : cbd1) for (const auto& e1w : cbd2) {
                if (max_outer_states && visited >= max_outer_states) goto finished;
                ++visited;
                const ModuleVector y{yw.value}, e1{e1w.value};
                RawCiphertext base;
                base.u = transpose_mat_vec(a, y, e1, p.q);
                base.v = dot(t, y, p.q); // e2 and message are integrated below.
                const Weight outer = checked_mul(checked_mul(checked_mul(sw.weight, ew.weight), yw.weight), e1w.weight);
                const auto inner = evaluate_inner(p, mode, s, base, outer);
                const Weight total = checked_mul(outer, inner.total);
                const Weight failures = checked_mul(outer, inner.failures);
                result.laws["global"].add("all", total, failures);
                result.laws["pk"].add(pk, total, failures);
                result.laws["secret_key"].add(sk, total, failures);
                add_public_features(result, a, t, p.q, total, failures);
                for (const auto& [margin, weight] : inner.margins) {
                    const Weight scaled = checked_mul(outer, weight);
                    result.laws["margin"].add(std::to_string(margin), scaled, margin <= 0 ? scaled : 0);
                    result.laws["norm_margin"].add(feature_t_centered_norm(t, p.q) + "|M=" + std::to_string(margin), scaled, margin <= 0 ? scaled : 0);
                }
                for (std::size_t i = 0; i < p.n; ++i) {
                    result.coordinate_total[i] = checked_add(result.coordinate_total[i], inner.coordinate_total[i]);
                    result.coordinate_correct[i] = checked_add(result.coordinate_correct[i], inner.coordinate_correct[i]);
                    auto& cells = result.pk_coordinate_laws[pk];
                    if (cells.empty()) cells.resize(p.n);
                    cells[i].total = checked_add(cells[i].total, inner.coordinate_total[i]);
                    cells[i].failures = checked_add(cells[i].failures,
                                                    inner.coordinate_total[i] - inner.coordinate_correct[i]);
                }
            }
        }
    }
finished:
    for (const auto& [_, law] : result.laws) law.validate();
    return result;
}

static Poly sample_cbd_poly(std::size_t n, int eta, int q, std::mt19937_64& rng) {
    Poly out(n, 0);
    std::uniform_int_distribution<int> bit(0, 1);
    for (std::size_t i = 0; i < n; ++i) {
        int x = 0;
        for (int j = 0; j < eta; ++j) x += bit(rng) - bit(rng);
        out[i] = mod_q(x, q);
    }
    return out;
}

ExperimentResult enumerate_sampled_su1_confirmation(const Params& p, std::size_t key_count,
                                                     std::size_t y_per_key, std::uint64_t seed) {
    p.validate();
    if (p.k != 1 || p.eta1 != 1 || p.eta2 != 1)
        throw std::invalid_argument("frozen S_u1 confirmation requires k=1 and eta1=eta2=1");
    if (key_count == 0 || y_per_key == 0)
        throw std::invalid_argument("frozen S_u1 confirmation requires positive key and y sample counts");
    ExperimentResult result;
    result.metadata["enumeration"] = "sampled-keys-and-y";
    result.metadata["conditional_enumeration"] = "exact-e1-e2-message-given-key-y";
    result.metadata["observable_scope"] = "frozen-su1-confirmation";
    result.metadata["key_count"] = std::to_string(key_count);
    result.metadata["y_per_key"] = std::to_string(y_per_key);
    result.metadata["seed"] = std::to_string(seed);
    std::mt19937_64 rng(seed);
    std::uniform_int_distribution<int> uniform(0, p.q - 1);
    const auto e1_support = module_support(cbd_polynomials(p.n, p.eta2, p.q), p.k);
    const auto e2_support = cbd_coefficients(p.eta2);
    std::vector<std::array<int, 2>> margin_lookup(static_cast<std::size_t>(p.q));
    for (int w = 0; w < p.q; ++w)
        for (int bit = 0; bit <= 1; ++bit)
            margin_lookup[static_cast<std::size_t>(w)][static_cast<std::size_t>(bit)] =
                signed_decoding_margin(w, bit, p.q);

    for (std::size_t key_index = 0; key_index < key_count; ++key_index) {
        Matrix a(p.k, std::vector<Poly>(p.k, Poly(p.n)));
        for (auto& row : a) for (auto& poly : row) for (int& x : poly) x = uniform(rng);
        ModuleVector s(p.k), e(p.k);
        for (std::size_t i = 0; i < p.k; ++i) {
            s[i] = sample_cbd_poly(p.n, p.eta1, p.q, rng);
            e[i] = sample_cbd_poly(p.n, p.eta1, p.q, rng);
        }
        const auto t = keygen(p, a, s, e);
        for (std::size_t y_index = 0; y_index < y_per_key; ++y_index) {
            ModuleVector y{sample_cbd_poly(p.n, p.eta1, p.q, rng)};
            ModuleVector zero(p.k, Poly(p.n, 0));
            const ModuleVector ay = transpose_mat_vec(a, y, zero, p.q);
            const Poly ty = dot(t, y, p.q);
            for (const auto& [e1, e1_weight] : e1_support) {
                ModuleVector raw_u = ay;
                for (std::size_t i = 0; i < p.n; ++i)
                    raw_u[0][i] = mod_q(raw_u[0][i] + e1[0][i], p.q);
                Ciphertext c;
                c.u.push_back(compress_poly(raw_u[0], p.du, p.q));
                ModuleVector uhat{decompress_poly(c.u[0], p.du, p.q)};
                const Poly h = dot(s, uhat, p.q);

                const std::size_t width = static_cast<std::size_t>(2 * p.q + 1);
                std::vector<std::uint64_t> dp(width), next(width), local(width);
                dp[static_cast<std::size_t>(2 * p.q)] = 1; // sentinel minimum +q
                for (std::size_t i = 0; i < p.n; ++i) {
                    std::fill(local.begin(), local.end(), 0);
                    for (const auto& [e2, _] : e2_support) for (int bit = 0; bit <= 1; ++bit) {
                        const int raw_v = mod_q(ty[i] + e2 + decompress_coeff(bit, 1, p.q), p.q);
                        const int vc = compress_coeff(raw_v, p.dv, p.q);
                        const int w = mod_q(decompress_coeff(vc, p.dv, p.q) - h[i], p.q);
                        const int margin = margin_lookup[static_cast<std::size_t>(w)][static_cast<std::size_t>(bit)];
                        local[static_cast<std::size_t>(margin + p.q)] += e2 == 0 ? 2U : 1U;
                    }
                    std::fill(next.begin(), next.end(), 0);
                    for (int old_margin = -p.q; old_margin <= p.q; ++old_margin) {
                        const auto old_weight = dp[static_cast<std::size_t>(old_margin + p.q)];
                        if (!old_weight) continue;
                        for (int margin = -p.q; margin <= p.q; ++margin) {
                            const auto local_weight = local[static_cast<std::size_t>(margin + p.q)];
                            if (!local_weight) continue;
                            const int minimum = std::min(old_margin, margin);
                            next[static_cast<std::size_t>(minimum + p.q)] += old_weight * local_weight;
                        }
                    }
                    dp.swap(next);
                }
                for (int margin = -p.q; margin < p.q; ++margin) {
                    const auto inner_weight = dp[static_cast<std::size_t>(margin + p.q)];
                    if (!inner_weight) continue;
                    const Weight scaled = checked_mul(e1_weight, Weight{inner_weight});
                    const Weight failed = margin <= 0 ? scaled : Weight{};
                    const std::string feature = feature_su1_margin(c, p.du, p.q, margin);
                    result.laws["global"].add("all", scaled, failed);
                    result.laws["su1_margin"].add(feature, scaled, failed);
                    result.laws["su1_margin_by_key"].add(
                        "K=" + std::to_string(key_index) + "|" + feature, scaled, failed);
                }
            }
        }
    }
    for (const auto& [_, law] : result.laws) law.validate();
    return result;
}

ExperimentResult enumerate_sampled_ciphertext_features(const Params& p, std::size_t key_count,
                                                       std::uint64_t seed,
                                                       std::size_t max_outer_per_key,
                                                       bool normalized_only,
                                                       bool mechanism_only) {
    p.validate();
    if (key_count == 0) throw std::invalid_argument("sampled-key count must be positive");
    if (p.dv > 4 || p.n > 15)
        throw std::invalid_argument("packed exact ciphertext histogram DP requires dv<=4 and n<=15");
    ExperimentResult result;
    result.metadata["enumeration"] = "sampled-keys";
    result.metadata["conditional_enumeration"] = max_outer_per_key ? "deterministic-prefix" : "exact";
    result.metadata["observable_scope"] = mechanism_only ? "mechanism-reduction" :
        (normalized_only ? "frozen-normalized-transfer" :
        "frozen-scalable-ciphertext-features");
    if (normalized_only && mechanism_only) throw std::invalid_argument("choose one focused ciphertext observer");
    result.metadata["key_count"] = std::to_string(key_count);
    result.metadata["seed"] = std::to_string(seed);
    if (max_outer_per_key) result.metadata["max_outer_per_key"] = std::to_string(max_outer_per_key);
    std::mt19937_64 rng(seed);
    std::uniform_int_distribution<int> uniform(0, p.q - 1);
    const auto y_support = module_support(cbd_polynomials(p.n, p.eta1, p.q), p.k);
    const auto e1_support = module_support(cbd_polynomials(p.n, p.eta2, p.q), p.k);
    const auto e2coeff = cbd_coefficients(p.eta2);

    for (std::size_t key_index = 0; key_index < key_count; ++key_index) {
        Matrix a(p.k, std::vector<Poly>(p.k, Poly(p.n)));
        for (auto& row : a) for (auto& poly : row) for (int& x : poly) x = uniform(rng);
        ModuleVector s(p.k), e(p.k);
        for (std::size_t i = 0; i < p.k; ++i) {
            s[i] = sample_cbd_poly(p.n, p.eta1, p.q, rng);
            e[i] = sample_cbd_poly(p.n, p.eta1, p.q, rng);
        }
        const auto t = keygen(p, a, s, e);
        const auto sk = feature_secret_key(a, s, e);
        std::size_t visited = 0;
        for (const auto& [y, yweight] : y_support) for (const auto& [e1, e1weight] : e1_support) {
            if (max_outer_per_key && visited >= max_outer_per_key) goto sampled_cipher_key_done;
            ++visited;
            const auto raw_u = transpose_mat_vec(a, y, e1, p.q);
            Ciphertext base_c;
            ModuleVector uhat;
            for (const auto& poly : raw_u) {
                base_c.u.push_back(compress_poly(poly, p.du, p.q));
                uhat.push_back(decompress_poly(base_c.u.back(), p.du, p.q));
            }
            const Poly h = dot(s, uhat, p.q);
            const Poly ty = dot(t, y, p.q);
            const bool track_joint = p.n <= 4 && !mechanism_only;
            using HistogramState = std::tuple<std::uint64_t, std::uint64_t, std::uint64_t, int>;
            std::map<HistogramState, Weight> dp{{{0, 0, 0, std::numeric_limits<int>::max()}, 1}};
            for (std::size_t i = 0; i < p.n; ++i) {
                std::map<HistogramState, Weight> next;
                for (const auto& [state, state_weight] : dp)
                    for (const auto& [e2, e2weight] : e2coeff) for (int bit = 0; bit <= 1; ++bit) {
                        const int raw_v = mod_q(ty[i] + e2 + decompress_coeff(bit, 1, p.q), p.q);
                        const int vc = compress_coeff(raw_v, p.dv, p.q);
                        const int w = mod_q(decompress_coeff(vc, p.dv, p.q) - h[i], p.q);
                        const int margin = signed_decoding_margin(w, bit, p.q);
                        const std::uint64_t code = std::get<0>(state) + (std::uint64_t{1} << (4 * vc));
                        const std::uint64_t sequence = track_joint
                            ? std::get<1>(state) | (static_cast<std::uint64_t>(vc) << (4 * i))
                            : 0;
                        std::uint64_t normalized = 0;
                        if (!mechanism_only) {
                            const int ubin = normalized_coordinate_bin(
                                decompress_coeff(base_c.u[0][i], p.du, p.q), p.q);
                            const int vbin = normalized_coordinate_bin(decompress_coeff(vc, p.dv, p.q), p.q);
                            const std::size_t joint_bin = static_cast<std::size_t>(4 * ubin + vbin);
                            normalized = std::get<2>(state) + (std::uint64_t{1} << (4 * joint_bin));
                        }
                        auto& weight = next[{code, sequence, normalized, std::min(std::get<3>(state), margin)}];
                        weight = checked_add(weight, checked_mul(state_weight, e2weight));
                    }
                dp = std::move(next);
            }
            const Weight outer = checked_mul(yweight, e1weight);
            for (const auto& [state, weight] : dp) {
                Ciphertext c = base_c;
                if (track_joint) {
                    for (std::size_t i = 0; i < p.n; ++i)
                        c.v.push_back(static_cast<int>((std::get<1>(state) >> (4 * i)) & 0xFULL));
                } else {
                    for (int symbol = 0; symbol < (1 << p.dv); ++symbol) {
                        const int count = static_cast<int>((std::get<0>(state) >> (4 * symbol)) & 0xFULL);
                        for (int j = 0; j < count; ++j) c.v.push_back(symbol);
                    }
                }
                const Weight scaled = checked_mul(outer, weight);
                const int minimum_margin = std::get<3>(state);
                const Weight failed = minimum_margin <= 0 ? scaled : 0;
                result.laws["global"].add("all", scaled, failed);
                if (!normalized_only && !mechanism_only) result.laws["secret_key"].add(sk, scaled, failed);
                auto add = [&](const std::string& name, const std::string& feature) {
                    result.laws[name].add(feature, scaled, failed);
                };
                if (!normalized_only && !mechanism_only) {
                    add("hist_u", feature_hist_u(c, 1 << p.du));
                    add("hist_v", feature_hist_v(c, 1 << p.dv));
                    add("extreme_symbols", feature_extreme_symbol_counts(c, 1 << p.du, 1 << p.dv));
                    add("entropy_1024", feature_entropy_1024(c, 1 << p.du, 1 << p.dv));
                    add("decompressed_norms", feature_decompressed_norms(c, p.du, p.dv, p.q));
                    if (track_joint) add("joint_uv_histogram", feature_joint_uv_histogram(c));
                }
                NormalizedJointHistogram normalized{};
                for (std::size_t bin = 0; bin < normalized.size(); ++bin)
                    normalized[bin] = static_cast<int>((std::get<2>(state) >> (4 * bin)) & 0xFULL);
                const std::string sufficient = encode_normalized_histogram(normalized) +
                    "|M=" + std::to_string(minimum_margin);
                if (!mechanism_only) {
                    add("normalized_uv_margin", sufficient);
                    add("normalized_uv_margin_by_key", "K=" + std::to_string(key_index) + "|" + sufficient);
                }
                if (!normalized_only) {
                    const std::string mechanism = feature_symbol_histogram_margin(
                        c, p.du, p.dv, minimum_margin);
                    add("mechanism_margin", mechanism);
                    add("mechanism_margin_by_key", "K=" + std::to_string(key_index) + "|" + mechanism);
                }
            }
        }
sampled_cipher_key_done:
        continue;
    }
    for (const auto& [_, law] : result.laws) law.validate();
    return result;
}

ExperimentResult enumerate_sampled_keys(const Params& p, std::size_t key_count,
                                        std::uint64_t seed, Ablation mode,
                                        std::size_t max_outer_per_key,
                                        bool screen_only) {
    p.validate();
    if (key_count == 0) throw std::invalid_argument("sampled-key count must be positive");
    if (mode == Ablation::IndependentCompression && p.k != 1)
        throw std::invalid_argument("independent compression currently supports k=1");
    ExperimentResult result;
    result.metadata["enumeration"] = "sampled-keys";
    result.metadata["conditional_enumeration"] = max_outer_per_key ? "deterministic-prefix" : "exact";
    result.metadata["key_count"] = std::to_string(key_count);
    result.metadata["seed"] = std::to_string(seed);
    result.metadata["observable_scope"] = screen_only ? "screen-only" : "public-features";
    if (max_outer_per_key) result.metadata["max_outer_per_key"] = std::to_string(max_outer_per_key);
    if (!screen_only) {
        result.coordinate_total.assign(p.n, 0);
        result.coordinate_correct.assign(p.n, 0);
    }
    std::mt19937_64 rng(seed);
    std::uniform_int_distribution<int> uniform(0, p.q - 1);
    const auto y_support = module_support(cbd_polynomials(p.n, p.eta1, p.q), p.k);
    const auto e1_support = module_support(cbd_polynomials(p.n, p.eta2, p.q), p.k);

    for (std::size_t key_index = 0; key_index < key_count; ++key_index) {
        Matrix a(p.k, std::vector<Poly>(p.k, Poly(p.n)));
        for (auto& row : a) for (auto& poly : row) for (int& x : poly) x = uniform(rng);
        ModuleVector s(p.k), e(p.k);
        for (std::size_t i = 0; i < p.k; ++i) {
            s[i] = sample_cbd_poly(p.n, p.eta1, p.q, rng);
            e[i] = sample_cbd_poly(p.n, p.eta1, p.q, rng);
        }
        const auto t = keygen(p, a, s, e);
        const auto pk = feature_pk(a, t);
        const auto sk = feature_secret_key(a, s, e);
        std::size_t visited = 0;
        for (const auto& [y, yweight] : y_support) for (const auto& [e1, e1weight] : e1_support) {
            if (max_outer_per_key && visited >= max_outer_per_key) goto sampled_key_done;
            ++visited;
            RawCiphertext base{transpose_mat_vec(a, y, e1, p.q), dot(t, y, p.q)};
            const Weight outer = checked_mul(yweight, e1weight);
            const auto inner = evaluate_inner(p, mode, s, base, outer);
            const Weight total = checked_mul(outer, inner.total);
            const Weight failures = checked_mul(outer, inner.failures);
            result.laws["global"].add("all", total, failures);
            result.laws["secret_key"].add(sk, total, failures);
            if (!screen_only) {
                result.laws["pk"].add(pk, total, failures);
                add_public_features(result, a, t, p.q, total, failures);
            }
            if (screen_only) continue;
            for (const auto& [margin, weight] : inner.margins) {
                const Weight scaled = checked_mul(outer, weight);
                result.laws["margin"].add(std::to_string(margin), scaled, margin <= 0 ? scaled : 0);
            }
            for (std::size_t i = 0; i < p.n; ++i) {
                result.coordinate_total[i] = checked_add(result.coordinate_total[i], inner.coordinate_total[i]);
                result.coordinate_correct[i] = checked_add(result.coordinate_correct[i], inner.coordinate_correct[i]);
                auto& cells = result.pk_coordinate_laws[pk];
                if (cells.empty()) cells.resize(p.n);
                cells[i].total = checked_add(cells[i].total, inner.coordinate_total[i]);
                cells[i].failures = checked_add(cells[i].failures,
                                                inner.coordinate_total[i] - inner.coordinate_correct[i]);
            }
        }
sampled_key_done:
        continue;
    }
    for (const auto& [_, law] : result.laws) law.validate();
    return result;
}

void export_result(const ExperimentResult& result, const Params& p,
                   Ablation mode, const std::string& directory) {
    for (const auto& [name, law] : result.laws)
        export_csv((std::filesystem::path(directory) / (name + ".csv")).string(), name, law);
    export_metadata((std::filesystem::path(directory) / "metadata.json").string(), p.id(), ablation_name(mode), result.laws, result.metadata);
    if (!result.coordinate_total.empty()) {
        std::ofstream out(std::filesystem::path(directory) / "coordinate_marginals.csv");
        out << "coordinate,total,correct,failures\n";
        for (std::size_t i = 0; i < result.coordinate_total.size(); ++i)
            out << i << ',' << result.coordinate_total[i] << ',' << result.coordinate_correct[i] << ','
                << result.coordinate_total[i] - result.coordinate_correct[i] << '\n';
    }
    if (!result.pk_coordinate_laws.empty()) {
        std::ofstream out(std::filesystem::path(directory) / "pk_coordinate_marginals.csv");
        out << "feature_value,coordinate,Nz,Eiz\n";
        for (const auto& [pk, cells] : result.pk_coordinate_laws)
            for (std::size_t i = 0; i < cells.size(); ++i)
                out << '"' << pk << "\"," << i << ',' << cells[i].total << ',' << cells[i].failures << '\n';
    }
}

} // namespace toy
