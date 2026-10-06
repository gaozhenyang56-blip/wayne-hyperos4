// Focused host check using unmodified AOSP libvintf; not full checkvintf/APEX validation.
#include <fstream>
#include <iostream>
#include <vector>
#include <vintf/HalManifest.h>
#include <vintf/CompatibilityMatrix.h>
#include <vintf/parse_xml.h>

using namespace android::vintf;
// Use AOSP's existing test friend to expose the unchanged combination algorithm.
namespace android::vintf {
struct FrameworkCompatibilityMatrixCombineTest {
    static auto combine(Level level, std::vector<CompatibilityMatrix>* matrices,
                        std::string* error) {
        return CompatibilityMatrix::combine(level, level, matrices, error);
    }
};
struct LibVintfTest {
    static auto unused(const HalManifest& manifest, const CompatibilityMatrix& matrix) {
        // Conservative: no generated HIDL inheritance metadata is available here.
        return manifest.checkUnusedHals(matrix, {});
    }
};
}
static std::string read(const char* path) {
    std::ifstream stream(path);
    if (!stream) throw std::runtime_error(std::string("Cannot open ")+path);
    return std::string(std::istreambuf_iterator<char>(stream), {});
}
int main(int argc, char** argv) {
    try {
        if (argc < 3) throw std::runtime_error("Usage: checker vendor-manifest manifest-fragment... matrix...");
        HalManifest manifest;
        std::string error;
        if (!fromXml(&manifest, read(argv[1]), &error)) throw std::runtime_error(error);
        std::vector<CompatibilityMatrix> matrices;
        for (int i=2;i<argc;++i) {
            auto xml=read(argv[i]);
            if (xml.find("<manifest") != std::string::npos) {
                HalManifest fragment;
                if (!fromXml(&fragment,xml,&error) || !manifest.addAllHals(&fragment,&error))
                    throw std::runtime_error(std::string(argv[i])+": "+error);
                continue;
            }
            CompatibilityMatrix matrix;
            if (!fromXml(&matrix,xml,&error)) throw std::runtime_error(std::string(argv[i])+": "+error);
            matrices.push_back(std::move(matrix));
        }
        auto combined=FrameworkCompatibilityMatrixCombineTest::combine(manifest.level(),&matrices,&error);
        if (!combined) throw std::runtime_error(error);
        if (!manifest.checkCompatibility(*combined,&error)) {
            std::cerr << "INCOMPATIBLE\n" << error << "\n";
            return 1;
        }
        auto unmatched=LibVintfTest::unused(manifest,*combined);
        if (!unmatched.empty()) {
            std::cerr << "UNMATCHED HAL DECLARATIONS (no HIDL inheritance metadata)\n";
            for (const auto& entry:unmatched) std::cerr << entry << "\n";
            return 1;
        }
        std::cout << "HAL manifest/framework matrix compatibility passed.\n"
                  << "Runtime kernel, APEX manifests and linker namespaces are not covered.\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << "\n";
        return 2;
    }
}
