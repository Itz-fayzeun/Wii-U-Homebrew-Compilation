#ifdef __SWITCH__
#include "friday_chat_activity.h"
#include "ps_settings_activity.h"
#include "ui_style.h"
#include "../platform/network_worker.h"
#include <cJSON.h>
#include <curl/curl.h>
#include <algorithm>
#include <cctype>
#include <chrono>
#include <cstdio>
#include <mutex>
#include <string>
#include <utility>

namespace lunar::ui {
namespace {

std::string lowerAscii(std::string text) {
    std::transform(text.begin(), text.end(), text.begin(),
        [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return text;
}

bool contains(const std::string& text, const char* term) {
    return text.find(term) != std::string::npos;
}

std::string offlineAdvice(const std::string& query,
                          const std::shared_ptr<app::IStreamRuntime>& runtime) {
    const std::string q = lowerAscii(query);
    std::string context;
    if (runtime && runtime->getStreamPlatform() == app::StreamPlatform::PlayStation) {
        const auto& p = runtime->getPerfStats();
        char values[128]{};
        std::snprintf(values, sizeof(values),
            "\nPS5 : latence %u ms, perte de paquets %.1f%%.",
            p.ps_rtt_ms.load(), p.ps_packet_loss_fraction.load() * 100.0f);
        context = values;
    }
    std::string advice;
    if (contains(q, "lag") || contains(q, "connexion") || contains(q, "latence") ||
        contains(q, "wifi") || contains(q, "réseau") || contains(q, "reseau")) {
        advice = "Pour stabiliser le Remote Play : PS5 branchée en Ethernet, "
                 "Switch Lite en Wi-Fi 5 GHz près du routeur, puis 720p et 10 Mb/s. "
                 "Si ça continue, vérifie les pertes de paquets.";
    } else if (contains(q, "image") || contains(q, "pixel") ||
               contains(q, "qualit") || contains(q, "resolution")) {
        advice = "Une image pixelisée vient souvent du débit réseau. "
                 "Essaie 720p/10 Mb/s et évite les téléchargements simultanés. "
                 "L'écran Switch Lite est en 720p.";
    } else if (contains(q, "fps") || contains(q, "fluide") ||
               contains(q, "saccade")) {
        advice = "Les FPS affichés dépendent du flux et du jeu PS5. "
                 "Un jeu bloqué à 30 FPS n'indique pas forcément un problème. "
                 "Regarde surtout les pertes de paquets et la latence.";
    } else if (contains(q, "batterie") || contains(q, "autonomie")) {
        advice = "Active le mode économie de batterie de LunarNX FR+, "
                 "désactive les vibrations et baisse la luminosité de la Switch.";
    } else if (contains(q, "ps5") || contains(q, "remote") ||
               contains(q, "reconnexion")) {
        advice = "Dans les réglages de la PS5, active Lecture à distance. "
                 "Pour la réveiller depuis le repos, active sa connexion Internet "
                 "et l'allumage via le réseau pendant le repos.";
    } else {
        advice = "Je peux te conseiller sur la connexion, l'image, les FPS, "
                 "la PS5 et la batterie. Pour une conversation IA libre, "
                 "configure une passerelle FRIDAY HTTPS dans les paramètres.";
    }
    return std::string("FRIDAY (diagnostic local, sans IA) :\n") + advice + context;
}

bool secureFridayUrl(const std::string& url) {
    if (url.size() < 12 || url.size() > 255 ||
        url.compare(0, 8, "https://") != 0) return false;
    // Only HTTPS to a configured host. Do not allow URL credentials or controls.
    return url.find('@') == std::string::npos &&
        url.find('#') == std::string::npos &&
        url.find_first_of("\r\n\t ") == std::string::npos;
}

size_t receiveReply(char* data, size_t size, size_t count, void* target) {
    auto* response = static_cast<std::string*>(target);
    const size_t bytes = size * count;
    if (bytes > 8192 || response->size() + bytes > 8192) return 0;
    response->append(data, bytes);
    return bytes;
}

std::string askGateway(const std::string& url, const std::string& token,
                       const std::string& question) {
    if (!secureFridayUrl(url) || token.size() < 16) {
        return "FRIDAY : passerelle non configurée (HTTPS + code de 16 caractères minimum).";
    }
    static std::once_flag curl_once;
    std::call_once(curl_once, []() { curl_global_init(CURL_GLOBAL_DEFAULT); });

    cJSON* request = cJSON_CreateObject();
    if (!request) return "FRIDAY : mémoire insuffisante.";
    cJSON_AddStringToObject(request, "message", question.c_str());
    char* encoded = cJSON_PrintUnformatted(request);
    cJSON_Delete(request);
    if (!encoded) return "FRIDAY : mémoire insuffisante.";
    std::string body(encoded);
    cJSON_free(encoded);

    CURL* curl = curl_easy_init();
    if (!curl) return "FRIDAY : accès réseau indisponible.";
    curl_slist* headers = nullptr;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    headers = curl_slist_append(headers, "Accept: application/json");
    const std::string token_header = "X-Friday-Token: " + token;
    headers = curl_slist_append(headers, token_header.c_str());
    std::string response;
    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_POST, 1L);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, body.c_str());
    curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE, static_cast<long>(body.size()));
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, receiveReply);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 1L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 2L);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 0L);
    curl_easy_setopt(curl, CURLOPT_PROTOCOLS, CURLPROTO_HTTPS);
    curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT_MS, 3000L);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT_MS, 9000L);
    curl_easy_setopt(curl, CURLOPT_NOSIGNAL, 1L);
    const CURLcode result = curl_easy_perform(curl);
    long status = 0;
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &status);
    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);
    if (result != CURLE_OK) {
        return "FRIDAY : impossible de joindre le serveur HTTPS. "
               "Vérifie son adresse et son certificat.";
    }
    if (status != 200) {
        return status == 401 ? "FRIDAY : code d'accès incorrect."
            : "FRIDAY : serveur indisponible. Réessaie plus tard.";
    }
    cJSON* reply_json = cJSON_Parse(response.c_str());
    if (!reply_json) return "FRIDAY : réponse du serveur invalide.";
    const cJSON* reply = cJSON_GetObjectItemCaseSensitive(reply_json, "reply");
    std::string answer = cJSON_IsString(reply) && reply->valuestring
        ? reply->valuestring : "FRIDAY : réponse invalide.";
    cJSON_Delete(reply_json);
    if (answer.size() > 1500) {
        answer.resize(1500);
        answer += "...";
    }
    return "FRIDAY :\n" + answer;
}

} // namespace

