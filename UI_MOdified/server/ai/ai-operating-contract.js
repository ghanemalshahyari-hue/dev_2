'use strict';
/* ============================================================================
 * ai-operating-contract.js — RMOOZ-AI-OPERATING-CONTRACT-V1
 * ----------------------------------------------------------------------------
 * Canonical scenario / agent / committed-order contract for the new RMOOZ AI
 * Free Fight operating path.
 *
 * This module is intentionally side-effect free. It does not call an LLM, does
 * not touch files, does not move units, and does not mutate caller input. Its
 * job is to make every layer speak the same shape:
 *
 *   JSON/scenario import → location resolver → review → AI/non-AI mode
 *   → RED/BLUE/WHITE/GREEN agents → COA planner → committed execution.
 *
 * The old DOCX red_team/blue_team import path can be hidden/removed later
 * without changing this contract. The new path starts from one canonical input.
 * ========================================================================== */

var AGENTS = ['RED', 'BLUE', 'WHITE', 'GREEN'];
var SIDES  = ['RED', 'BLUE', 'GREEN', 'WHITE', 'NEUTRAL', 'UNKNOWN'];
var DOMAINS = ['air', 'ground', 'naval', 'air_defense', 'fires', 'base', 'support', 'infrastructure', 'unknown'];
var COORD_STATUS = ['exact', 'candidate', 'missing'];
var SOURCES = ['json', 'scenario', 'gazetteer', 'llm', 'manual', 'candidate', 'unknown'];
var CONFIDENCE = ['low', 'medium', 'high'];
var MODES = ['scenario_only', 'ai_free_fight'];

function arr(v) { return Array.isArray(v) ? v : []; }
function obj(v) { return v && typeof v === 'object' && !Array.isArray(v) ? v : {}; }
function str(v, max) {
    var s = String(v == null ? '' : v).trim();
    return max ? s.slice(0, max) : s;
}
function pick(v, allowed, fallback) {
    v = str(v).toLowerCase();
    for (var i = 0; i < allowed.length; i++) {
        if (String(allowed[i]).toLowerCase() === v) return allowed[i];
    }
    return fallback;
}
function side(v) { return String(pick(v, SIDES, 'UNKNOWN')).toUpperCase(); }
function domain(v) { return pick(v, DOMAINS, 'unknown'); }
function confidence(v) { return pick(v, CONFIDENCE, 'low'); }
function coordStatus(v) { return pick(v, COORD_STATUS, 'missing'); }
function source(v) { return pick(v, SOURCES, 'unknown'); }
function finite(v) { var n = Number(v); return Number.isFinite(n) ? n : null; }
function inLat(v) { var n = finite(v); return n != null && n >= -90 && n <= 90; }
function inLon(v) { var n = finite(v); return n != null && n >= -180 && n <= 180; }

function extractLonLat(x) {
    x = obj(x);
    if (Array.isArray(x.coord) && x.coord.length >= 2) {
        var lonA = finite(x.coord[0]);
        var latA = finite(x.coord[1]);
        if (inLon(lonA) && inLat(latA)) return [lonA, latA];
    }
    if (Array.isArray(x.coords) && x.coords.length >= 2) {
        var lonB = finite(x.coords[0]);
        var latB = finite(x.coords[1]);
        if (inLon(lonB) && inLat(latB)) return [lonB, latB];
    }
    var lon = finite(x.lon != null ? x.lon : x.lng);
    var lat = finite(x.lat);
    if (inLon(lon) && inLat(lat)) return [lon, lat];
    return null;
}

function coordBlock(x) {
    var c = extractLonLat(x);
    if (!c) return { coord: null, coord_status: 'missing', needs_review: true };
    var st = coordStatus(x.coord_status || x.placement_status || 'exact');
    return { coord: c, coord_status: st, needs_review: st !== 'exact' || x.needs_review === true };
}

function stableId(prefix, parts) {
    var s = arr(parts).join('|'), h = 5381;
    for (var i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) >>> 0;
    return prefix + '-' + h.toString(36).toUpperCase();
}

function normalizeObjective(raw, idx) {
    raw = obj(raw);
    var cb = coordBlock(raw);
    var name = str(raw.name || raw.label || raw.title || raw.canonical || raw.name_en || ('Objective ' + (idx + 1)), 120);
    return {
        id: str(raw.id || raw.objective_id || raw.uid || stableId('OBJ', [name, idx]), 64),
        name: name,
        type: str(raw.type || raw.kind || raw.category || 'unknown', 64),
        coord: cb.coord,
        coord_status: cb.coord_status,
        confidence: typeof raw.confidence === 'number' ? Math.max(0, Math.min(1, raw.confidence)) : raw.confidence || null,
        confidence_label: confidence(raw.confidence_label || raw.confidence_text || (cb.coord ? 'medium' : 'low')),
        source: source(raw.source_type || raw.source || (cb.coord ? 'json' : 'unknown')),
        needs_review: raw.needs_review === true || cb.needs_review,
        evidence: arr(raw.evidence || raw.citations || raw.sources).slice(0, 12),
        raw_ref: raw.raw_ref || raw.source_key || null,
    };
}

