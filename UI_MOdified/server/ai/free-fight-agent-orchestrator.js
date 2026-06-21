'use strict';
/* ============================================================================
 * free-fight-agent-orchestrator.js — RMOOZ-AI-AGENTS-V1
 * ----------------------------------------------------------------------------
 * Thin orchestration layer for the new RED / BLUE / WHITE / GREEN operating
 * model. This is deliberately conservative: it produces inspectable agent
 * assessments and constraints, but it does NOT move units, does NOT adjudicate
 * combat effects, and does NOT claim deterministic output is an LLM COA.
 *
 * Intended use:
 *   1. Normalize one scenario/JSON package through ai-operating-contract.
 *   2. Show agent outputs in Scenario Control Center.
 *   3. Feed the RED/BLUE intent + WHITE/GREEN constraints into /plan-coas.
 *   4. Commit/run only the validated LLM COA.
 * ========================================================================== */

var CONTRACT = require('./ai-operating-contract.js');
var GREEN_WORLD = require('./green-world.js');

function arr(v) { return Array.isArray(v) ? v : []; }
function obj(v) { return v && typeof v === 'object' && !Array.isArray(v) ? v : {}; }
function str(v, max) { var s = String(v == null ? '' : v).trim(); return max ? s.slice(0, max) : s; }
function ll(item) {
    item = obj(item);
    if (Array.isArray(item.coord) && item.coord.length >= 2) return { lon: Number(item.coord[0]), lat: Number(item.coord[1]) };
    if (Number.isFinite(Number(item.lon)) && Number.isFinite(Number(item.lat))) return { lon: Number(item.lon), lat: Number(item.lat) };
    return null;
}
function distKm(a, b) {
    a = ll(a) || a; b = ll(b) || b;
    if (!a || !b || !Number.isFinite(+a.lat) || !Number.isFinite(+a.lon) || !Number.isFinite(+b.lat) || !Number.isFinite(+b.lon)) return null;
    var R = 6371, tr = Math.PI / 180;
    var dLat = (+b.lat - +a.lat) * tr, dLon = (+b.lon - +a.lon) * tr;
    var la1 = +a.lat * tr, la2 = +b.lat * tr;
    var h = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos(la1) * Math.cos(la2) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
}
function nearest(units, objective, limit) {
    return arr(units).map(function (u) { return { unit: u, km: distKm(u, objective) }; })
        .filter(function (x) { return x.km != null; })
        .sort(function (a, b) { return a.km - b.km; })
        .slice(0, limit || 5);
}
function domainCounts(units) {
    var out = {};
    arr(units).forEach(function (u) { var d = u.domain || 'unknown'; out[d] = (out[d] || 0) + 1; });
    return out;
}
function primaryObjective(scenario) { return arr(scenario.objectives)[0] || null; }

function buildRedAgent(scenario, context) {
    var objv = primaryObjective(scenario);
    var red = arr(scenario.units).filter(function (u) { return u.side === 'RED' && u.coord && u.taskable !== false; });
    var near = nearest(red, objv, 6);
    var actions = [];
    if (objv && near.length) {
        actions.push({ type: 'develop_red_coa', objective_id: objv.id, preferred_units: near.map(function (x) { return x.unit.uid; }), note: 'Use nearest relevant RED units first; do not move the whole force.' });
        actions.push({ type: 'phase_guidance', phases: ['recon/screen approach', 'main effort toward objective', 'support/reserve follow-on'] });
    }
    return CONTRACT.normalizeAgentOutput('RED', {
        assessment: red.length
            ? ('RED has ' + red.length + ' taskable unit(s). Nearest RED elements should shape the attack or pressure the objective; distant units stay reserve/hold unless needed.')
            : 'No taskable RED units are available for AI Free Fight.',
        recommended_actions: actions,
        constraints: [
            'No all-units-at-once movement.',
            'No objective-center stacking.',
            'Air/naval/ground units must use domain-realistic movement roles.',
        ],
        confidence: objv && near.length ? 'medium' : 'low',
        evidence: near.map(function (x) { return { unit_uid: x.unit.uid, name: x.unit.name, distance_km: Math.round(x.km * 10) / 10 }; }),
    });
}

