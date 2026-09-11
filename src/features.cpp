#include "toy_mlkem/features.hpp"

#include <map>
#include <sstream>

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

} // namespace toy
