#!/usr/bin/env python3
"""Install FRIDAY diagnostic/chat without changing the remote-play transport."""
from pathlib import Path
import shutil
import sys

base = Path(sys.argv[1]).resolve()
payload = Path(__file__).resolve().parent

def edit(path, changes):
    target = base / path
    source = target.read_text(encoding="utf-8")
    for anchor, replacement in changes:
        n = source.count(anchor)
        if n != 1:
            raise RuntimeError(f"{path}: expected exactly one match, got {n}: {anchor[:90]!r}")
        source = source.replace(anchor, replacement, 1)
    target.write_text(source, encoding="utf-8")
    print(f"FRIDAY patched {path}")

for name in ("friday_chat_activity.h", "friday_chat_activity.cpp"):
    shutil.copyfile(payload / name, base / "src" / "ui" / name)
    print(f"FRIDAY copied src/ui/{name}")

edit("Makefile.switch", [
    ("    src/ui/perf_overlay.cpp src/ui/stream_overlay.cpp \\",
     "    src/ui/friday_chat_activity.cpp src/ui/perf_overlay.cpp src/ui/stream_overlay.cpp \\"),
])

edit("src/ui/ps_settings_activity.h", [
    ("""    int fr_accent_theme = 0;
""", """    int fr_accent_theme = 0;
    bool friday_antlag_enabled = true;
    std::string friday_gateway_url;
    std::string friday_gateway_token;
"""),
])

edit("src/ui/ps_settings_activity.cpp", [
    ("""#include "button_mapping_activity.h"
""", """#include "button_mapping_activity.h"
#include "friday_chat_activity.h"
"""),
    ("""    if (cJSON_IsNumber(accent)) out.fr_accent_theme = std::clamp(accent->valueint, 0, 3);
    cJSON_Delete(root);""", """    if (cJSON_IsNumber(accent)) out.fr_accent_theme = std::clamp(accent->valueint, 0, 3);
    const cJSON* fr_antlag = cJSON_GetObjectItem(root, "friday_antlag_enabled");
    if (cJSON_IsBool(fr_antlag)) out.friday_antlag_enabled = cJSON_IsTrue(fr_antlag);
    const cJSON* fr_url = cJSON_GetObjectItem(root, "friday_gateway_url");
    if (cJSON_IsString(fr_url) && fr_url->valuestring)
        out.friday_gateway_url = fr_url->valuestring;
    const cJSON* fr_token = cJSON_GetObjectItem(root, "friday_gateway_token");
    if (cJSON_IsString(fr_token) && fr_token->valuestring)
        out.friday_gateway_token = fr_token->valuestring;
    cJSON_Delete(root);"""),
    ("""    cJSON_AddNumberToObject(root, "fr_accent_theme", settings.fr_accent_theme);
    bool ok = writeConfig(root);""", """    cJSON_AddNumberToObject(root, "fr_accent_theme", settings.fr_accent_theme);
    cJSON_DeleteItemFromObject(root, "friday_antlag_enabled");
    cJSON_AddBoolToObject(root, "friday_antlag_enabled", settings.friday_antlag_enabled);
    cJSON_DeleteItemFromObject(root, "friday_gateway_url");
    cJSON_AddStringToObject(root, "friday_gateway_url", settings.friday_gateway_url.c_str());
    cJSON_DeleteItemFromObject(root, "friday_gateway_token");
    cJSON_AddStringToObject(root, "friday_gateway_token", settings.friday_gateway_token.c_str());
    bool ok = writeConfig(root);"""),
    ("""    plus->addView(reconnect);
    auto* theme = new brls::SelectorCell();""", """    plus->addView(reconnect);

    auto* friday_antlag = new brls::BooleanCell();
    friday_antlag->init("FRIDAY anti-lag (alertes locales)", settings_.friday_antlag_enabled,
        [this](bool enabled) { settings_.friday_antlag_enabled = enabled; });
    plus->addView(friday_antlag);

    auto* friday_chat = new brls::DetailCell();
    friday_chat->setText("FRIDAY Chat");
    friday_chat->setDetailText("Conseils locaux ou conversation IA (facultative)");
    friday_chat->registerClickAction([](brls::View*) -> bool {
        brls::Application::pushActivity(
            new FridayChatActivity(), brls::TransitionAnimation::NONE);
        return true;
    });
    plus->addView(friday_chat);

    auto* friday_url = new brls::InputCell();
    friday_url->init("Serveur FRIDAY (HTTPS)", settings_.friday_gateway_url,
        [this](std::string url) { settings_.friday_gateway_url = std::move(url); },
        "Adresse HTTPS de ta passerelle IA",
        "https://ton-serveur.example/ask", 255, 0);
    plus->addView(friday_url);

    auto* friday_token = new brls::InputCell();
    friday_token->init("Code FRIDAY (facultatif)", "",
        [this](std::string token) {
            if (!token.empty()) settings_.friday_gateway_token = std::move(token);
        },
        "Code de la passerelle ; ne mets PAS ta clé OpenAI",
        "Code secret de 16 caractères minimum", 180, 0);
    plus->addView(friday_token);

    auto* clear_token = new brls::DetailCell();
    clear_token->setText("Effacer le code FRIDAY");
    clear_token->setDetailText("Retirer l'accès IA de la configuration locale");
    clear_token->registerClickAction([this](brls::View*) -> bool {
        settings_.friday_gateway_token.clear();
        brls::Application::notify("Code FRIDAY effacé : valide les paramètres.");
        return true;
    });
    plus->addView(clear_token);

    auto* theme = new brls::SelectorCell();"""),
])

edit("src/ui/stream_view.cpp", [
    ("""    uint32_t last_frames = 0;
    while (running_) {""", """    uint32_t last_frames = 0;
    const bool friday_antlag = runtime_->getStreamPlatform() ==
        app::StreamPlatform::PlayStation && loadPsSettings().friday_antlag_enabled;
    unsigned friday_bad_samples = 0;
    auto friday_last_alert = steady_clock::now();
    while (running_) {"""),
    ("""        last_stats = now;

        if (disconnect_armed_.load()) {""", """        last_stats = now;

        // Lightweight local FRIDAY monitor. No network, no model and no
        // adjustments to the video session. Only a rate-limited suggestion.
        if (friday_antlag && !backgrounded_.load() &&
            !child_activity_visible_ &&
            runtime_->getState() == app::StreamState::Streaming) {
            const float loss = p.ps_packet_loss_fraction.load();
            const uint32_t rtt = p.ps_rtt_ms.load();
            const bool degraded = (loss > 0.035f && loss <= 1.0f) ||
                (rtt > 140 && rtt < 10000);
            friday_bad_samples = degraded
                ? std::min(friday_bad_samples + 1, 40u)
                : (friday_bad_samples > 1 ? friday_bad_samples - 2 : 0u);
            if (friday_bad_samples >= 12 &&
                now - friday_last_alert >= seconds(90)) {
                const std::string hint = loss > 0.035f
                    ? "FRIDAY : pertes réseau élevées. Essaie le Wi-Fi 5 GHz et 720p."
                    : "FRIDAY : latence élevée. Vérifie le routeur et le Wi-Fi.";
                auto alive = alive_;
                brls::sync([alive, hint]() {
                    if (alive->load()) brls::Application::notify(hint);
                });
                friday_bad_samples = 0;
                friday_last_alert = now;
            }
        } else {
            friday_bad_samples = 0;
        }

        if (disconnect_armed_.load()) {"""),
])
print("FRIDAY integration complete. The PS5 streaming implementation is unchanged.")
