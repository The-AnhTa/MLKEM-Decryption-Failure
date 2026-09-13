#pragma once

#include <map>
#include <string>
#include <vector>

#include "toy_mlkem/features.hpp"
#include "toy_mlkem/stats.hpp"

namespace toy {

enum class Ablation { None, NoCompression, IndependentCompression };

std::string ablation_name(Ablation mode);
Ablation parse_ablation(const std::string& name);

struct ExperimentResult {
    std::map<std::string, JointLaw> laws;
    std::vector<Weight> coordinate_total;
    std::vector<Weight> coordinate_correct;
    std::map<std::string, std::string> metadata;
    std::map<std::string, std::vector<Cell>> pk_coordinate_laws;
};

ExperimentResult enumerate_bruteforce(const Params& p, bool ciphertext_features = true);
ExperimentResult enumerate_ciphertext_dp(const Params& p, Ablation mode = Ablation::None,
                                         std::size_t max_outer_states = 0,
                                         bool scalable_only = false,
                                         bool normalized_only = false,
                                         bool mechanism_only = false);
ExperimentResult enumerate_frozen_public(const Params& p, std::size_t max_keys = 0);
ExperimentResult enumerate_optimized_pk(const Params& p, Ablation mode = Ablation::None,
                                        std::size_t max_outer_states = 0);
ExperimentResult enumerate_sampled_keys(const Params& p, std::size_t key_count,
                                        std::uint64_t seed, Ablation mode = Ablation::None,
                                        std::size_t max_outer_per_key = 0,
                                        bool screen_only = false);
ExperimentResult enumerate_sampled_ciphertext_features(const Params& p, std::size_t key_count,
                                                       std::uint64_t seed,
                                                       std::size_t max_outer_per_key = 0,
                                                       bool normalized_only = false,
                                                       bool mechanism_only = false);
void export_result(const ExperimentResult& result, const Params& p,
                   Ablation mode, const std::string& directory);

} // namespace toy
