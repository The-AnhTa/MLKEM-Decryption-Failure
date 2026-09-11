#include "toy_mlkem/enumerate.hpp"

#include <chrono>
#include <exception>
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
            else if (arg == "--seed") seed = std::stoull(value("--seed"));
            else if (arg == "--bruteforce") brute_force = true;
            else if (arg == "--ciphertext-dp") ciphertext_dp = true;
            else if (arg == "--list-presets") {
                std::cout << "e0 e1 e2 e3 e4 e5\n";
                return 0;
            } else if (arg == "--help") {
                std::cout << "toy-mlkem [--preset e0] [--mode none|no-compression|independent-compression]\n"
                             "          [--output DIR] [--max-outer N] [--bruteforce|--ciphertext-dp]\n"
                             "          [--sample-keys N --seed N]\n";
                return 0;
            } else throw std::invalid_argument("unknown option: " + arg);
        }

        const auto params = toy::Params::preset(preset);
        params.validate();
        const auto mode = toy::parse_ablation(mode_name);
        if (brute_force && mode != toy::Ablation::None)
            throw std::invalid_argument("the brute-force CLI currently models the exact scheme only");
        if (ciphertext_dp && mode != toy::Ablation::None)
            throw std::invalid_argument("ciphertext DP currently models the exact scheme only");
        if (static_cast<int>(brute_force) + static_cast<int>(ciphertext_dp) + static_cast<int>(sample_keys != 0) > 1)
            throw std::invalid_argument("choose only one of --bruteforce, --ciphertext-dp, or --sample-keys");

        const auto start = std::chrono::steady_clock::now();
        toy::ExperimentResult result;
        if (brute_force) result = toy::enumerate_bruteforce(params, true);
        else if (ciphertext_dp) result = toy::enumerate_ciphertext_dp(params, max_outer);
        else if (sample_keys) result = toy::enumerate_sampled_keys(params, sample_keys, seed, mode, max_outer);
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
