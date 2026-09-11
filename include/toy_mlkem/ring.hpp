#pragma once

#include <vector>

#include "toy_mlkem/params.hpp"

namespace toy {

using Poly = std::vector<int>;
using ModuleVector = std::vector<Poly>;
using Matrix = std::vector<std::vector<Poly>>;

int mod_q(long long value, int q);
int centered(int value, int q);
Poly add(const Poly& a, const Poly& b, int q);
Poly sub(const Poly& a, const Poly& b, int q);
Poly negacyclic_mul(const Poly& a, const Poly& b, int q);
Poly dot(const ModuleVector& a, const ModuleVector& b, int q);
ModuleVector mat_vec(const Matrix& a, const ModuleVector& x, const ModuleVector& error, int q);
ModuleVector transpose_mat_vec(const Matrix& a, const ModuleVector& x, const ModuleVector& error, int q);

} // namespace toy