function normalizeUnit(raw, idx) {
    raw = obj(raw);
    var cb = coordBlock(raw);
    var name = str(raw.name || raw.label || raw.title || raw.unit_name || raw.uid || raw.id || ('Unit ' + (idx + 1)), 160);
    var sd = side(raw.side || raw.force || raw.coalition);
    var uid = str(raw.uid || raw.id || raw.unit_uid || stableId(sd === 'BLUE' ? 'B' : (sd === 'RED' ? 'R' : 'U'), [sd, name, idx]), 80);
    var blockedByCoord = !cb.coord;
    return {
        uid: uid,
        id: uid,
        name: name,
        side: sd,
        domain: domain(raw.domain || raw.type || raw.kind || raw.role_domain),
        role: str(raw.role || raw.unit_role || raw.category || '', 80),
        echelon: str(raw.echelon || raw.size || '', 40),
        home_base: str(raw.home_base || raw.base || raw.origin || '', 120) || null,
        coord: cb.coord,
        coord_status: cb.coord_status,
        confidence: typeof raw.confidence === 'number' ? Math.max(0, Math.min(1, raw.confidence)) : raw.confidence || null,
        confidence_label: confidence(raw.confidence_label || raw.confidence_text || (cb.coord ? 'medium' : 'low')),
        source: source(raw.source_type || raw.source || (cb.coord ? 'json' : 'unknown')),
        needs_review: raw.needs_review === true || cb.needs_review,
        taskable: raw.taskable === false ? false : !blockedByCoord,
        blocked_reason: blockedByCoord ? 'missing_coordinates' : (raw.blocked_reason || null),
        capabilities: obj(raw.capabilities || raw.capability || {}),
        evidence: arr(raw.evidence || raw.citations || raw.sources).slice(0, 12),
        raw_ref: raw.raw_ref || raw.source_key || null,
    };
}

function normalizeInfrastructure(raw, idx) {
    raw = obj(raw);
    var cb = coordBlock(raw);
    var name = str(raw.name || raw.label || raw.title || ('Infrastructure ' + (idx + 1)), 160);
    return {
        id: str(raw.id || raw.infrastructure_id || stableId('INF', [name, idx]), 80),
        name: name,
        type: str(raw.type || raw.kind || 'infrastructure', 80),
        side: side(raw.side || raw.owner || 'NEUTRAL'),
        coord: cb.coord,
        coord_status: cb.coord_status,
        source: source(raw.source_type || raw.source || (cb.coord ? 'json' : 'unknown')),
        needs_review: raw.needs_review === true || cb.needs_review,
        evidence: arr(raw.evidence || raw.citations || raw.sources).slice(0, 12),
    };
}

function normalizeAreaOfInterest(raw) {
    raw = obj(raw);
    var name = str(raw.name || raw.label || raw.area_name || '', 160) || null;
    var bbox = Array.isArray(raw.bbox) && raw.bbox.length === 4 ? raw.bbox.map(Number) : null;
    if (bbox && !(inLon(bbox[0]) && inLat(bbox[1]) && inLon(bbox[2]) && inLat(bbox[3]))) bbox = null;
    return {
        name: name,
        bbox: bbox,
        center: extractLonLat(raw.center || raw) || null,
        description: str(raw.description || raw.summary || '', 500) || null,
        source: source(raw.source_type || raw.source || (bbox ? 'json' : 'unknown')),
    };
}

function collectRawUnits(input) {
    input = obj(input);
    var out = [];
    arr(input.units).forEach(function (u) { out.push(u); });
    arr(input.red_units).forEach(function (u) { out.push(Object.assign({}, obj(u), { side: 'RED' })); });
    arr(input.blue_units).forEach(function (u) { out.push(Object.assign({}, obj(u), { side: 'BLUE' })); });
    arr(input.blue_units_initial).forEach(function (u) { out.push(Object.assign({}, obj(u), { side: 'BLUE' })); });
    return out;
}

function collectRawObjectives(input) {
    input = obj(input);
    var out = [];
    arr(input.objectives).forEach(function (o) { out.push(o); });
    if (input.objective) out.push(input.objective);
    if (input.obj) {
        var o = obj(input.obj);
        if (Array.isArray(o.coord)) out.push({ id: o.id || 'OBJ-PRIMARY', name: o.name || o.name_en || 'Primary Objective', coord: o.coord, type: o.type || 'objective' });
    }
    return out;
}

