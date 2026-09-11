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

} // namespace toy

