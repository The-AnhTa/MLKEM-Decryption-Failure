#include "toy_mlkem/enumerate.hpp"

#include <chrono>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    try {
        std::string preset = "e0";
        std::string mode_name = "none";
        std::string output = "results/e0/none";
        std::size_t max_outer = 0;
        std::size_t sample_keys = 0;
        std::uint64_t seed = 1;
        bool brute_force = false;
        bool ciphertext_dp = false;
        bool scalable_only = false;
        bool frozen_public = false;
        bool support_bound = false;
        bool screen_only = false;
        bool normalized_transfer = false;
        bool mechanism_reduction = false;

        for (int i = 1; i < argc; ++i) {
            const std::string arg = argv[i];
            auto value = [&](const char* option) -> std::string {
                if (++i >= argc) throw std::invalid_argument(std::string("missing value for ") + option);
                return argv[i];
            };
            if (arg == "--preset") preset = value("--preset");
            else if (arg == "--mode") mode_name = value("--mode");
            else if (arg == "--output") output = value("--output");
            else if (arg == "--max-outer") max_outer = std::stoull(value("--max-outer"));
            else if (arg == "--sample-keys") sample_keys = std::stoull(value("--sample-keys"));
            else if (arg == "--screen-keys") {
                sample_keys = std::stoull(value("--screen-keys"));
                screen_only = true;
            }
            else if (arg == "--seed") seed = std::stoull(value("--seed"));
            else if (arg == "--bruteforce") brute_force = true;
            else if (arg == "--ciphertext-dp") ciphertext_dp = true;
            else if (arg == "--scalable-only") scalable_only = true;
            else if (arg == "--frozen-public") frozen_public = true;
            else if (arg == "--support-bound") support_bound = true;
            else if (arg == "--normalized-transfer") normalized_transfer = true;
            else if (arg == "--mechanism-reduction") mechanism_reduction = true;
            else if (arg == "--list-presets") {
                std::cout << "e0 e1 e1a e1b e1c e2 e3 e4 e5 "
                             "n4q17d32 n4q17d42 n4q17d43 n4q19d32 n4q19d42 n4q19d43 "
                             "n4q23d32 n4q23d42 n4q23d43 n4q29d32 n4q29d42 n4q29d43\n";
                return 0;
            } else if (arg == "--help") {
                std::cout << "toy-mlkem [--preset e0] [--mode none|no-compression|independent-compression]\n"
                             "          [--output DIR] [--max-outer N] [--bruteforce|--ciphertext-dp]\n"
                             "          [--sample-keys N|--screen-keys N --seed N] [--scalable-only|--frozen-public]\n"
                             "          [--support-bound] [--normalized-transfer|--mechanism-reduction]\n";
                return 0;
            } else throw std::invalid_argument("unknown option: " + arg);
        }

        const auto params = toy::Params::preset(preset);
        params.validate();
        const auto mode = toy::parse_ablation(mode_name);
        if (support_bound) {
            const auto bound = toy::noise_support_bound(params);
            std::filesystem::create_directories(output);
            std::ofstream out(std::filesystem::path(output) / "support_bound.json");
            out << "{\n  \"parameters\": \"" << params.id() << "\",\n"
                << "  \"terms\": {\"ey\": " << bound.ey << ", \"se1\": " << bound.se1
                << ", \"e2\": " << bound.e2 << ", \"scu\": " << bound.scu
                << ", \"cv\": " << bound.cv << "},\n"
                << "  \"total_noise_bound\": " << bound.total << ",\n"
                << "  \"decoding_margin\": " << bound.decoding_margin << ",\n"
                << "  \"failure_impossible\": " << (bound.failure_impossible ? "true" : "false") << "\n}\n";
            std::cout << "parameters=" << params.id() << " noise_bound=" << bound.total
                      << " decoding_margin=" << bound.decoding_margin
                      << " failure_impossible=" << (bound.failure_impossible ? "true" : "false") << '\n';
            return 0;
        }
        if (brute_force && mode != toy::Ablation::None)
            throw std::invalid_argument("the brute-force CLI currently models the exact scheme only");
        if (ciphertext_dp && mode == toy::Ablation::IndependentCompression)
            throw std::invalid_argument("ciphertext observables are undefined for independent-compression mode");
        if (scalable_only && !ciphertext_dp && !sample_keys)
            throw std::invalid_argument("--scalable-only requires --ciphertext-dp or --sample-keys");
        if (normalized_transfer && !ciphertext_dp && !sample_keys)
            throw std::invalid_argument("--normalized-transfer requires --ciphertext-dp or --sample-keys");
        if (normalized_transfer && mode != toy::Ablation::None)
            throw std::invalid_argument("--normalized-transfer is defined only for the exact-compression mode");
        if (mechanism_reduction && !ciphertext_dp && !sample_keys)
            throw std::invalid_argument("--mechanism-reduction requires --ciphertext-dp or --sample-keys");
        if (mechanism_reduction && mode != toy::Ablation::None)
            throw std::invalid_argument("--mechanism-reduction is defined only for the exact-compression mode");
        if (mechanism_reduction && normalized_transfer)
            throw std::invalid_argument("choose one focused ciphertext observer");
        if (static_cast<int>(brute_force) + static_cast<int>(ciphertext_dp) +
            static_cast<int>(sample_keys != 0) + static_cast<int>(frozen_public) > 1)
            throw std::invalid_argument("choose only one enumeration driver");

        const auto start = std::chrono::steady_clock::now();
        toy::ExperimentResult result;
        if (brute_force) result = toy::enumerate_bruteforce(params, true);
        else if (ciphertext_dp) result = toy::enumerate_ciphertext_dp(params, mode, max_outer, scalable_only,
                                                                     normalized_transfer, mechanism_reduction);
        else if (frozen_public) result = toy::enumerate_frozen_public(params, max_outer);
        else if (sample_keys && (scalable_only || normalized_transfer || mechanism_reduction)) {
            if (mode != toy::Ablation::None) throw std::invalid_argument("sampled scalable ciphertext supports exact compression only");
            result = toy::enumerate_sampled_ciphertext_features(params, sample_keys, seed, max_outer,
                                                                normalized_transfer, mechanism_reduction);
        } else if (sample_keys)
            result = toy::enumerate_sampled_keys(params, sample_keys, seed, mode, max_outer, screen_only);
        else result = toy::enumerate_optimized_pk(params, mode, max_outer);
        toy::export_result(result, params, mode, output);
        const auto elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
        const auto& global = result.laws.at("global");
        std::cout << "parameters=" << params.id() << " mode=" << mode_name
                  << " N=" << global.total() << " E=" << global.failures()
                  << " seconds=" << elapsed << "\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
}
