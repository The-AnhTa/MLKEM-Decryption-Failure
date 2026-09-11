#include "toy_mlkem/stats.hpp"

#include <filesystem>
#include <fstream>
#include <stdexcept>

namespace toy {

void JointLaw::add(const std::string& feature, Weight total_weight, Weight failure_weight) {
    if (failure_weight > total_weight) throw std::invalid_argument("failure weight exceeds total weight");
    auto& cell = cells_[feature];
    cell.total = checked_add(cell.total, total_weight);
    cell.failures = checked_add(cell.failures, failure_weight);
}

Weight JointLaw::total() const {
    Weight out = 0;
    for (const auto& [_, cell] : cells_) out = checked_add(out, cell.total);
    return out;
}

Weight JointLaw::failures() const {
    Weight out = 0;
    for (const auto& [_, cell] : cells_) out = checked_add(out, cell.failures);
    return out;
}

void JointLaw::validate() const {
    for (const auto& [_, cell] : cells_) if (cell.failures > cell.total) throw std::logic_error("invalid joint-law cell");
}

static std::string csv_escape(const std::string& text) {
    std::string out = "\"";
    for (char c : text) out += (c == '"') ? "\"\"" : std::string(1, c);
    return out + "\"";
}

void export_csv(const std::string& path, const std::string& feature_id, const JointLaw& law) {
    std::filesystem::create_directories(std::filesystem::path(path).parent_path());
    std::ofstream out(path);
    if (!out) throw std::runtime_error("cannot open output file: " + path);
    out << "feature_id,feature_value,Nz,Ez\n";
    for (const auto& [feature, cell] : law.cells())
        out << feature_id << ',' << csv_escape(feature) << ',' << cell.total << ',' << cell.failures << '\n';
}

void export_metadata(const std::string& path, const std::string& params_id,
                     const std::string& mode, const std::map<std::string, JointLaw>& laws,
                     const std::map<std::string, std::string>& extra) {
    std::filesystem::create_directories(std::filesystem::path(path).parent_path());
    std::ofstream out(path);
    if (!out) throw std::runtime_error("cannot open metadata file: " + path);
    out << "{\n  \"schema_version\": 1,\n  \"parameters\": \"" << params_id
        << "\",\n  \"mode\": \"" << mode << "\",\n  \"laws\": {\n";
    bool first = true;
    for (const auto& [name, law] : laws) {
        if (!first) out << ",\n";
        first = false;
        out << "    \"" << name << "\": {\"N\": \"" << law.total()
            << "\", \"E\": \"" << law.failures() << "\", \"cells\": " << law.cells().size() << '}';
    }
    out << "\n  },\n  \"run\": {";
    first = true;
    for (const auto& [name, value] : extra) {
        if (!first) out << ',';
        first = false;
        out << "\n    \"" << name << "\": \"" << value << "\"";
    }
    if (!extra.empty()) out << '\n';
    out << "  }\n}\n";
}

} // namespace toy
