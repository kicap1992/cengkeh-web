/**
 * chat.js — Cengkeh chatbot UI interactions.
 *
 * Wires up:
 *   #chat-form    — the input form (submit event)
 *   #chat-input   — the text field
 *   #chat-send    — the send button
 *   #chat-messages — the message container
 *
 * Talks to:
 *   GET /api/search?q=...        — find matching QAs
 *   GET /api/qa/<id>             — get a QA with answer + follow-ups
 *   GET /api/next/<option_id>    — follow a diagnostic branch
 */

console.log("🍀 chat.js loaded");