function buildBlueAgent(scenario, context) {
    var objv = primaryObjective(scenario);
    var blue = arr(scenario.units).filter(function (u) { return u.side === 'BLUE' && u.coord && u.taskable !== false; });
    var near = nearest(blue, objv, 6);
    var actions = [];
    if (objv && near.length) {
        actions.push({ type: 'protect_objective', objective_id: objv.id, preferred_units: near.map(function (x) { return x.unit.uid; }), note: 'Hold protected zone and send nearest suitable intercept/reinforcement only when triggered.' });
        actions.push({ type: 'reaction_triggers', triggers: ['warning_zone_entry', 'objective_contested', 'objective_lost_retake'] });
    }
    return CONTRACT.normalizeAgentOutput('BLUE', {
        assessment: blue.length
            ? ('BLUE has ' + blue.length + ' taskable unit(s). Defense should hold key objectives, intercept intrusions, and keep reserve for retake.')
            : 'No taskable BLUE units are available for AI Free Fight.',
        recommended_actions: actions,
        constraints: [
            'Do not send every BLUE unit to one contact.',
            'Use nearest appropriate units first.',
            'If objective is lost, generate retake COA with main effort/support/reserve.',
        ],
        confidence: objv && near.length ? 'medium' : 'low',
        evidence: near.map(function (x) { return { unit_uid: x.unit.uid, name: x.unit.name, distance_km: Math.round(x.km * 10) / 10 }; }),
    });
}

function buildWhiteAgent(scenario, context) {
    var objv = primaryObjective(scenario);
    var taskable = arr(scenario.units).filter(function (u) { return u.coord && u.taskable !== false; });
    var missing = arr(scenario.missing_coordinates);
    var constraints = [
        'Only committed LLM COA actions may execute in AI Free Fight.',
        'Movement must be phased and bounded; no teleporting.',
        'Reject shallow one-unit/one-action COAs when multiple taskable units exist.',
        'Hold unresolved/missing-coordinate units until reviewed.',
    ];
    if (missing.length) constraints.push(missing.length + ' unresolved item(s) require location review before tasking.');
    return CONTRACT.normalizeAgentOutput('WHITE', {
        assessment: 'WHITE controls legality, timing, validation, and event-log truth. Current scenario has ' + taskable.length + ' taskable unit(s)' + (objv ? ' and a primary objective.' : ' but no primary objective.'),
        recommended_actions: [
            { type: 'validate_before_commit', required: ['plan_source=llm', 'llm_status=ok', 'selected_plan_id == committed_plan_id'] },
            { type: 'quality_gate', required: ['multi_phase_when_possible', 'multi_unit_when_possible', 'domain_realistic_movement'] },
        ],
        constraints: constraints,
        confidence: objv && taskable.length ? 'medium' : 'low',
        evidence: [{ taskable_units: taskable.length, missing_coordinates: missing.length }],
    });
}

function buildGreenAgent(scenario, context) {
    var objv = primaryObjective(scenario);
    var green = GREEN_WORLD.assessNeutralWorld({
        units: arr(scenario.units),
        objective: objv,
        terrain: obj(context.terrain || context.terrain_context),
        coa: context.coa || null,
    });
    return CONTRACT.normalizeAgentOutput('GREEN', {
        assessment: arr(green.notes).join(' '),
        recommended_actions: [
            { type: 'neutral_constraints', collateral_risk: green.collateral_risk, road_status: green.road_status, neutral_reaction_score: green.neutral_reaction_score },
        ],
        constraints: [
            'Consider civilian/infrastructure/collateral constraints before committing route or fires.',
            'GREEN is advisory and review-only; it does not move units or invent effects.',
        ],
        confidence: green.provenance && green.provenance.population === 'absent' ? 'low' : 'medium',
        evidence: [{ green_world: green }],
    });
}

function buildAgentAssessments(input, context) {
    context = obj(context);
    var scenario = input && input.contract_version === 'RMOOZ-AI-OPERATING-CONTRACT-V1'
        ? input
        : CONTRACT.normalizeScenarioInput(input || {}, { mode: context.mode || 'ai_free_fight' });
    return {
        ok: true,
        contract_version: scenario.contract_version,
        scenario_id: scenario.scenario_id,
        operation_name: scenario.operation_name,
        mode: scenario.mode,
        readiness: scenario.readiness,
        agents: {
            RED: buildRedAgent(scenario, context),
            BLUE: buildBlueAgent(scenario, context),
            WHITE: buildWhiteAgent(scenario, context),
            GREEN: buildGreenAgent(scenario, context),
        },
        force_summary: {
            red: arr(scenario.units).filter(function (u) { return u.side === 'RED'; }).length,
            blue: arr(scenario.units).filter(function (u) { return u.side === 'BLUE'; }).length,
            taskable: arr(scenario.units).filter(function (u) { return u.taskable && u.coord; }).length,
            domains: domainCounts(scenario.units),
        },
    };
}

module.exports = {
    buildAgentAssessments: buildAgentAssessments,
    _internals: {
        buildRedAgent: buildRedAgent,
        buildBlueAgent: buildBlueAgent,
        buildWhiteAgent: buildWhiteAgent,
        buildGreenAgent: buildGreenAgent,
        nearest: nearest,
    },
};