function normalizeScenarioInput(input, opts) {
    opts = obj(opts);
    input = obj(input);
    var mode = pick(opts.mode || input.mode || input.scenario_mode, MODES, 'scenario_only');
    var units = collectRawUnits(input).map(normalizeUnit);
    var objectives = collectRawObjectives(input).map(normalizeObjective);
    var infra = arr(input.infrastructure || input.objects || input.facilities).map(normalizeInfrastructure);
    var ao = normalizeAreaOfInterest(input.area_of_interest || input.aoi || input.ao || {});
    var missing = [];
    units.forEach(function (u) { if (!u.coord) missing.push({ kind: 'unit', id: u.uid, name: u.name, reason: 'missing_coordinates' }); });
    objectives.forEach(function (o) { if (!o.coord) missing.push({ kind: 'objective', id: o.id, name: o.name, reason: 'missing_coordinates' }); });
    infra.forEach(function (i) { if (!i.coord) missing.push({ kind: 'infrastructure', id: i.id, name: i.name, reason: 'missing_coordinates' }); });
    return {
        contract_version: 'RMOOZ-AI-OPERATING-CONTRACT-V1',
        scenario_id: str(input.scenario_id || input.id || stableId('SCN', [input.name || input.operation_name || 'scenario', units.length, objectives.length]), 80),
        operation_name: str(input.operation_name || input.name || input.title || 'Untitled Scenario', 160),
        mode: mode,
        area_of_interest: ao,
        objectives: objectives,
        units: units,
        infrastructure: infra,
        resolver_report: arr(input.resolver_report).slice(0, 200),
        missing_coordinates: missing,
        readiness: summarizeReadiness(units, objectives, missing),
    };
}

function summarizeReadiness(units, objectives, missing) {
    var taskable = arr(units).filter(function (u) { return u.taskable && u.coord; }).length;
    var red = arr(units).filter(function (u) { return u.side === 'RED'; }).length;
    var blue = arr(units).filter(function (u) { return u.side === 'BLUE'; }).length;
    var objReady = arr(objectives).filter(function (o) { return !!o.coord; }).length;
    return {
        units_total: arr(units).length,
        red_units: red,
        blue_units: blue,
        taskable_units: taskable,
        objectives_total: arr(objectives).length,
        objectives_with_coordinates: objReady,
        missing_coordinates: arr(missing).length,
        executable_with_ai: taskable > 0 && objReady > 0 && red > 0 && blue > 0,
        executable_without_ai: objReady > 0 && arr(units).length > 0,
    };
}

function normalizeAgentOutput(agent, raw) {
    raw = obj(raw);
    var a = String(agent || raw.agent || '').toUpperCase();
    if (AGENTS.indexOf(a) === -1) a = 'WHITE';
    return {
        agent: a,
        assessment: str(raw.assessment || raw.summary || '', 2000),
        recommended_actions: arr(raw.recommended_actions || raw.actions).slice(0, 50),
        constraints: arr(raw.constraints).slice(0, 50),
        confidence: confidence(raw.confidence || 'low'),
        evidence: arr(raw.evidence || raw.citations || raw.sources).slice(0, 20),
        warnings: arr(raw.warnings).slice(0, 20),
    };
}

function validateCommittedAiExecution(selection) {
    selection = obj(selection);
    var errors = [];
    if (!selection.selected_plan_id) errors.push('missing_selected_plan_id');
    if (!selection.committed_plan_id) errors.push('missing_committed_plan_id');
    if (selection.selected_plan_id && selection.committed_plan_id && selection.selected_plan_id !== selection.committed_plan_id) errors.push('selected_committed_plan_mismatch');
    if (selection.plan_source !== 'llm') errors.push('plan_source_not_llm');
    if (selection.llm_status !== 'ok') errors.push('llm_status_not_ok');
    if (!arr(selection.actions).length) errors.push('no_committed_actions');
    return { ok: errors.length === 0, errors: errors };
}

module.exports = {
    AGENTS: AGENTS,
    SIDES: SIDES,
    DOMAINS: DOMAINS,
    COORD_STATUS: COORD_STATUS,
    SOURCES: SOURCES,
    CONFIDENCE: CONFIDENCE,
    MODES: MODES,
    extractLonLat: extractLonLat,
    normalizeScenarioInput: normalizeScenarioInput,
    normalizeObjective: normalizeObjective,
    normalizeUnit: normalizeUnit,
    normalizeInfrastructure: normalizeInfrastructure,
    normalizeAgentOutput: normalizeAgentOutput,
    summarizeReadiness: summarizeReadiness,
    validateCommittedAiExecution: validateCommittedAiExecution,
};
