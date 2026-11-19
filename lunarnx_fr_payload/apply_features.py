#!/usr/bin/env python3
"""Add French opt-in PlayStation UX improvements without rewriting the transport stack."""
from pathlib import Path
import sys

base = Path(sys.argv[1]).resolve()

def edit(path, changes):
    target = base / path
    source = target.read_text(encoding="utf-8")
    original = source
    for before, after in changes:
        count = source.count(before)
        if count != 1:
            raise RuntimeError(f"{path}: expected exactly one patch anchor, found {count}: {before[:85]!r}")
        source = source.replace(before, after, 1)
    if source == original:
        raise RuntimeError(f"{path}: no edits applied")
    target.write_text(source, encoding="utf-8")
    print(f"FR+ patched {path}")

edit("src/ui/ps_settings_activity.h", [
    ("#include <functional>", "#include <functional>\n#include <string>"),
    ("    int rumble_strength_percent = 50;\n", """    int rumble_strength_percent = 50;
    bool fr_smart_quality = false;
    bool fr_eco_mode = false;
    bool fr_stats_at_start = false;
    bool fr_quick_reconnect = true;
    int fr_accent_theme = 0;
"""),
    ("PsSettingsSnapshot loadPsSettings();", """PsSettingsSnapshot loadPsSettings();
void rememberLastPsConsole(const std::string& server_mac, bool remote);
std::string loadLastPsConsoleMac();
bool loadLastPsConsoleRemote();"""),
])

edit("src/ui/ps_settings_activity.cpp", [
    ("""    cJSON_Delete(root);
    return out;
}

bool savePsSettings""", """    const cJSON* smart = cJSON_GetObjectItem(root, "fr_smart_quality");
    if (cJSON_IsBool(smart)) out.fr_smart_quality = cJSON_IsTrue(smart);
    const cJSON* eco = cJSON_GetObjectItem(root, "fr_eco_mode");
    if (cJSON_IsBool(eco)) out.fr_eco_mode = cJSON_IsTrue(eco);
    const cJSON* stats = cJSON_GetObjectItem(root, "fr_stats_at_start");
    if (cJSON_IsBool(stats)) out.fr_stats_at_start = cJSON_IsTrue(stats);
    const cJSON* reconnect = cJSON_GetObjectItem(root, "fr_quick_reconnect");
    if (cJSON_IsBool(reconnect)) out.fr_quick_reconnect = cJSON_IsTrue(reconnect);
    const cJSON* accent = cJSON_GetObjectItem(root, "fr_accent_theme");
    if (cJSON_IsNumber(accent)) out.fr_accent_theme = std::clamp(accent->valueint, 0, 3);
    cJSON_Delete(root);
    return out;
}

void rememberLastPsConsole(const std::string& server_mac, bool remote) {
    if (server_mac.empty()) return;
    cJSON* root = readConfig();
    cJSON_DeleteItemFromObject(root, "fr_last_ps_mac");
    cJSON_AddStringToObject(root, "fr_last_ps_mac", server_mac.c_str());
    cJSON_DeleteItemFromObject(root, "fr_last_ps_remote");
    cJSON_AddBoolToObject(root, "fr_last_ps_remote", remote);
    writeConfig(root);
    cJSON_Delete(root);
}

std::string loadLastPsConsoleMac() {
    cJSON* root = readConfig();
    const cJSON* mac = cJSON_GetObjectItem(root, "fr_last_ps_mac");
    std::string result = cJSON_IsString(mac) && mac->valuestring ? mac->valuestring : "";
    cJSON_Delete(root);
    return result;
}

bool loadLastPsConsoleRemote() {
    cJSON* root = readConfig();
    const cJSON* remote = cJSON_GetObjectItem(root, "fr_last_ps_remote");
    bool result = cJSON_IsTrue(remote);
    cJSON_Delete(root);
    return result;
}

bool savePsSettings"""),
    ("""    bool ok = writeConfig(root);
    cJSON_Delete(root);
    return ok;
}

PsSettingsActivity""", """    cJSON_DeleteItemFromObject(root, "fr_smart_quality");
    cJSON_AddBoolToObject(root, "fr_smart_quality", settings.fr_smart_quality);
    cJSON_DeleteItemFromObject(root, "fr_eco_mode");
    cJSON_AddBoolToObject(root, "fr_eco_mode", settings.fr_eco_mode);
    cJSON_DeleteItemFromObject(root, "fr_stats_at_start");
    cJSON_AddBoolToObject(root, "fr_stats_at_start", settings.fr_stats_at_start);
    cJSON_DeleteItemFromObject(root, "fr_quick_reconnect");
    cJSON_AddBoolToObject(root, "fr_quick_reconnect", settings.fr_quick_reconnect);
    cJSON_DeleteItemFromObject(root, "fr_accent_theme");
    cJSON_AddNumberToObject(root, "fr_accent_theme", settings.fr_accent_theme);
    bool ok = writeConfig(root);
    cJSON_Delete(root);
    return ok;
}

PsSettingsActivity"""),
    ("""    auto* done = new brls::Button(); done->setText""", """    // FR+ options apply at the next PS stream; only accent themes require app restart.
    root->addView(makeSectionHeader("LunarNX FR+", "Réglages PlayStation supplémentaires"));
    auto* plus = makeUiCard(); plus->setPadding(4, 8, 4, 8);
    auto* smart = new brls::BooleanCell();
    smart->init("Qualité réseau auto (au démarrage)", settings_.fr_smart_quality,
        [this](bool enabled) { settings_.fr_smart_quality = enabled; });
    plus->addView(smart);
    auto* eco = new brls::BooleanCell();
    eco->init("Mode économie de batterie", settings_.fr_eco_mode,
        [this](bool enabled) { settings_.fr_eco_mode = enabled; });
    plus->addView(eco);
    auto* stats = new brls::BooleanCell();
    stats->init("Statistiques visibles au lancement", settings_.fr_stats_at_start,
        [this](bool enabled) { settings_.fr_stats_at_start = enabled; });
    plus->addView(stats);
    auto* reconnect = new brls::BooleanCell();
    reconnect->init("Bouton reconnexion rapide", settings_.fr_quick_reconnect,
        [this](bool enabled) { settings_.fr_quick_reconnect = enabled; });
    plus->addView(reconnect);
    auto* theme = new brls::SelectorCell();
    theme->init("Thème (redémarrer LunarNX)",
        {"Menthe classique", "Bleu PlayStation", "Violet", "Rouge"},
        std::clamp(settings_.fr_accent_theme, 0, 3),
        [this](int selected) { settings_.fr_accent_theme = std::clamp(selected, 0, 3); });
    plus->addView(theme);
    root->addView(plus);
    root->addView(makeMutedLabel(
        "Auto = 720p, 12 Mb/s en réseau local ou 8 Mb/s via PSN. "
        "Eco = 720p, 6 Mb/s et vibrations désactivées. "
        "Ces profils sont choisis AVANT la connexion (pas de débit variable en direct).", 12));
    auto* done = new brls::Button(); done->setText"""),
])

