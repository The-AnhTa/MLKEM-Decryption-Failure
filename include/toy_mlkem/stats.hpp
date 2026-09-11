#pragma once

#include <cstdint>
#include <map>
#include <string>

#include "toy_mlkem/cbd.hpp"

namespace toy {

struct Cell {
    Weight total{};
    Weight failures{};
    bool operator==(const Cell&) const = default;
};

class JointLaw {
public:
    void add(const std::string& feature, Weight total, Weight failures);
    Weight total() const;
    Weight failures() const;
    const std::map<std::string, Cell>& cells() const { return cells_; }
    void validate() const;

private:
    std::map<std::string, Cell> cells_;
};

void export_csv(const std::string& path, const std::string& feature_id, const JointLaw& law);
void export_metadata(const std::string& path, const std::string& params_id,
                     const std::string& mode, const std::map<std::string, JointLaw>& laws,
                     const std::map<std::string, std::string>& extra);

} // namespace toy
