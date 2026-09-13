#include "toy_mlkem/features.hpp"

#include <map>
#include <cmath>
#include <sstream>
#include <stdexcept>

namespace toy {

std::string encode_poly(const Poly& poly) {
    std::ostringstream out;
    for (std::size_t i = 0; i < poly.size(); ++i) {
        if (i) out << '.';
        out << poly[i];
    }
    return out.str();
}

static void append_vector(std::ostringstream& out, const ModuleVector& value) {
    for (std::size_t i = 0; i < value.size(); ++i) {
        if (i) out << '/';
        out << encode_poly(value[i]);
    }
}

std::string feature_pk(const Matrix& a, const ModuleVector& t) {
    std::ostringstream out;
    out << "A=";
    for (std::size_t i = 0; i < a.size(); ++i) for (std::size_t j = 0; j < a[i].size(); ++j) {
        if (i || j) out << '/';
        out << encode_poly(a[i][j]);
    }
    out << "|t=";
    append_vector(out, t);
    return out.str();
}

std::string feature_secret_key(const Matrix& a, const ModuleVector& s, const ModuleVector& e) {
    std::ostringstream out;
    out << feature_pk(a, s) << "|e=";
    append_vector(out, e);
    return out.str();
}

std::string feature_ciphertext(const Ciphertext& c) {
    std::ostringstream out;
    out << "u=";
    append_vector(out, c.u);
    out << "|v=" << encode_poly(c.v);
    return out.str();
}

std::string feature_pk_ciphertext(const Matrix& a, const ModuleVector& t, const Ciphertext& c) {
    return feature_pk(a, t) + "|" + feature_ciphertext(c);
}

std::string feature_t_centered_norm(const ModuleVector& t, int q) {
    long long norm2 = 0;
    for (const auto& poly : t) for (int x : poly) {
        const long long c = centered(x, q);
        norm2 += c * c;
    }
    return std::to_string(norm2);
}

std::string feature_t_histogram(const ModuleVector& t, int q) {
    std::map<int, int> counts;
    for (const auto& poly : t) for (int x : poly) ++counts[centered(x, q)];
    std::ostringstream out;
    for (const auto& [x, count] : counts) out << x << ':' << count << ';';
    return out.str();
}

std::string feature_t_autocorrelation(const ModuleVector& t, int q) {
    long long corr = 0;
    for (const auto& poly : t) for (std::size_t i = 0; i < poly.size(); ++i)
        corr += static_cast<long long>(centered(poly[i], q)) * centered(poly[(i + 1) % poly.size()], q);
    return std::to_string(corr);
}

std::string feature_ciphertext_symbols(const Ciphertext& c, int du, int dv) {
    std::vector<int> ucounts(std::size_t{1} << du), vcounts(std::size_t{1} << dv);
    for (const auto& poly : c.u) for (int x : poly) ++ucounts[x];
    for (int x : c.v) ++vcounts[x];
    std::ostringstream out;
    out << "u:";
    for (int x : ucounts) out << x << '.';
    out << "|v:";
    for (int x : vcounts) out << x << '.';
    return out.str();
}

static long long centered_norm2(const ModuleVector& values, int q) {
    long long result = 0;
    for (const auto& poly : values) for (int x : poly) {
        const long long value = centered(x, q);
        result += value * value;
    }
    return result;
}

std::string feature_at_norm_pair(const Matrix& a, const ModuleVector& t, int q) {
    long long a_norm = 0;
    for (const auto& row : a) a_norm += centered_norm2(row, q);
    return "A=" + std::to_string(a_norm) + "|t=" + std::to_string(centered_norm2(t, q));
}

std::string feature_at_pair_histogram(const Matrix& a, const ModuleVector& t, int q) {
    std::map<std::pair<int, int>, int> counts;
    for (std::size_t i = 0; i < a.size(); ++i)
        for (std::size_t j = 0; j < a[i].size(); ++j)
            for (std::size_t r = 0; r < a[i][j].size(); ++r)
                ++counts[{centered(a[i][j][r], q), centered(t[i][r], q)}];
    std::ostringstream out;
    for (const auto& [pair, count] : counts) out << pair.first << ':' << pair.second << ':' << count << ';';
    return out.str();
}

std::string feature_at_correlations(const Matrix& a, const ModuleVector& t, int q, std::size_t shifts) {
    std::ostringstream out;
    const std::size_t n = t.front().size();
    for (std::size_t shift = 0; shift < std::min(shifts, n); ++shift) {
        long long value = 0;
        for (std::size_t i = 0; i < a.size(); ++i)
            for (std::size_t j = 0; j < a[i].size(); ++j)
                for (std::size_t r = 0; r < n; ++r)
                    value += static_cast<long long>(centered(a[i][j][r], q)) * centered(t[i][(r + shift) % n], q);
        if (shift) out << '.';
        out << value;
    }
    return out.str();
}

std::string feature_at_projections(const Matrix& a, const ModuleVector& t, int q) {
    long long projections[4]{};
    std::size_t index = 0;
    auto consume = [&](int raw) {
        const long long x = centered(raw, q);
        projections[0] += x;
        projections[1] += static_cast<long long>((index % 5) + 1) * x;
        projections[2] += (index % 2 ? -1LL : 1LL) * x;
        projections[3] += static_cast<long long>(((index * 3 + 1) % 7) - 3) * x;
        ++index;
    };
    for (const auto& row : a) for (const auto& poly : row) for (int x : poly) consume(x);
    for (const auto& poly : t) for (int x : poly) consume(x);
    std::ostringstream out;
    for (std::size_t i = 0; i < 4; ++i) { if (i) out << '.'; out << projections[i]; }
    return out.str();
}

static std::string histogram(const std::vector<int>& counts) {
    std::ostringstream out;
    for (int value : counts) out << value << '.';
    return out.str();
}

std::string feature_hist_u(const Ciphertext& c, int symbols) {
    std::vector<int> counts(symbols);
    for (const auto& poly : c.u) for (int x : poly) ++counts.at(static_cast<std::size_t>(x));
    return histogram(counts);
}

std::string feature_hist_v(const Ciphertext& c, int symbols) {
    std::vector<int> counts(symbols);
    for (int x : c.v) ++counts.at(static_cast<std::size_t>(x));
    return histogram(counts);
}

std::string feature_extreme_symbol_counts(const Ciphertext& c, int u_symbols, int v_symbols) {
    int u_zero = 0, u_max = 0, v_zero = 0, v_max = 0;
    for (const auto& poly : c.u) for (int x : poly) { u_zero += x == 0; u_max += x == u_symbols - 1; }
    for (int x : c.v) { v_zero += x == 0; v_max += x == v_symbols - 1; }
    return std::to_string(u_zero) + '.' + std::to_string(u_max) + '.' +
           std::to_string(v_zero) + '.' + std::to_string(v_max);
}

static long long entropy_1024(const std::vector<int>& counts, int total) {
    double entropy = 0.0;
    for (int count : counts) if (count) {
        const double probability = static_cast<double>(count) / total;
        entropy -= probability * std::log2(probability);
    }
    return std::llround(entropy * 1024.0);
}

std::string feature_entropy_1024(const Ciphertext& c, int u_symbols, int v_symbols) {
    std::vector<int> uc(u_symbols), vc(v_symbols);
    int usize = 0;
    for (const auto& poly : c.u) for (int x : poly) { ++uc.at(static_cast<std::size_t>(x)); ++usize; }
    for (int x : c.v) ++vc.at(static_cast<std::size_t>(x));
    return std::to_string(entropy_1024(uc, usize)) + '.' +
           std::to_string(entropy_1024(vc, static_cast<int>(c.v.size())));
}

std::string feature_decompressed_norms(const Ciphertext& c, int du, int dv, int q) {
    ModuleVector uhat;
    for (const auto& poly : c.u) uhat.push_back(decompress_poly(poly, du, q));
    const ModuleVector vhat{decompress_poly(c.v, dv, q)};
    return std::to_string(centered_norm2(uhat, q)) + '.' + std::to_string(centered_norm2(vhat, q));
}

std::string feature_joint_uv_histogram(const Ciphertext& c) {
    if (c.u.empty() || c.u.front().size() != c.v.size()) return "unsupported";
    std::map<std::pair<int, int>, int> counts;
    for (std::size_t j = 0; j < c.u.size(); ++j)
        for (std::size_t i = 0; i < c.v.size(); ++i) ++counts[{c.u[j][i], c.v[i]}];
    std::ostringstream out;
    for (const auto& [pair, count] : counts) out << pair.first << ':' << pair.second << ':' << count << ';';
    return out.str();
}

int normalized_coordinate_bin(int residue, int q) {
    if (q <= 2 || (q % 2) == 0) throw std::invalid_argument("normalized binning requires odd q > 2");
    const int value = centered(residue, q);
    const long long scaled = 4LL * value;
    if (scaled < -q) return 0;
    if (value < 0) return 1;
    if (scaled < q) return 2;
    return 3;
}

NormalizedJointHistogram normalized_joint_histogram(const Ciphertext& c, int du, int dv, int q) {
    if (c.u.size() != 1 || c.u.front().size() != c.v.size() || c.v.empty())
        throw std::invalid_argument("normalized joint histogram currently requires k=1 and aligned nonempty u,v");
    NormalizedJointHistogram counts{};
    for (std::size_t i = 0; i < c.v.size(); ++i) {
        const int ubin = normalized_coordinate_bin(decompress_coeff(c.u[0][i], du, q), q);
        const int vbin = normalized_coordinate_bin(decompress_coeff(c.v[i], dv, q), q);
        ++counts[static_cast<std::size_t>(4 * ubin + vbin)];
    }
    return counts;
}

std::array<int, 4> normalized_u_marginal(const NormalizedJointHistogram& histogram) {
    std::array<int, 4> out{};
    for (std::size_t u = 0; u < 4; ++u)
        for (std::size_t v = 0; v < 4; ++v) out[u] += histogram[4 * u + v];
    return out;
}

std::array<int, 4> normalized_v_marginal(const NormalizedJointHistogram& histogram) {
    std::array<int, 4> out{};
    for (std::size_t u = 0; u < 4; ++u)
        for (std::size_t v = 0; v < 4; ++v) out[v] += histogram[4 * u + v];
    return out;
}

std::string encode_normalized_histogram(const NormalizedJointHistogram& histogram) {
    std::ostringstream out;
    for (std::size_t i = 0; i < histogram.size(); ++i) {
        if (i) out << '.';
        out << histogram[i];
    }
    return out.str();
}

std::string feature_normalized_uv_margin(const Ciphertext& c, int du, int dv, int q, int margin) {
    return encode_normalized_histogram(normalized_joint_histogram(c, du, dv, q)) + "|M=" +
           std::to_string(margin);
}

std::string feature_symbol_histogram_margin(const Ciphertext& c, int du, int dv, int margin) {
    if (c.u.size() != 1 || c.u.front().size() != c.v.size() || c.v.empty())
        throw std::invalid_argument("symbol histogram currently requires k=1 and aligned nonempty u,v");
    std::vector<int> u_counts(static_cast<std::size_t>(std::uint64_t{1} << du));
    std::vector<int> v_counts(static_cast<std::size_t>(std::uint64_t{1} << dv));
    for (int symbol : c.u[0]) ++u_counts.at(static_cast<std::size_t>(symbol));
    for (int symbol : c.v) ++v_counts.at(static_cast<std::size_t>(symbol));
    auto encode = [](const std::vector<int>& counts) {
        std::ostringstream out;
        for (std::size_t i = 0; i < counts.size(); ++i) {
            if (i) out << '.';
            out << counts[i];
        }
        return out.str();
    };
    return "U=" + encode(u_counts) + "|V=" + encode(v_counts) + "|M=" + std::to_string(margin);
}

} // namespace toy
