#pragma once

#include <cstddef>
#include <string>

namespace toy {

struct Params {
    std::size_t n{};
    std::size_t k{};
    int q{};
    int eta1{};
    int eta2{};
    int du{};
    int dv{};

    void validate() const;
    std::string id() const;
    static Params e0();
    static Params preset(const std::string& name);
};

} // namespace toy

