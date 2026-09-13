#include "toy_mlkem/cbd.hpp"
#include "toy_mlkem/compress.hpp"
#include "toy_mlkem/params.hpp"
#include "toy_mlkem/pke.hpp"
#include "toy_mlkem/ring.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <random>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace {

using toy::Bits;
using toy::Matrix;
using toy::ModuleVector;
using toy::Params;
using toy::Poly;
using toy::Weight;

struct GlobalKey {
    std::size_t key{};
    int su1_numerator{};
    int minimum_margin{};
    bool operator<(const GlobalKey& other) const {
        return std::tie(key, su1_numerator, minimum_margin) <
               std::tie(other.key, other.su1_numerator, other.minimum_margin);
    }
};

struct LocalKey {
    std::size_t key{};
    int x_numerator{};
    int margin{};
    bool operator<(const LocalKey& other) const {
        return std::tie(key, x_numerator, margin) <
               std::tie(other.key, other.x_numerator, other.margin);
    }
};

Poly sample_cbd_poly(std::size_t n, int eta, int q, std::mt19937_64& rng) {
    Poly out(n, 0);
    std::uniform_int_distribution<int> bit(0, 1);
    for (std::size_t i = 0; i < n; ++i) {
        int x = 0;
        for (int j = 0; j < eta; ++j) x += bit(rng) - bit(rng);
        out[i] = toy::mod_q(x, q);
    }
    return out;
}

std::vector<std::pair<ModuleVector, Weight>> module_support(
        const std::vector<toy::WeightedPoly>& polynomials, std::size_t k) {
    std::vector<std::pair<ModuleVector, Weight>> states{{ModuleVector{}, 1}};
    for (std::size_t i = 0; i < k; ++i) {
        std::vector<std::pair<ModuleVector, Weight>> next;
        for (const auto& [prefix, prefix_weight] : states)
            for (const auto& poly : polynomials) {
                auto value = prefix;
                value.push_back(poly.value);
                next.push_back({std::move(value), toy::checked_mul(prefix_weight, poly.weight)});
            }
        states = std::move(next);
    }
    return states;
}

Weight power(Weight base, std::size_t exponent) {
    Weight result{1};
    for (std::size_t i = 0; i < exponent; ++i) result = toy::checked_mul(result, base);
    return result;
}

void add(std::map<GlobalKey, Weight>& law, const GlobalKey& key, const Weight& weight) {
    law[key] = toy::checked_add(law[key], weight);
}

void add(std::map<LocalKey, Weight>& law, const LocalKey& key, const Weight& weight) {
    law[key] = toy::checked_add(law[key], weight);
}