FridayChatActivity::FridayChatActivity(std::shared_ptr<app::IStreamRuntime> runtime)
    : runtime_(std::move(runtime)) {}

FridayChatActivity::~FridayChatActivity() {
    alive_->store(false);
}

brls::View* FridayChatActivity::createContentView() {
    const auto& palette = uiPalette();
    auto* scroll = new brls::ScrollingFrame();
    scroll->setBackgroundColor(palette.background);
    auto* root = new brls::Box(brls::Axis::COLUMN);
    root->setPadding(22, 52, 34, 52);
    root->setBackgroundColor(palette.background);

    root->addView(makeSectionHeader("FRIDAY",
        "Assistant de diagnostic local + IA en ligne facultative"));
    auto* hint = makeMutedLabel(
        "Sans passerelle HTTPS : conseils de dépannage simples, pas de vraie IA.", 14);
    hint->setMarginBottom(20);
    root->addView(hint);

    auto* question = new brls::InputCell();
    question->setHeight(70);
    question->init("Ta question", "",
        [this, alive = alive_](std::string value) {
            if (alive->load()) question_ = std::move(value);
        },
        "Demander à FRIDAY", "Exemple : Pourquoi mon Remote Play lag ?", 280, 0);
    root->addView(question);

    auto* ask = new brls::Button();
    ask->setText("Envoyer à FRIDAY");
    stylePrimaryButton(ask);
    ask->setMarginTop(14);
    ask->registerClickAction([this](brls::View*) -> bool {
        askFriday();
        return true;
    });
    root->addView(ask);

    auto* reply_card = makeUiCard();
    reply_card->setMarginTop(20);
    response_ = new brls::Label();
    response_->setFontSize(17.0f);
    response_->setTextColor(palette.text);
    response_->setHeight(240);
    response_->setText("FRIDAY est prête. Pose une question sur la PS5, "
                       "la connexion, la qualité vidéo ou les performances.");
    reply_card->addView(response_);
    root->addView(reply_card);

    root->addView(makeMutedLabel(
        "Confidentialité : seul le texte de ta question part au serveur configuré. "
        "Aucun identifiant PSN ni capture d'écran n'est envoyé.", 12));
    scroll->setContentView(root);
    return makeAppFrame("FRIDAY", scroll);
}

void FridayChatActivity::askFriday() {
    if (busy_ || !response_) return;
    if (question_.empty()) {
        response_->setText("Écris ta question dans la case du haut.");
        return;
    }
    const PsSettingsSnapshot options = loadPsSettings();
    if (options.friday_gateway_url.empty()) {
        response_->setText(offlineAdvice(question_, runtime_));
        return;
    }
    if (!secureFridayUrl(options.friday_gateway_url) ||
        options.friday_gateway_token.size() < 16) {
        response_->setText("Pour activer l'IA : renseigne une adresse HTTPS "
            "et un code d'accès FRIDAY de 16 caractères minimum dans les paramètres PS.");
        return;
    }

    busy_ = true;
    response_->setText("FRIDAY : connexion au serveur IA...");
    auto alive = alive_;
    auto url = options.friday_gateway_url;
    auto token = options.friday_gateway_token;
    auto question = question_;
    const bool launched = lunar::platform::startNetworkWorker("friday-chat",
        [this, alive, url = std::move(url), token = std::move(token),
         question = std::move(question)]() {
            const std::string answer = askGateway(url, token, question);
            brls::sync([this, alive, answer]() {
                if (!alive->load()) return;
                busy_ = false;
                if (response_) response_->setText(answer);
            });
        });
    if (!launched) {
        busy_ = false;
        response_->setText("FRIDAY : le système est occupé. "
            "Aucun changement n'a été apporté au Remote Play.");
    }
}

} // namespace lunar::ui
#endif
