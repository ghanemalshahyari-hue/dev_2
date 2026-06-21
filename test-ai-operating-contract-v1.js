'use strict';
/* ============================================================================
 * test-ai-operating-contract-v1.js — RMOOZ-AI-OPERATING-CONTRACT-V1 smoke test
 * ----------------------------------------------------------------------------
 * Verifies the new canonical scenario contract and RED/BLUE/WHITE/GREEN agent
 * wrapper without starting the app, moving units, or calling any LLM.
 * ========================================================================== */

const assert = require('assert');
const CONTRACT = require('./UI_MOdified/server/ai/ai-operating-contract.js');
const AGENTS = require('./UI_MOdified/server/ai/free-fight-agent-orchestrator.js');

const input = {
  operation_name: 'AI Agent V1 Smoke Scenario',
  mode: 'ai_free_fight',
  area_of_interest: { name: 'Gulf AOI', bbox: [50, 24, 58, 30] },
  objectives: [
    { id: 'OBJ-BA', name: 'Bandar Abbas Naval Base', type: 'naval_base', coord: [56.2167, 27.15], source: 'gazetteer' }
  ],
  red_units: [
    { uid: 'R-AIR-1', name: 'RED strike aircraft', domain: 'air', coord: [56.10, 27.05], source: 'json' },
    { uid: 'R-NAV-1', name: 'RED naval group', domain: 'naval', coord: [56.00, 27.00], source: 'json' }
  ],
  blue_units_initial: [
    { uid: 'B-AD-1', name: 'BLUE air defense battery', domain: 'air_defense', coord: [56.40, 27.35], source: 'json' },
    { uid: 'B-AIR-1', name: 'BLUE interceptor pair', domain: 'air', coord: [56.50, 27.45], source: 'json' }
  ],
  infrastructure: [
    { id: 'INF-PORT', name: 'Port facility', type: 'port', coord: [56.22, 27.16] }
  ]
};

const scenario = CONTRACT.normalizeScenarioInput(input, { mode: 'ai_free_fight' });
assert.strictEqual(scenario.contract_version, 'RMOOZ-AI-OPERATING-CONTRACT-V1');
assert.strictEqual(scenario.mode, 'ai_free_fight');
assert.strictEqual(scenario.units.length, 4);
assert.strictEqual(scenario.objectives.length, 1);
assert.strictEqual(scenario.readiness.red_units, 2);
assert.strictEqual(scenario.readiness.blue_units, 2);
assert.strictEqual(scenario.readiness.taskable_units, 4);
assert.strictEqual(scenario.readiness.executable_with_ai, true);
assert.strictEqual(scenario.missing_coordinates.length, 0);

const agentOut = AGENTS.buildAgentAssessments(scenario, { terrain: { terrain_class: 'coastal urban', owner_country: 'Iran' } });
assert.strictEqual(agentOut.ok, true);
assert(agentOut.agents.RED.assessment.includes('RED has 2'));
assert(agentOut.agents.BLUE.assessment.includes('BLUE has 2'));
assert(agentOut.agents.WHITE.constraints.some((x) => /Only committed LLM COA/.test(x)));
assert(agentOut.agents.GREEN.evidence[0].green_world.review_only);
assert.strictEqual(agentOut.force_summary.taskable, 4);

const badCommit = CONTRACT.validateCommittedAiExecution({
  selected_plan_id: 'COA-1', committed_plan_id: 'COA-2', plan_source: 'deterministic_coa_fallback', llm_status: 'disabled', actions: []
});
assert.strictEqual(badCommit.ok, false);
assert(badCommit.errors.includes('selected_committed_plan_mismatch'));
assert(badCommit.errors.includes('plan_source_not_llm'));
assert(badCommit.errors.includes('llm_status_not_ok'));
assert(badCommit.errors.includes('no_committed_actions'));

const goodCommit = CONTRACT.validateCommittedAiExecution({
  selected_plan_id: 'COA-1', committed_plan_id: 'COA-1', plan_source: 'llm', llm_status: 'ok', actions: [{ unit_uid: 'R-AIR-1', action_type: 'RECON_OBJECTIVE' }]
});
assert.strictEqual(goodCommit.ok, true);

console.log('PASS test-ai-operating-contract-v1');