void recover(const Params& p, std::size_t key_count, std::size_t sampled_y,
             std::uint64_t seed, const std::filesystem::path& output) {
    if (p.k != 1 || p.eta1 != 1 || p.eta2 != 1)
        throw std::invalid_argument("recovery requires k=1 and eta1=eta2=1");
    if (!key_count) throw std::invalid_argument("key count must be positive");

    const auto y_support = module_support(toy::cbd_polynomials(p.n, p.eta1, p.q), p.k);
    const auto e1_support = module_support(toy::cbd_polynomials(p.n, p.eta2, p.q), p.k);
    const auto e2_support = toy::cbd_coefficients(p.eta2);
    const Weight other_coordinates = power(Weight{8}, p.n - 1);
    std::vector<std::array<int, 2>> margin_lookup(static_cast<std::size_t>(p.q));
    for (int residue = 0; residue < p.q; ++residue)
        for (int bit = 0; bit <= 1; ++bit)
            margin_lookup[static_cast<std::size_t>(residue)][static_cast<std::size_t>(bit)] =
                toy::signed_decoding_margin(residue, bit, p.q);

    std::map<GlobalKey, Weight> global;
    std::map<LocalKey, Weight> local;
    std::mt19937_64 rng(seed);
    std::uniform_int_distribution<int> uniform(0, p.q - 1);

    auto observe_y = [&](std::size_t key_index, const Matrix& a, const ModuleVector& s,
                         const ModuleVector& t, const ModuleVector& y, const Weight& y_weight) {
        ModuleVector zero(p.k, Poly(p.n, 0));
        const ModuleVector ay = toy::transpose_mat_vec(a, y, zero, p.q);
        const Poly ty = toy::dot(t, y, p.q);
        for (const auto& [e1, e1_weight] : e1_support) {
            ModuleVector raw_u = ay;
            for (std::size_t i = 0; i < p.n; ++i)
                raw_u[0][i] = toy::mod_q(raw_u[0][i] + e1[0][i], p.q);
            const Poly compressed_u = toy::compress_poly(raw_u[0], p.du, p.q);
            ModuleVector uhat{toy::decompress_poly(compressed_u, p.du, p.q)};
            const Poly h = toy::dot(s, uhat, p.q);
            int su1_numerator = 0;
            for (int value : uhat[0]) su1_numerator += std::abs(toy::centered(value, p.q));

            const Weight outer = toy::checked_mul(y_weight, e1_weight);
            std::vector<std::map<int, Weight>> coordinate_laws(p.n);
            for (std::size_t i = 0; i < p.n; ++i) {
                auto& coordinate = coordinate_laws[i];
                for (const auto& [e2, e2_weight] : e2_support)
                    for (int bit = 0; bit <= 1; ++bit) {
                        const int raw_v = toy::mod_q(
                            ty[i] + e2 + toy::decompress_coeff(bit, 1, p.q), p.q);
                        const int vc = toy::compress_coeff(raw_v, p.dv, p.q);
                        const int w = toy::mod_q(
                            toy::decompress_coeff(vc, p.dv, p.q) - h[i], p.q);
                        const int margin = margin_lookup[static_cast<std::size_t>(w)]
                                                       [static_cast<std::size_t>(bit)];
                        coordinate[margin] = toy::checked_add(coordinate[margin], e2_weight);
                    }
                const int x = std::abs(toy::centered(uhat[0][i], p.q));
                for (const auto& [margin, weight] : coordinate) {
                    const Weight scaled = toy::checked_mul(
                        outer, toy::checked_mul(weight, other_coordinates));
                    add(local, {key_index, x, margin}, scaled);
                }
            }

            std::map<int, Weight> minimum{{std::numeric_limits<int>::max(), Weight{1}}};
            for (const auto& coordinate : coordinate_laws) {
                std::map<int, Weight> next;
                for (const auto& [old_margin, old_weight] : minimum)
                    for (const auto& [margin, weight] : coordinate) {
                        const int value = std::min(old_margin, margin);
                        next[value] = toy::checked_add(
                            next[value], toy::checked_mul(old_weight, weight));
                    }
                minimum = std::move(next);
            }
            for (const auto& [margin, weight] : minimum)
                add(global, {key_index, su1_numerator, margin},
                    toy::checked_mul(outer, weight));
        }
    };

    for (std::size_t key_index = 0; key_index < key_count; ++key_index) {
        Matrix a(p.k, std::vector<Poly>(p.k, Poly(p.n)));
        for (auto& row : a) for (auto& poly : row) for (int& value : poly) value = uniform(rng);
        ModuleVector s(p.k), e(p.k);
        for (std::size_t i = 0; i < p.k; ++i) {
            s[i] = sample_cbd_poly(p.n, p.eta1, p.q, rng);
            e[i] = sample_cbd_poly(p.n, p.eta1, p.q, rng);
        }
        const ModuleVector t = toy::keygen(p, a, s, e);
        if (sampled_y) {
            for (std::size_t i = 0; i < sampled_y; ++i) {
                ModuleVector y{sample_cbd_poly(p.n, p.eta1, p.q, rng)};
                observe_y(key_index, a, s, t, y, Weight{1});
            }
        } else {
            for (const auto& [y, weight] : y_support)
                observe_y(key_index, a, s, t, y, weight);
        }
    }

    std::filesystem::create_directories(output);
    {
        std::ofstream out(output / "recovered_su1_margin_by_key.csv");
        out << "key_id,su1_numerator,minimum_margin,Nz,Ez\n";
        for (const auto& [key, weight] : global)
            out << key.key << ',' << key.su1_numerator << ',' << key.minimum_margin << ','
                << weight << ',' << (key.minimum_margin <= 0 ? weight : Weight{}) << '\n';
    }
    {
        std::ofstream out(output / "coordinate_margin_by_key.csv");
        out << "key_id,x_numerator,coordinate_margin,Nz,Ez\n";
        for (const auto& [key, weight] : local)
            out << key.key << ',' << key.x_numerator << ',' << key.margin << ','
                << weight << ',' << (key.margin <= 0 ? weight : Weight{}) << '\n';
    }
    {
        std::ofstream out(output / "recovery-metadata.json");
        out << "{\n  \"parameters\": \"" << p.id() << "\",\n"
            << "  \"key_count\": " << key_count << ",\n"
            << "  \"seed\": " << seed << ",\n"
            << "  \"y_mode\": \"" << (sampled_y ? "sampled" : "exact") << "\",\n"
            << "  \"sample_y\": " << sampled_y << "\n}\n";
    }
}

} // namespace

int main(int argc, char** argv) {
    try {
        std::string preset, output;
        std::size_t key_count = 128, sampled_y = 0;
        std::uint64_t seed = 0;
        for (int i = 1; i < argc; ++i) {
            const std::string arg = argv[i];
            auto value = [&]() -> std::string {
                if (++i >= argc) throw std::invalid_argument("missing value for " + arg);
                return argv[i];
            };
            if (arg == "--preset") preset = value();
            else if (arg == "--output") output = value();
            else if (arg == "--sample-keys") key_count = std::stoull(value());
            else if (arg == "--sample-y") sampled_y = std::stoull(value());
            else if (arg == "--seed") seed = std::stoull(value());
            else throw std::invalid_argument("unknown option: " + arg);
        }
        if (preset.empty() || output.empty())
            throw std::invalid_argument("--preset and --output are required");
        recover(Params::preset(preset), key_count, sampled_y, seed, output);
        std::cout << "recovered " << preset << " coordinate law in " << output << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
}
