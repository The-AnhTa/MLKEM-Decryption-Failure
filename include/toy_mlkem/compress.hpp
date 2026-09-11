#pragma once

#include "toy_mlkem/ring.hpp"

namespace toy {

int compress_coeff(int x, int d, int q);
int decompress_coeff(int y, int d, int q);
Poly compress_poly(const Poly& x, int d, int q);
Poly decompress_poly(const Poly& y, int d, int q);

} // namespace toy