edit("src/ui/ps_activity.cpp", [
    ("""    sidebar->addView(pair_button);

    auto* settings_button""", """    sidebar->addView(pair_button);

    // Safe reconnect shortcut: the user initiates it and the normal route planner
    // still validates cached console credentials, route and console state.
    if (loadPsSettings().fr_quick_reconnect) {
        auto* quick = makeSidebarButton("Reconnexion PS5 rapide", false, UiIcon::Link);
        quick->registerClickAction([this](brls::View*) -> bool {
            const std::string mac = loadLastPsConsoleMac();
            const bool remote = loadLastPsConsoleRemote();
            if (mac.empty()) {
                brls::Application::notify("Connecte une première fois ta PS5.");
                return true;
            }
            auto it = std::find_if(hosts_.begin(), hosts_.end(),
                [&mac, remote](const ps::PsConsole& host) {
                    return host.server_mac == mac &&
                        (remote ? host.remote.has_value() : host.local.has_value());
                });
            if (it == hosts_.end()) {
                if (remote) fetchPsnConsoles();
                else startLanDiscovery();
                brls::Application::notify("Recherche des consoles : réessaie dans un instant.");
                return true;
            }
            const ps::PsConsole host = *it;
            setConsoleSource(remote ? PsConsoleSource::Remote : PsConsoleSource::Local);
            if (!remote && host.local->verified &&
                host.local->state == ps::PsConsoleState::Standby) {
                wakeupConsole(host);
            } else {
                connectToConsole(host);
            }
            return true;
        });
        sidebar->addView(quick);
    }

    auto* settings_button"""),
    ("""    const bool requested_remote = plan.isRemote();
    if (action_status_)""", """    const bool requested_remote = plan.isRemote();
    rememberLastPsConsole(host.server_mac, requested_remote);
    if (action_status_)"""),
    ("""    const auto settings = loadPsSettings();
    diagnosticLog("ui-ps", "stream profile=""", """    auto settings = loadPsSettings();
    if (settings.fr_smart_quality) {
        // Safe start-of-session selection, not in-stream bitrate renegotiation.
        settings.width = 1280;
        settings.height = 720;
        settings.bitrate_kbps = requested_remote ? 8000 : 12000;
    }
    if (settings.fr_eco_mode) {
        settings.width = 1280;
        settings.height = 720;
        settings.bitrate_kbps = std::min(settings.bitrate_kbps, 6000);
        settings.vibration_enabled = false;
    }
    diagnosticLog("ui-ps", "stream profile="""),
])

