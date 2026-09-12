#pragma once

#include <string>

#include "toy_mlkem/pke.hpp"

namespace toy {

std::string encode_poly(const Poly& poly);
std::string feature_pk(const Matrix& a, const ModuleVector& t);
std::string feature_secret_key(const Matrix& a, const ModuleVector& s, const ModuleVector& e);
std::string feature_ciphertext(const Ciphertext& c);
std::string feature_pk_ciphertext(const Matrix& a, const ModuleVector& t, const Ciphertext& c);
std::string feature_t_centered_norm(const ModuleVector& t, int q);
std::string feature_t_histogram(const ModuleVector& t, int q);
std::string feature_t_autocorrelation(const ModuleVector& t, int q);
std::string feature_ciphertext_symbols(const Ciphertext& c, int du, int dv);
std::string feature_at_norm_pair(const Matrix& a, const ModuleVector& t, int q);
std::string feature_at_pair_histogram(const Matrix& a, const ModuleVector& t, int q);
std::string feature_at_correlations(const Matrix& a, const ModuleVector& t, int q, std::size_t shifts = 4);
std::string feature_at_projections(const Matrix& a, const ModuleVector& t, int q);
std::string feature_hist_u(const Ciphertext& c, int symbols);
std::string feature_hist_v(const Ciphertext& c, int symbols);
std::string feature_extreme_symbol_counts(const Ciphertext& c, int u_symbols, int v_symbols);
std::string feature_entropy_1024(const Ciphertext& c, int u_symbols, int v_symbols);
std::string feature_decompressed_norms(const Ciphertext& c, int du, int dv, int q);
std::string feature_joint_uv_histogram(const Ciphertext& c);

} // namespace toy
