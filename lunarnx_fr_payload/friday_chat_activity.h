#pragma once
#ifdef __SWITCH__
#include <borealis.hpp>
#include "../app/stream_runtime.h"
#include <atomic>
#include <memory>
#include <string>

namespace lunar::ui {

// Optional assistant. It never controls the PS5 nor the streaming engine.
class FridayChatActivity : public brls::Activity {
public:
    explicit FridayChatActivity(std::shared_ptr<app::IStreamRuntime> runtime = {});
    ~FridayChatActivity() override;
    brls::View* createContentView() override;

private:
    void askFriday();
    std::shared_ptr<app::IStreamRuntime> runtime_;
    std::shared_ptr<std::atomic<bool>> alive_ = std::make_shared<std::atomic<bool>>(true);
    brls::Label* response_ = nullptr;
    std::string question_;
    bool busy_ = false; // Only accessed on the UI thread.
};

} // namespace lunar::ui
#endif