edit("src/ui/stream_view.cpp", [
    ("""    quick_menu_->setHeight(620);""", """    quick_menu_->setHeight(690);"""),
    ("""(brls::Application::ORIGINAL_WINDOW_HEIGHT - 620) / 2);""", """(brls::Application::ORIGINAL_WINDOW_HEIGHT - 690) / 2);"""),
    ("""    auto* platform_button = new brls::Button();""", """    if (runtime_->getStreamPlatform() == app::StreamPlatform::PlayStation) {
        auto* power_button = new brls::Button();
        power_button->setHeight(64);
        power_button->setStyle(&brls::BUTTONSTYLE_DEFAULT);
        power_button->setCornerRadius(0);
        power_button->setHighlightCornerRadius(3);
        power_button->setText("Alimentation PS5 (ouvrir menu)");
        power_button->registerClickAction([this](brls::View*) -> bool {
            // The PS button opens Control Center. User must choose the
            // console's native Power > Rest Mode option; do not fake power-off.
            setQuickMenuVisible(false);
            runtime_->requestPlatformHomeButton();
            brls::Application::notify("Sur la PS5 : Alimentation > Mode repos.");
            return true;
        });
        quick_menu_->addView(power_button);
    }

    auto* platform_button = new brls::Button();"""),
    ("""    root->addView(quick_menu_);
    updatePerformanceVisibility();""", """    root->addView(quick_menu_);
    if (runtime_->getStreamPlatform() == app::StreamPlatform::PlayStation) {
        performance_visible_ = loadPsSettings().fr_stats_at_start;
    }
    updatePerformanceVisibility();"""),
])

edit("src/ui/ui_style.cpp", [
    ("""#include "ui_style.h"

#include <algorithm>""", """#include "ui_style.h"
#include "../common.h"
#include <cJSON.h>
#include <cstdio>
#include <string>

#include <algorithm>"""),
    ("""} // namespace

void installLunarTheme() {
    installThemeVariant(brls::Theme::getDarkTheme(), kDarkPalette, true);
    installThemeVariant(brls::Theme::getLightTheme(), kLightPalette, false);
}

const UiPalette& uiPalette() {
    return brls::Application::getThemeVariant() == brls::ThemeVariant::DARK
        ? kDarkPalette
        : kLightPalette;
}""", """} // namespace

// Palette copied from the upstream defaults. Theme choice is read only at
// application startup; a restart is needed after changing the selector.
static UiPalette gFrDarkPalette = kDarkPalette;
static UiPalette gFrLightPalette = kLightPalette;

void installLunarTheme() {
    int theme = 0;
    FILE* file = std::fopen(lunar::get_config_path(), "rb");
    if (file) {
        if (std::fseek(file, 0, SEEK_END) == 0) {
            const long size = std::ftell(file);
            if (size > 0 && size < 65536 && std::fseek(file, 0, SEEK_SET) == 0) {
                std::string data(static_cast<size_t>(size), '\\0');
                if (std::fread(data.data(), 1, data.size(), file) == data.size()) {
                    cJSON* config = cJSON_Parse(data.c_str());
                    if (config) {
                        const cJSON* value = cJSON_GetObjectItem(config, "fr_accent_theme");
                        if (cJSON_IsNumber(value)) theme = std::clamp(value->valueint, 0, 3);
                        cJSON_Delete(config);
                    }
                }
            }
        }
        std::fclose(file);
    }
    gFrDarkPalette = kDarkPalette;
    gFrLightPalette = kLightPalette;
    if (theme == 1) {
        gFrDarkPalette.accent = nvgRGB(50, 130, 255);
        gFrDarkPalette.accent_soft = nvgRGBA(25, 75, 135, 210);
        gFrLightPalette.accent = nvgRGB(15, 80, 190);
        gFrLightPalette.accent_soft = nvgRGBA(15, 80, 190, 36);
    } else if (theme == 2) {
        gFrDarkPalette.accent = nvgRGB(180, 115, 255);
        gFrDarkPalette.accent_soft = nvgRGBA(86, 45, 130, 210);
        gFrLightPalette.accent = nvgRGB(116, 54, 175);
        gFrLightPalette.accent_soft = nvgRGBA(116, 54, 175, 36);
    } else if (theme == 3) {
        gFrDarkPalette.accent = nvgRGB(242, 90, 105);
        gFrDarkPalette.accent_soft = nvgRGBA(120, 28, 45, 210);
        gFrLightPalette.accent = nvgRGB(190, 35, 60);
        gFrLightPalette.accent_soft = nvgRGBA(190, 35, 60, 36);
    }
    installThemeVariant(brls::Theme::getDarkTheme(), gFrDarkPalette, true);
    installThemeVariant(brls::Theme::getLightTheme(), gFrLightPalette, false);
}

const UiPalette& uiPalette() {
    return brls::Application::getThemeVariant() == brls::ThemeVariant::DARK
        ? gFrDarkPalette
        : gFrLightPalette;
}"""),
])
print("All LunarNX FR+ source patches applied.")
