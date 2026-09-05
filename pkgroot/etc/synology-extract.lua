-- IDNNOV Log Agent — extrait les SD-PARAMS Synology en champs indexés + dérive severity.
-- Benché sur le binaire embarqué (Fluent Bit 5.0.9, filter lua compilé pour 1027).
--
-- DSM Log Center n'envoie PAS le SD-PARAMS dans le champ extradata RFC5424: la
-- trame "[synolog@6574 k="v" ...]" arrive collée au début de MESSAGE (prouvé au
-- banc + en prod). On parse donc record["message"], en tolérant:
--   - plusieurs segments SD: "[synolog@6574 ...][meta sequenceId="N"]texte"
--   - séparateur optionnel: [synolog@6574 ...] texte  ou  [synolog@6574 ...]texte
--
-- ATTENTION PATTERNS LUA: pas de (?:...) ni de | (alternance) — ce sont des
-- extensions PCRE. Le premier jet utilisait '(?:[^"\\]|\\.)*' et gmatch ne
-- trouvait RIEN (banc: dbg_cnt0=0). Patterns natifs uniquement ci-dessous.
--
-- severity dérivée de pri (RFC 5424: pri = facility*8 + severity).

local SEV_NAMES = {
    [0] = "emergency", [1] = "alert", [2] = "critical", [3] = "error",
    [4] = "warning", [5] = "notice", [6] = "info", [7] = "debug",
}

-- Paires k="v" d'un segment SD-PARAMS.
-- '[^"]*' s'arrête à la 1re quote: une valeur contenant \" (rarissime, aucun cas
-- observé sur 163 événements de prod) serait tronquée, mais les paires suivantes
-- restent correctement alignées car gmatch reprend au prochain key=".
local function extract_params(segment, record)
    for key, value in segment:gmatch('([%w_]+)="([^"]*)"') do
        if key ~= "sequenceId" and key ~= "sequenceid" and record[key] == nil then
            -- Dé-échappe RFC 5424: \" -> " puis \\ -> \.
            value = value:gsub('\\"', '"')
            value = value:gsub('\\\\', '\\')
            record[key] = value
        end
    end
end

function cb_synology_extract(tag, timestamp, record)
    local message = record["message"]
    local pri = record["pri"]

    -- 1. Sévérité dérivée (toujours dispo, même sans SD-PARAMS).
    --    RFC 5424: pri = facility*8 + severity => severity = pri % 8.
    if pri then
        local n = tonumber(pri)
        if n and n >= 0 and n <= 191 then
            record["severity"] = SEV_NAMES[n % 8] or "info"
        end
    end

    if type(message) ~= "string" then
        return 2, timestamp, record
    end

    -- 2. SD-PARAMS collés au message: suite de segments [id k="v" ...] suivis
    --    du texte utile.
    local pos = 1
    local any_sd = false
    while message:sub(pos, pos) == "[" do
        local close = message:find("]", pos, true)
        if not close then break end
        local segment = message:sub(pos + 1, close - 1)
        -- Un segment SD valide commence par un identifiant "xxx@yyy" ou "meta".
        local ident = segment:match("^([%w@%-_.]+)%s") or segment:match("^([%w@%-_.]+)$")
        if not ident then break end
        extract_params(segment, record)
        any_sd = true
        pos = close + 1
        -- RFC 5424: UN espace optionnel entre segments / avant le message.
        if message:sub(pos, pos) == " " then pos = pos + 1 end
    end

    -- 3. Message nettoyé: texte utile sans la chaîne SD-PARAMS.
    if any_sd and pos > 1 then
        local rest = message:sub(pos)
        -- BOM éventuel en tête des messages DSM.
        rest = rest:gsub("^\xEF\xBB\xBF", "")
        if rest ~= "" then
            record["message"] = rest
        else
            record["message"] = record["msgid"] or ""
        end
    end

    return 2, timestamp, record
end
